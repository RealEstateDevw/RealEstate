from fastapi import Request, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.core.deps import get_current_user_from_cookie
from backend.database.attendanceservice import has_user_checked_in, register_attendance
from config import templates

router = APIRouter(prefix="/complexes")


@router.get("/", response_class=HTMLResponse, name="complexes")
async def sales_dashboard(request: Request):
    return templates.TemplateResponse("/shaxmatki/complexes.html", {"request": request})
