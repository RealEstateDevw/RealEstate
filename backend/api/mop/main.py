from typing import List, Union

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.api.leads.schemas import LeadSearchResponse
from backend.api.mop.schemas import SearchResponse
from backend.api.users.schemas import UserSearchResponse

router = APIRouter(prefix="/api/mop")


@router.get("/search", response_model=SearchResponse)
async def search_leads_and_users(
        query: str = Query(..., min_length=1, description="Search query"),
        limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
        db: Session = Depends(get_db)
):
    """
    Search leads and users by name, phone, email, or region.
    Returns a unified list of matching results.
    """
    try:
        results = lead_crud.combined_search(db=db, query=query, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {str(e)}"
        )

    return results
