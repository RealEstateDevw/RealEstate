from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.api.leads.schemas import LeadSearchResponse
from backend.api.users.schemas import UserSearchResponse

router = APIRouter(prefix="/api/mop")


@router.get("/search", response_model=List[LeadSearchResponse, UserSearchResponse])
async def search_leads(
        query: str = Query(..., min_length=0, description="Search query for leads"),
        limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
        db: Session = Depends(get_db)
):
    """
    Search leads by name, phone number, or region.
    Returns a list of matching leads with basic information.
    """
    results = lead_crud.combined_search(db, query, limit)
    return results
