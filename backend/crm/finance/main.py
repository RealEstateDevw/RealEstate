"""Маршруты CRM для финансового отдела.

Доступ имеют только пользователи с ``role_id = 4``. Перед рендером страниц
отмечаем присутствие в системе учёта посещаемости. Эндпоинты возвращают
HTML-шаблоны, бизнес-операции с платежами и лидами находятся в CRUD/сервисах.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.core.deps import get_current_user_from_cookie
from backend.database.attendanceservice import has_user_checked_in, register_attendance
from config import templates

router = APIRouter(prefix="/dashboard/finance")


@router.get("/", response_class=HTMLResponse, name="finance_dashboard")
async def finance_dashboard(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Главный дашборд финансистов: проверяем роль и регистрируем вход."""
    if current_user.role_id != 4:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/finance/finance-dashboard.html", {"request": request, "user": current_user})


@router.get("/add-payment", response_class=HTMLResponse, name="add_payment")
async def add_payment(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Форма фиксации оплат по контрактам/лидам."""
    if current_user.role_id != 4:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/finance/add-payment.html", {"request": request, "user": current_user})


@router.get("/stats-detail", response_class=HTMLResponse)
async def stats_detail(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Детальный отчёт с финансовыми показателями."""
    if current_user.role_id != 4:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/finance/finance-dashboard-all.html", {"request": request, "user": current_user})


@router.get("/lead/{lead_id}", response_class=HTMLResponse, name="exact_finance_lead")
async def lead(request: Request, lead_id: int, current_user=Depends(get_current_user_from_cookie),
               db: Session = Depends(get_db)):
    """Карточка лида для финансов: загружаем данные и отмечаем посещение."""
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/finance/exact-lead.html",
                                      {"request": request, "user": current_user, "lead": db_lead})
