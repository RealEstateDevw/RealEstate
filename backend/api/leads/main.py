from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.api.leads.schemas import LeadSearchResponse, LeadInDB, LeadUpdate, LeadState, LeadStatus, LeadCreate, \
    CommentCreate, CommentResponse
from backend.core.deps import get_current_user_from_cookie
from backend.database import get_db
from backend.database.models import Comment, User
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
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    print(lead.monthly_payment, lead.installment_markup)
    return lead_crud.create_lead(db, lead)



@router.get("/{lead_id}", response_model=LeadInDB)
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.get("/", response_model=List[LeadInDB])
async def get_leads(
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
async def update_lead(lead_id: int, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    db_lead = lead_crud.update_lead(db, lead_id, lead_update)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    success = lead_crud.delete_lead(db, lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead successfully deleted"}


@router.get("/user/{user_id}", response_model=List[LeadInDB])
async def get_user_leads(
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    return lead_crud.get_leads_by_user(db, user_id, skip, limit)


@router.get("/comments/{lead_id}", response_model=List[CommentResponse])
async def get_comments(lead_id: int, db: Session = Depends(get_db)):
    comments = (
        db.query(Comment)
        .filter(Comment.lead_id == lead_id)
        .order_by(Comment.created_at)
        .all()
    )

    # Add author name to each comment
    for comment in comments:
        comment.author_name = comment.author.first_name

    return comments


@router.post("/comments", response_model=CommentResponse)
async def create_comment(comment: CommentCreate, db: Session = Depends(get_db),
                         current_user_id=Depends(get_current_user_from_cookie)):
    db_comment = Comment(
        text=comment.text,
        is_internal=comment.is_internal,
        lead_id=comment.lead_id,
        author_id=current_user_id.id
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Add author name for response
    db_comment.author_name = db_comment.author.first_name

    return db_comment
