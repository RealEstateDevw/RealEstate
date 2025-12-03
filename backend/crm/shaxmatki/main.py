"""Маршруты витрины по жилым комплексам и шахматкам.

Сейчас модуль содержит только публичную страницу выбора ЖК. Закомментированные
обработчики оставлены как заготовки для более детальной навигации по блокам,
ЖК и квартирам. Такой скелет удобен, чтобы быстро включить/выключить страницы,
не ломая маршруты, когда фронтенд ещё в разработке.
"""

from fastapi import Request, APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.core.deps import get_current_user_from_cookie
from backend.database.attendanceservice import has_user_checked_in, register_attendance
from config import templates

router = APIRouter(prefix="/complexes")


@router.get("/", response_class=HTMLResponse, name="complexes")
async def complexes_page(request: Request):
    """Публичная страница со списком жилых комплексов и переходом внутрь."""
    return templates.TemplateResponse("/shaxmatki/complexes.html", {"request": request})



# @router.get("/blocks", response_class=HTMLResponse, name="blocks")
# async def blocks_page(request: Request, complex_id: str = Query(None)):
#     """Страница выбора блоков с поддержкой глубоких ссылок"""
#     # Поддерживаемые complex_id: rassvet, bahor
#     supported_complexes = ["rassvet", "bahor"]
    
#     if complex_id  in supported_complexes:
#         # Если передан валидный complex_id, передаем его в шаблон
#         return templates.TemplateResponse("/shaxmatki/blocks.html", {
#             "request": request, 
#             "complex_id": complex_id
#         })
#     elif complex_id:
#         # Если передан неверный complex_id, возвращаем ошибку
#         raise HTTPException(status_code=404, detail="ЖК не найден")
#     else:
#         # Если complex_id не передан, показываем обычную страницу
#         return templates.TemplateResponse("/shaxmatki/blocks.html", {
#             "request": request, 
#             "complex_id": None
#         })



# @router.get("/rassvet", response_class=HTMLResponse, name="rassvet")
# async def rassvet_page(request: Request, block: str = Query(None)):
#     """Страница ЖК Рассвет"""
#     return templates.TemplateResponse("/landing/rassvet.html", {
#         "request": request,
#         "block": block
#     })


# @router.get("/bahor", response_class=HTMLResponse, name="bahor")
# async def bahor_page(request: Request, block: str = Query(None)):
#     """Страница ЖК Бахор"""
#     return templates.TemplateResponse("/landing/bahor.html", {
#         "request": request,
#         "block": block
#     })


# @router.get("/apartments", response_class=HTMLResponse, name="apartments")
# async def apartments_page(request: Request, complex: str = Query("rassvet"), block: str = Query(None)):
#     """Страница выбора квартир"""
#     return templates.TemplateResponse("/shaxmatki/apartments.html", {
#         "request": request,
#         "complex": complex,
#         "block": block
#     })
