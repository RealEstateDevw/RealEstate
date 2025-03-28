from fastapi import Depends, APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse

from backend.core.deps import get_current_user_from_cookie
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
