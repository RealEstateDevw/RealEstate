from fastapi import Request, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.core.deps import get_current_user_from_cookie
from backend.database.attendanceservice import has_user_checked_in, register_attendance
from config import templates


router = APIRouter(prefix="/dashboard/sales")


@router.get("/", response_class=HTMLResponse, name="sales_dashboard")
async def sales_dashboard(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role_id != 1:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/sales-dashboard.html", {"request": request, "user": current_user})


@router.get("/add-lead", response_class=HTMLResponse)
async def add_lead(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role_id != 1:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/add-lead-sales.html", {"request": request, "user": current_user})


@router.get("/lead/{lead_id}", response_class=HTMLResponse, name="exact_lead")
async def lead(request: Request, lead_id: int, current_user=Depends(get_current_user_from_cookie),
               db: Session = Depends(get_db)):
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/exact_lead.html", {"request": request, "user": current_user, "lead": db_lead})

