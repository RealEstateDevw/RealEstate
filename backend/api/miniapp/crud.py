"""CRUD operations for Mini App API."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database.models import (
    TelegramMiniAppUser,
    ApartmentInterestScore,
    MiniAppLeadRequest,
    MiniAppLeadRequestType,
    MiniAppLeadRequestStatus,
)


class MiniAppCRUD:
    """CRUD operations for Telegram Mini App."""

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def get_user_by_telegram_id(self, db: Session, telegram_id: int) -> Optional[TelegramMiniAppUser]:
        """Get user by Telegram ID."""
        return db.query(TelegramMiniAppUser).filter(
            TelegramMiniAppUser.telegram_id == telegram_id
        ).first()

    def get_or_create_user(
        self,
        db: Session,
        telegram_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        source_payload: str = "telegram"
    ) -> TelegramMiniAppUser:
        """Get existing user or create new one."""
        user = self.get_user_by_telegram_id(db, telegram_id)

        if user:
            # Update last activity and potentially source_payload
            user.last_active_at = datetime.utcnow()
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if username:
                user.username = username
            # Only update source_payload if it's still default
            if user.source_payload == "telegram" and source_payload != "telegram":
                user.source_payload = source_payload
            db.commit()
            db.refresh(user)
            return user

        # Create new user
        user = TelegramMiniAppUser(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            source_payload=source_payload
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user_phone(self, db: Session, telegram_id: int, phone: str) -> Optional[TelegramMiniAppUser]:
        """Update user's phone number."""
        user = self.get_user_by_telegram_id(db, telegram_id)
        if user:
            user.phone = phone
            db.commit()
            db.refresh(user)
        return user

    # =========================================================================
    # INTEREST SCORE OPERATIONS
    # =========================================================================

    def get_or_create_interest_score(
        self,
        db: Session,
        user_id: int,
        complex_name: str,
        block_name: str,
        floor: int,
        unit_number: str,
        area_sqm: Optional[float] = None,
        rooms: Optional[int] = None
    ) -> ApartmentInterestScore:
        """Get existing interest score record or create new one."""
        score = db.query(ApartmentInterestScore).filter(
            ApartmentInterestScore.user_id == user_id,
            ApartmentInterestScore.complex_name == complex_name,
            ApartmentInterestScore.block_name == block_name,
            ApartmentInterestScore.floor == floor,
            ApartmentInterestScore.unit_number == unit_number
        ).first()

        if score:
            return score

        score = ApartmentInterestScore(
            user_id=user_id,
            complex_name=complex_name,
            block_name=block_name,
            floor=floor,
            unit_number=unit_number,
            area_sqm=area_sqm,
            rooms=rooms
        )
        db.add(score)
        db.commit()
        db.refresh(score)
        return score

    def increment_view_count(
        self,
        db: Session,
        score: ApartmentInterestScore
    ) -> ApartmentInterestScore:
        """Increment view count (+1 point) and update last_viewed_at."""
        score.view_count += 1
        score.last_viewed_at = datetime.utcnow()
        score.recalculate_total()
        db.commit()
        db.refresh(score)
        return score

    def add_time_score(
        self,
        db: Session,
        score: ApartmentInterestScore,
        seconds: int
    ) -> ApartmentInterestScore:
        """
        Add time score: +1 per 10 seconds, max +12.
        Also updates total_time_seconds (capped at 180s per apartment).
        """
        MAX_TIME_SCORE = 12
        MAX_TOTAL_TIME = 180

        # Add to total time (capped)
        new_total_time = min(score.total_time_seconds + seconds, MAX_TOTAL_TIME)
        score.total_time_seconds = new_total_time

        # Calculate time score (1 point per 10 seconds, max 12)
        new_time_score = min(new_total_time // 10, MAX_TIME_SCORE)
        score.time_score = new_time_score

        score.last_viewed_at = datetime.utcnow()
        score.recalculate_total()
        db.commit()
        db.refresh(score)
        return score

    def add_event_bonus(
        self,
        db: Session,
        score: ApartmentInterestScore,
        event_type: str
    ) -> tuple[ApartmentInterestScore, int]:
        """
        Add bonus points for specific events.
        Returns (updated_score, bonus_added)
        """
        bonus_added = 0

        if event_type == "payment_view" and score.payment_view_bonus == 0:
            score.payment_view_bonus = 3
            bonus_added = 3
        elif event_type == "map_view" and score.map_view_bonus == 0:
            score.map_view_bonus = 2
            bonus_added = 2
        elif event_type == "favorite" and score.favorites_bonus == 0:
            score.favorites_bonus = 5
            bonus_added = 5

        if bonus_added > 0:
            score.last_viewed_at = datetime.utcnow()
            score.recalculate_total()
            db.commit()
            db.refresh(score)

        return score, bonus_added

    def get_top_interests(
        self,
        db: Session,
        user_id: int,
        top_n: int = 10
    ) -> List[ApartmentInterestScore]:
        """Get user's top N apartments by interest score."""
        # First, recalculate all scores for freshness
        scores = db.query(ApartmentInterestScore).filter(
            ApartmentInterestScore.user_id == user_id
        ).all()

        for score in scores:
            score.recalculate_total()

        db.commit()

        # Now get sorted list
        return db.query(ApartmentInterestScore).filter(
            ApartmentInterestScore.user_id == user_id
        ).order_by(
            ApartmentInterestScore.total_score.desc()
        ).limit(top_n).all()

    def get_best_interest(
        self,
        db: Session,
        user_id: int
    ) -> Optional[ApartmentInterestScore]:
        """Get user's top apartment by interest score."""
        interests = self.get_top_interests(db, user_id, top_n=1)
        return interests[0] if interests else None

    # =========================================================================
    # LEAD REQUEST OPERATIONS
    # =========================================================================

    def create_lead_request(
        self,
        db: Session,
        user_id: int,
        request_type: str,
        complex_name: Optional[str] = None,
        block_name: Optional[str] = None,
        floor: Optional[int] = None,
        unit_number: Optional[str] = None,
        area_sqm: Optional[float] = None,
        rooms: Optional[int] = None,
        price_snapshot: Optional[float] = None,
        payment_type_interest: Optional[str] = None
    ) -> MiniAppLeadRequest:
        """Create lead request from Mini App action."""
        # Get current interest score if apartment is specified
        interest_score = None
        if complex_name and unit_number:
            score = db.query(ApartmentInterestScore).filter(
                ApartmentInterestScore.user_id == user_id,
                ApartmentInterestScore.complex_name == complex_name,
                ApartmentInterestScore.block_name == block_name,
                ApartmentInterestScore.floor == floor,
                ApartmentInterestScore.unit_number == unit_number
            ).first()
            if score:
                score.recalculate_total()
                interest_score = score.total_score

        # Map string to enum
        type_enum = MiniAppLeadRequestType(request_type)

        request = MiniAppLeadRequest(
            user_id=user_id,
            request_type=type_enum,
            complex_name=complex_name,
            block_name=block_name,
            floor=floor,
            unit_number=unit_number,
            area_sqm=area_sqm,
            rooms=rooms,
            price_snapshot=price_snapshot,
            payment_type_interest=payment_type_interest,
            interest_score=interest_score
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    def get_pending_request(
        self,
        db: Session,
        user_id: int
    ) -> Optional[MiniAppLeadRequest]:
        """Get most recent pending request for user."""
        return db.query(MiniAppLeadRequest).filter(
            MiniAppLeadRequest.user_id == user_id,
            MiniAppLeadRequest.status == MiniAppLeadRequestStatus.PENDING
        ).order_by(
            MiniAppLeadRequest.created_at.desc()
        ).first()

    def get_request_by_id(
        self,
        db: Session,
        request_id: int
    ) -> Optional[MiniAppLeadRequest]:
        """Get lead request by ID."""
        return db.query(MiniAppLeadRequest).filter(
            MiniAppLeadRequest.id == request_id
        ).first()

    def confirm_request(
        self,
        db: Session,
        request_id: int
    ) -> Optional[MiniAppLeadRequest]:
        """Mark request as confirmed (user said "Yes" in bot)."""
        request = self.get_request_by_id(db, request_id)
        if request and request.status == MiniAppLeadRequestStatus.PENDING:
            request.status = MiniAppLeadRequestStatus.CONFIRMED
            request.confirmed_at = datetime.utcnow()
            db.commit()
            db.refresh(request)
        return request

    def decline_request(
        self,
        db: Session,
        request_id: int
    ) -> Optional[MiniAppLeadRequest]:
        """Mark request as declined."""
        request = self.get_request_by_id(db, request_id)
        if request and request.status == MiniAppLeadRequestStatus.PENDING:
            request.status = MiniAppLeadRequestStatus.DECLINED
            db.commit()
            db.refresh(request)
        return request

    def convert_to_lead(
        self,
        db: Session,
        request_id: int,
        lead_id: int
    ) -> Optional[MiniAppLeadRequest]:
        """Mark request as converted and link to CRM lead."""
        request = self.get_request_by_id(db, request_id)
        if request:
            request.status = MiniAppLeadRequestStatus.CONVERTED
            request.lead_id = lead_id
            request.converted_at = datetime.utcnow()
            db.commit()
            db.refresh(request)
        return request


# Global instance
miniapp_crud = MiniAppCRUD()
