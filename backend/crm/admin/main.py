"""Маршруты административной панели CRM.

Здесь собираются HTML-страницы, доступные только пользователям с ролью
``Админ``. Каждый эндпоинт:
* проверяет, что текущий пользователь имеет нужную роль;
* подготавливает данные (пользователи, участники розыгрышей, кампании);
* возвращает шаблон, который уже знает, как отрисовать полученные данные;
* при необходимости формирует файлы (генератор актов).

Файл старается не содержать бизнес-логики: вся работа с БД и внешними сервисами
делегируется в CRUD-слой и сервисы, чтобы удобно было дорабатывать.
"""

from datetime import date

from fastapi import Depends, APIRouter, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend import get_db
from backend.core.deps import get_current_user_from_cookie
from backend.database.marketing.crud import DrawUserCRUD
from backend.database.userservice import get_all_users
from config import templates
from backend.database.act_service import reg_act

router = APIRouter(prefix="/dashboard/admin")


@router.get("/", response_class=HTMLResponse)
async def admin(request: Request, current_user=Depends(get_current_user_from_cookie), all_users=Depends(get_all_users)):
    """Главная страница админки с перечнем всех пользователей.

    Если зашёл не админ, отправляем на главную страницу приложения, чтобы не показывать
    внутренние инструменты управления.
    """
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/main_admin.html",
                                      {"request": request, "user": current_user, "all_users": all_users})


@router.get("/add_user", response_class=HTMLResponse)
async def add_user(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Форма для создания нового сотрудника через веб-интерфейс."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/register-employer.html", {"request": request, "user": current_user})


@router.get('/add-excel-files', response_class=HTMLResponse, name="add_excel_file")
async def add_excel_file_html(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Загрузка Excel-файлов с данными (например, импорты лидов или объектов)."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/add-excel-files.html", {"request": request, "user": current_user})


@router.get("/data-base", response_class=HTMLResponse)
async def users(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Раздел с выгрузкой/просмотром базы данных в интерфейсе админа."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/resident-complex.html", {"request": request, "user": current_user})


@router.get("/draws", response_class=HTMLResponse)
async def users(request: Request, current_user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    """Список участников розыгрышей, подтягиваем из маркетингового CRUD."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    draw_users = DrawUserCRUD().list_draw_users(db)
    return templates.TemplateResponse("/admin/draw-complex.html",
                                      {"request": request, "user": current_user, "draw_users": draw_users})


@router.get('/marketing', response_class=HTMLResponse)
async def marketing(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    """Дашборд маркетинга с кампаниями."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse(
        "/marketing/register.html",
        {"request": request, "user": current_user},
    )


@router.get('/marketing/add-campaigns', response_class=HTMLResponse)
async def marketing(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Форма создания маркетинговой кампании (верстка без бизнес-логики)."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/marketing/add-campaigns.html", {"request": request, "user": current_user})


@router.get('/marketing/campaigns', response_class=HTMLResponse)
async def marketing(request: Request, current_user=Depends(get_current_user_from_cookie)):
    """Список кампаний для просмотра уже созданных активностей."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/marketing/exact_campaign.html", {"request": request, "user": current_user})


@router.get("/act-generator", response_class=HTMLResponse, name="act_generator")
async def act_generator(
    request: Request,
    current_user=Depends(get_current_user_from_cookie),
):
    """Страница с формой генерации актов выполненных работ."""
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})

    return templates.TemplateResponse(
        "/admin/act-generator.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.post("/act-generator/create", name="act_generator_create")
async def act_generator_create(
    jk_name: str = Form(...),
    contract_id: str = Form(...),
    act_number: str = Form(...),
    date_act: date = Form(...),
    current_user=Depends(get_current_user_from_cookie),
):
    """Создание акта: валидируем роль, генерируем документ и отдаём файл."""
    if current_user.role.name != "Админ":
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания актов.")

    try:
        act_path = reg_act(jk_name=jk_name, contract_id=contract_id, act_number=act_number, date_act=date_act)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Не удалось сформировать акт.") from exc

    return FileResponse(
        path=act_path,
        filename=act_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
