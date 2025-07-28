from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import HTMLResponse

from backend import get_db
from backend.core.deps import get_current_user_from_cookie
from backend.database.marketing.crud import DrawUserCRUD
from backend.database.userservice import get_all_users
from config import templates

router = APIRouter(prefix="/dashboard/admin")


@router.get("/", response_class=HTMLResponse)
async def admin(request: Request, current_user=Depends(get_current_user_from_cookie), all_users=Depends(get_all_users)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/main_admin.html",
                                      {"request": request, "user": current_user, "all_users": all_users})


@router.get("/add_user", response_class=HTMLResponse)
async def add_user(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/register-employer.html", {"request": request, "user": current_user})


@router.get('/add-excel-files', response_class=HTMLResponse, name="add_excel_file")
async def add_excel_file_html(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/add-excel-files.html", {"request": request, "user": current_user})


@router.get("/data-base", response_class=HTMLResponse)
async def users(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/resident-complex.html", {"request": request, "user": current_user})


@router.get("/draws", response_class=HTMLResponse)
async def users(request: Request, current_user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    draw_users = DrawUserCRUD().list_draw_users(db)
    return templates.TemplateResponse("/admin/draw-complex.html",
                                      {"request": request, "user": current_user, "draw_users": draw_users})


@router.get('/marketing', response_class=HTMLResponse)
async def marketing(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/marketing/register.html", {"request": request, "user": current_user})


@router.get('/marketing/add-campaigns', response_class=HTMLResponse)
async def marketing(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/marketing/add-campaigns.html", {"request": request, "user": current_user})


@router.get('/marketing/campaigns', response_class=HTMLResponse)
async def marketing(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/marketing/exact_campaign.html", {"request": request, "user": current_user})
