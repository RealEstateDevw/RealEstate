from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import Optional, List, Dict, Any, Union
from fastapi.encoders import jsonable_encoder

from backend.api.leads.schemas import LeadCreate, LeadStatus, LeadState, LeadUpdate
from backend.database.models import Lead, User


class LeadCRUD:
    def create_lead(self, db: Session, lead: LeadCreate) -> Lead:

        db_lead = Lead(**lead.dict())
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        return db_lead

    def get_lead(self, db: Session, lead_id: int) -> Optional[Lead]:
        return db.query(Lead).filter(Lead.id == lead_id).first()

    def get_leads(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            status: Optional[LeadStatus] = None,
            state: Optional[LeadState] = None,
            region: Optional[str] = None,
            payment_type: Optional[str] = None
    ) -> List[Lead]:
        query = db.query(Lead)

        if status:
            query = query.filter(Lead.status == status)
        if state:
            query = query.filter(Lead.state == state)
        if region:
            query = query.filter(Lead.region == region)
        if payment_type:
            query = query.filter(Lead.payment_type == payment_type)

        return query.order_by(desc(Lead.created_at)).offset(skip).limit(limit).all()

    def update_lead(self, db: Session, lead_id: int, lead_update: LeadUpdate) -> Optional[Lead]:
        db_lead = self.get_lead(db, lead_id)
        if not db_lead:
            return None

        update_data = lead_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_lead, field, value)

        db.commit()
        db.refresh(db_lead)
        return db_lead

    def delete_lead(self, db: Session, lead_id: int) -> bool:
        db_lead = self.get_lead(db, lead_id)
        if not db_lead:
            return False

        db.delete(db_lead)
        db.commit()
        return True

    def get_leads_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Lead]:
        return db.query(Lead).filter(Lead.user_id == user_id) \
            .order_by(desc(Lead.created_at)) \
            .offset(skip) \
            .limit(limit) \
            .all()

    def search_leads(
            self,
            db: Session,
            query: str,
            limit: int = 10
    ) -> List[Lead]:
        """
        Search leads by multiple fields:
        - full_name
        - phone
        - region
        """
        search_query = f"%{query}%"
        return db.query(Lead).filter(
            or_(
                Lead.full_name.ilike(search_query),
                Lead.phone.ilike(search_query),
                Lead.region.ilike(search_query)
            )
        ).limit(limit).all()

    def combined_search(db: Session, query: str, limit: int = 10) -> List[Union[Lead, User]]:
        """
        Search both leads and users by the provided query.
        """
        search_query = f"%{query}%"

        # Query Leads
        leads = db.query(Lead).filter(
            or_(
                Lead.full_name.ilike(search_query),
                Lead.phone.ilike(search_query),
                Lead.region.ilike(search_query)
            )
        ).limit(limit).all()

        # Query Users
        users = db.query(User).filter(
            or_(
                User.first_name.ilike(search_query),
                User.last_name.ilike(search_query),
                User.phone.ilike(search_query),
                User.email.ilike(search_query)
            )
        ).limit(limit).all()

        # Combine and limit results
        combined_results = (leads + users)[:limit]
        return combined_results
