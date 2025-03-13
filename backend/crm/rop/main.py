from fastapi import Request, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.core.deps import get_current_user_from_cookie
from backend.database.attendanceservice import has_user_checked_in, register_attendance
from config import templates


router = APIRouter(prefix="/dashboard/rop")


@router.get("/", response_class=HTMLResponse, name="rop_dashboard")
async def mop_dashboard(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role_id != 3:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/rop/rop-dashboard.html", {"request": request, "user": current_user})
