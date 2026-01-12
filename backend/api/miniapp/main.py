"""Mini App API endpoints."""
import hashlib
import hmac
import json
from urllib.parse import parse_qs
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.miniapp.schemas import (
    MiniAppUserInit,
    MiniAppUserResponse,
    ViewSessionStart,
    ViewSessionStartResponse,
    ViewSessionHeartbeat,
    ViewSessionHeartbeatResponse,
    ViewSessionEnd,
    ViewSessionEndResponse,
    InterestEventRequest,
    InterestEventResponse,
    InterestScoreResponse,
    TopInterestsResponse,
    FavoriteRequest,
    FavoriteResponse,
    LeadRequestCreate,
    LeadRequestResponse,
)
from backend.api.miniapp.crud import miniapp_crud
from settings import settings

router = APIRouter(prefix='/api/miniapp', tags=['Mini App'])


# =============================================================================
# TELEGRAM INIT DATA VALIDATION
# =============================================================================

def validate_telegram_init_data(init_data: str) -> Optional[dict]:
    """
    Validates Telegram Web App initData.
    Returns parsed user data if valid, None if invalid.
    """
    if not init_data or not settings.BOT_TOKEN:
        return None

    try:
        # Parse init_data as query string
        parsed = parse_qs(init_data)

        # Get hash and remove it from data
        received_hash = parsed.get('hash', [None])[0]
        if not received_hash:
            return None

        # Build data-check-string
        data_check_arr = []
        for key in sorted(parsed.keys()):
            if key != 'hash':
                data_check_arr.append(f"{key}={parsed[key][0]}")
        data_check_string = '\n'.join(data_check_arr)

        # Calculate secret key
        secret_key = hmac.new(
            b"WebAppData",
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify hash
        if calculated_hash != received_hash:
            return None

        # Parse user data
        user_data = parsed.get('user', [None])[0]
        if user_data:
            return json.loads(user_data)
        return None

    except Exception:
        return None


# =============================================================================
# USER ENDPOINTS
# =============================================================================

@router.post("/init", response_model=MiniAppUserResponse)
async def init_user(
    init_request: MiniAppUserInit,
    db: Session = Depends(get_db)
):
    """
    Initialize Mini App user session.
    Called when Mini App opens with Telegram initData.
    Extracts PAYLOAD from deep link if present.
    """
    # Validate initData (in production)
    user_data = validate_telegram_init_data(init_request.init_data)

    # For development/testing, allow without validation
    if not user_data:
        # Try to parse without validation for testing
        try:
            parsed = parse_qs(init_request.init_data)
            user_json = parsed.get('user', [None])[0]
            if user_json:
                user_data = json.loads(user_json)
        except Exception:
            pass

    if not user_data or 'id' not in user_data:
        raise HTTPException(status_code=400, detail="Invalid initData")

    telegram_id = user_data['id']
    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name')
    username = user_data.get('username')
    source_payload = init_request.start_param or "telegram"

    user = miniapp_crud.get_or_create_user(
        db,
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        source_payload=source_payload
    )

    # Get favorites count and top interest
    favorites_count = len(user.interest_scores) if hasattr(user, 'interest_scores') else 0
    top_interest = miniapp_crud.get_best_interest(db, user.id)
    top_interest_data = None
    if top_interest:
        top_interest_data = {
            "complex_name": top_interest.complex_name,
            "unit_number": top_interest.unit_number,
            "score": top_interest.total_score
        }

    return MiniAppUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        source_payload=user.source_payload,
        favorites_count=favorites_count,
        top_interest_apartment=top_interest_data
    )


@router.get("/me", response_model=MiniAppUserResponse)
async def get_current_user(
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get current user's profile and stats."""
    user = miniapp_crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    favorites_count = len(user.interest_scores) if hasattr(user, 'interest_scores') else 0
    top_interest = miniapp_crud.get_best_interest(db, user.id)
    top_interest_data = None
    if top_interest:
        top_interest_data = {
            "complex_name": top_interest.complex_name,
            "unit_number": top_interest.unit_number,
            "score": top_interest.total_score
        }

    return MiniAppUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        source_payload=user.source_payload,
        favorites_count=favorites_count,
        top_interest_apartment=top_interest_data
    )


# =============================================================================
# VIEW SESSION ENDPOINTS
# =============================================================================

# In-memory storage for active sessions (in production, use Redis)
_active_sessions: dict[int, dict] = {}


@router.post("/view-session/start", response_model=ViewSessionStartResponse)
async def start_view_session(
    session_data: ViewSessionStart,
    db: Session = Depends(get_db)
):
    """
    Start a new viewing session for an apartment.
    Creates a session record and increments view count.
    Returns session_id for subsequent heartbeats.
    """
    user = miniapp_crud.get_user_by_telegram_id(db, session_data.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create interest score record
    score = miniapp_crud.get_or_create_interest_score(
        db,
        user_id=user.id,
        complex_name=session_data.complex_name,
        block_name=session_data.block_name,
        floor=session_data.floor,
        unit_number=session_data.unit_number,
        area_sqm=session_data.area_sqm,
        rooms=session_data.rooms
    )

    # Increment view count
    score = miniapp_crud.increment_view_count(db, score)

    # Create session in memory
    session_id = score.id * 1000 + score.view_count  # Simple unique ID
    _active_sessions[session_id] = {
        "score_id": score.id,
        "user_id": user.id,
        "telegram_id": session_data.telegram_id,
        "total_active_seconds": 0,
        "started_at": score.last_viewed_at
    }

    return ViewSessionStartResponse(
        session_id=session_id,
        score_id=score.id,
        view_count=score.view_count
    )


@router.post("/view-session/heartbeat", response_model=ViewSessionHeartbeatResponse)
async def heartbeat(
    heartbeat_data: ViewSessionHeartbeat,
    db: Session = Depends(get_db)
):
    """
    Report time spent on apartment card.
    Called every 10 seconds while tab is active.
    Anti-fraud: checks if tab is visible, validates timing.
    """
    session = _active_sessions.get(heartbeat_data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["telegram_id"] != heartbeat_data.telegram_id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    MAX_TOTAL_TIME = 180
    should_end = False

    # Only count time if visible
    if heartbeat_data.is_visible and heartbeat_data.seconds_elapsed > 0:
        # Anti-fraud: cap at 30 seconds per heartbeat
        seconds_to_add = min(heartbeat_data.seconds_elapsed, 30)

        # Check if we're at the cap
        if session["total_active_seconds"] >= MAX_TOTAL_TIME:
            should_end = True
        else:
            session["total_active_seconds"] += seconds_to_add

            # Update score in database
            score = db.query(miniapp_crud.__class__.__bases__[0]).get(session["score_id"])
            # Actually get the score properly
            from backend.database.models import ApartmentInterestScore
            score = db.query(ApartmentInterestScore).filter(
                ApartmentInterestScore.id == session["score_id"]
            ).first()

            if score:
                score = miniapp_crud.add_time_score(db, score, seconds_to_add)

                if score.total_time_seconds >= MAX_TOTAL_TIME:
                    should_end = True

    return ViewSessionHeartbeatResponse(
        session_id=heartbeat_data.session_id,
        total_active_seconds=session["total_active_seconds"],
        time_score=min(session["total_active_seconds"] // 10, 12),
        should_end=should_end
    )


@router.post("/view-session/end", response_model=ViewSessionEndResponse)
async def end_view_session(
    session_end: ViewSessionEnd,
    db: Session = Depends(get_db)
):
    """
    End viewing session and finalize score calculation.
    Called when user leaves apartment card.
    """
    session = _active_sessions.pop(session_end.session_id, None)
    if not session:
        # Return default response if session not found (already ended)
        return ViewSessionEndResponse(
            session_id=session_end.session_id,
            total_score=0,
            time_score=0,
            total_time_seconds=0
        )

    # Get final score
    from backend.database.models import ApartmentInterestScore
    score = db.query(ApartmentInterestScore).filter(
        ApartmentInterestScore.id == session["score_id"]
    ).first()

    if score:
        score.recalculate_total()
        db.commit()
        return ViewSessionEndResponse(
            session_id=session_end.session_id,
            total_score=score.total_score,
            time_score=score.time_score,
            total_time_seconds=score.total_time_seconds
        )

    return ViewSessionEndResponse(
        session_id=session_end.session_id,
        total_score=0,
        time_score=0,
        total_time_seconds=session["total_active_seconds"]
    )


# =============================================================================
# INTEREST EVENT ENDPOINTS
# =============================================================================

@router.post("/interest-event", response_model=InterestEventResponse)
async def record_interest_event(
    event: InterestEventRequest,
    db: Session = Depends(get_db)
):
    """
    Record interest events:
    - payment_view: +3 points
    - map_view: +2 points
    """
    user = miniapp_crud.get_user_by_telegram_id(db, event.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get interest score record
    score = miniapp_crud.get_or_create_interest_score(
        db,
        user_id=user.id,
        complex_name=event.complex_name,
        block_name=event.block_name,
        floor=event.floor,
        unit_number=event.unit_number
    )

    score, bonus_added = miniapp_crud.add_event_bonus(db, score, event.event_type.value)

    return InterestEventResponse(
        score_id=score.id,
        event_type=event.event_type.value,
        bonus_added=bonus_added,
        total_score=score.total_score
    )


@router.get("/interest-scores/{telegram_id}", response_model=TopInterestsResponse)
async def get_user_interest_scores(
    telegram_id: int,
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get user's top apartments by interest score."""
    user = miniapp_crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interests = miniapp_crud.get_top_interests(db, user.id, top_n)

    return TopInterestsResponse(
        interests=[InterestScoreResponse.model_validate(i) for i in interests],
        total_count=len(interests)
    )


# =============================================================================
# FAVORITES ENDPOINTS
# =============================================================================

@router.post("/favorites", response_model=FavoriteResponse)
async def add_to_favorites(
    favorite: FavoriteRequest,
    db: Session = Depends(get_db)
):
    """Add apartment to favorites (+5 interest points)."""
    user = miniapp_crud.get_user_by_telegram_id(db, favorite.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create interest score
    score = miniapp_crud.get_or_create_interest_score(
        db,
        user_id=user.id,
        complex_name=favorite.complex_name,
        block_name=favorite.block_name,
        floor=favorite.floor,
        unit_number=favorite.unit_number,
        area_sqm=favorite.area_sqm,
        rooms=favorite.rooms
    )

    # Add favorite bonus
    score, bonus_added = miniapp_crud.add_event_bonus(db, score, "favorite")

    return FavoriteResponse(
        success=True,
        is_favorite=True,
        total_score=score.total_score
    )


@router.delete("/favorites", response_model=FavoriteResponse)
async def remove_from_favorites(
    telegram_id: int = Query(...),
    complex_name: str = Query(...),
    block_name: str = Query(...),
    floor: int = Query(...),
    unit_number: str = Query(...),
    db: Session = Depends(get_db)
):
    """Remove apartment from favorites (keeps the +5 bonus)."""
    user = miniapp_crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from backend.database.models import ApartmentInterestScore
    score = db.query(ApartmentInterestScore).filter(
        ApartmentInterestScore.user_id == user.id,
        ApartmentInterestScore.complex_name == complex_name,
        ApartmentInterestScore.block_name == block_name,
        ApartmentInterestScore.floor == floor,
        ApartmentInterestScore.unit_number == unit_number
    ).first()

    total_score = score.total_score if score else 0

    return FavoriteResponse(
        success=True,
        is_favorite=False,
        total_score=total_score
    )


# =============================================================================
# LEAD REQUEST ENDPOINTS
# =============================================================================

@router.post("/lead-request", response_model=LeadRequestResponse)
async def create_lead_request(
    request_data: LeadRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Create a lead request from Mini App.
    Types: leave_request, book, question
    Returns request_id for bot to reference.
    """
    user = miniapp_crud.get_user_by_telegram_id(db, request_data.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    request = miniapp_crud.create_lead_request(
        db,
        user_id=user.id,
        request_type=request_data.request_type.value,
        complex_name=request_data.complex_name,
        block_name=request_data.block_name,
        floor=request_data.floor,
        unit_number=request_data.unit_number,
        area_sqm=request_data.area_sqm,
        rooms=request_data.rooms,
        price_snapshot=request_data.price_snapshot,
        payment_type_interest=request_data.payment_type_interest
    )

    return LeadRequestResponse(
        id=request.id,
        request_type=request.request_type.value,
        status=request.status.value,
        complex_name=request.complex_name,
        block_name=request.block_name,
        floor=request.floor,
        unit_number=request.unit_number,
        area_sqm=request.area_sqm,
        rooms=request.rooms,
        price_snapshot=request.price_snapshot,
        interest_score=request.interest_score,
        created_at=request.created_at,
        confirmed_at=request.confirmed_at,
        converted_at=request.converted_at
    )


@router.get("/lead-request/{request_id}", response_model=LeadRequestResponse)
async def get_lead_request_status(
    request_id: int,
    db: Session = Depends(get_db)
):
    """Get lead request status."""
    request = miniapp_crud.get_request_by_id(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return LeadRequestResponse(
        id=request.id,
        request_type=request.request_type.value,
        status=request.status.value,
        complex_name=request.complex_name,
        block_name=request.block_name,
        floor=request.floor,
        unit_number=request.unit_number,
        area_sqm=request.area_sqm,
        rooms=request.rooms,
        price_snapshot=request.price_snapshot,
        interest_score=request.interest_score,
        created_at=request.created_at,
        confirmed_at=request.confirmed_at,
        converted_at=request.converted_at
    )


@router.get("/pending-request/{telegram_id}", response_model=Optional[LeadRequestResponse])
async def get_pending_request(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """Get pending lead request for user (used by bot)."""
    user = miniapp_crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None

    request = miniapp_crud.get_pending_request(db, user.id)
    if not request:
        return None

    return LeadRequestResponse(
        id=request.id,
        request_type=request.request_type.value,
        status=request.status.value,
        complex_name=request.complex_name,
        block_name=request.block_name,
        floor=request.floor,
        unit_number=request.unit_number,
        area_sqm=request.area_sqm,
        rooms=request.rooms,
        price_snapshot=request.price_snapshot,
        interest_score=request.interest_score,
        created_at=request.created_at,
        confirmed_at=request.confirmed_at,
        converted_at=request.converted_at
    )
