from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.leads.schemas import LeadSearchResponse, LeadInDB, LeadUpdate, LeadState, LeadStatus, LeadCreate
from backend.database import get_db
from backend.database.sales_service.crud import LeadCRUD

router = APIRouter(prefix="/api/leads")

lead_crud = LeadCRUD()


@router.get("/search", response_model=List[LeadSearchResponse])
async def search_leads(
        query: str = Query(..., min_length=0, description="Search query for leads"),
        limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
        db: Session = Depends(get_db)
):
    """
    Search leads by name, phone number, or region.
    Returns a list of matching leads with basic information.
    """
    results = lead_crud.search_leads(db, query, limit)
    return results


@router.post("/", response_model=LeadInDB)
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    return lead_crud.create_lead(db, lead)


@router.get("/{lead_id}", response_model=LeadInDB)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.get("/", response_model=List[LeadInDB])
def get_leads(
        skip: int = 0,
        limit: int = 100,
        status: Optional[LeadStatus] = None,
        state: Optional[LeadState] = None,
        region: Optional[str] = None,
        payment_type: Optional[str] = None,
        db: Session = Depends(get_db)
):
    return lead_crud.get_leads(db, skip, limit, status, state, region, payment_type)


@router.put("/{lead_id}", response_model=LeadInDB)
def update_lead(lead_id: int, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    db_lead = lead_crud.update_lead(db, lead_id, lead_update)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    success = lead_crud.delete_lead(db, lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead successfully deleted"}


@router.get("/user/{user_id}", response_model=List[LeadInDB])
def get_user_leads(
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    return lead_crud.get_leads_by_user(db, user_id, skip, limit)


