import asyncio
from datetime import timedelta, datetime, timezone

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from authlib.jose import jwt
from fastapi.openapi.models import Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from jose import JWTError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from backend import init_roles
from backend.api.users.main import user_router
from backend.api.leads.main import router as leads_router, lead_crud
from backend.api.mop.main import router as mop_api_router
from backend.api.users.schemas import ROLE_REDIRECTS, UserRead
from backend.bot.main import run_bot
from backend.core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, SECRET_KEY, ALGORITHM
from settings import settings
from backend.core.deps import get_current_user, get_current_user_from_cookie
# from backend.core.google_sheets import schedule_lid_check, load_data_to_cache
from backend.database import Base, engine, get_db
from fastapi import FastAPI, Request, HTTPException, Form, Depends, BackgroundTasks, Body
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.core.exceptions import (
    http_exception_handler, 
    validation_exception_handler, 
    general_exception_handler
)
from backend.core.middleware import (
    LoggingMiddleware,
    SecurityHeadersMiddleware,
    DatabaseConnectionMiddleware,
    NoCacheMiddleware
)
from backend.core.static import CachedStaticFiles
from backend.core.rate_limiter import RateLimitMiddleware
from backend.core.logging_config import setup_logging
from backend.database.userservice import get_user_by_login, get_all_users
from backend.core.cache_utils import warmup_complex_caches
from config import logger, templates
from backend.crm.admin.main import router as admin_router
from backend.crm.seller.main import router as seller_router
from backend.crm.mop.main import router as mop_router
from backend.crm.finance.main import router as finance_router
from backend.api.finance.main import router as finance_api_router
from backend.crm.rop.main import router as rop_router
from backend.api.rop.main import router as rop_api_router
from backend.crm.shaxmatki.main import router as shaxmatki_router
from backend.api.complexes.main import router as shaxmatki_api_router
from backend.api.draws.main import router as draw_users_router
from backend.api.payment_options.main import router as payment_options_router
# from backend.api.excel_utils import router as excel_router
from backend.api.test_excel import router as test_excel
from backend.api.instagram.main import router as instagram_router

# Инициализация логирования
setup_logging()

app = FastAPI(
    docs_url="/api/docs", 
    redoc_url="/api/redoc",
    title="RealEstate CRM API",
    description="API для системы управления недвижимостью",
    version="1.0.0"
)

# Добавляем middleware (порядок важен!)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(NoCacheMiddleware)  # Предотвращаем кеширование API в браузере
app.add_middleware(DatabaseConnectionMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Добавляем обработчики ошибок
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(user_router)
app.include_router(leads_router)
app.include_router(admin_router)
app.include_router(seller_router)
app.include_router(mop_router)
app.include_router(mop_api_router)
app.include_router(finance_router)
app.include_router(finance_api_router)
app.include_router(rop_router)
app.include_router(rop_api_router)
app.include_router(shaxmatki_router)
app.include_router(shaxmatki_api_router)
app.include_router(draw_users_router)
app.include_router(payment_options_router)
# app.include_router(excel_router)
app.include_router(test_excel)
app.include_router(instagram_router)

app.mount(
    "/media",
    CachedStaticFiles(directory="media", cache_control="public, max-age=604800"),
    name="media"
)
app.mount(
    "/static",
    CachedStaticFiles(directory="static", cache_control="public, max-age=31536000, immutable"),
    name="static"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


#
# WEBHOOK_BASE = "https://2c67-213-230-72-140.ngrok-free.app"
# WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
# WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}"
# USED_UPDATE_TYPES: list = [
#     "message",
#     "callback_query",
#     "chat_member"
# ]


@app.on_event("startup")
async def on_startup():
    """Функция, которая выполняется при старте сервера."""
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    # Можно также выполнить первоначальную загрузку данных, если необходимо:
    Base.metadata.create_all(bind=engine)  # Создание таблиц, если их нет
    init_roles()
    try:
        await warmup_complex_caches()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Cache warmup failed: {exc}")
    asyncio.create_task(_periodic_cache_warmup())

    # Запуск Telegram бота в фоне
    if settings.BOT_TOKEN:
        asyncio.create_task(run_bot())
        logger.info("Telegram bot started in background")


async def _periodic_cache_warmup(interval_seconds: int = 900) -> None:
    """Re-populates caches on a rolling schedule to keep landing data fresh (every 15 minutes)."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await warmup_complex_caches()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Scheduled cache warmup failed: {exc}")
    # asyncio.get_event_loop().create_task(run_bot())
    # await bot.set_webhook(WEBHOOK_URL, allowed_updates=USED_UPDATE_TYPES)
    # dp.include_router(draw_router)
    # print(f"[startup] Webhook set to {WEBHOOK_URL}")
#
# bot_session = AiohttpSession()
#
#
# async def feed_update(token, update):
#     async with Bot(token, bot_session, parse_mode="HTML").context(auto_close=False) as bot_:
#         await dp.feed_raw_update(bot_, update)
#
#
#
# @app.post(WEBHOOK_PATH, include_in_schema=False)
# async def telegram_update(token: str, background_tasks: BackgroundTasks,
#                           update: dict = Body(...)) -> Response:
#     print("here")
#     if token == bot.token:
#         background_tasks.add_task(feed_update, token, update)
#         return Response(status_code=status.HTTP_202_ACCEPTED)
#     return Response(status_code=status.HTTP_401_UNAUTHORIZED)


# asyncio.create_task(schedule_lid_check(60, 60))
# await load_data_to_cache()


# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Перенаправляем на главную страницу выбора ЖК
    return templates.TemplateResponse("/landing/index.html", {"request": request})

@app.get("/rassvet", response_class=HTMLResponse)
async def rassvet_landing(request: Request):
    # Страница ЖК Рассвет
    return templates.TemplateResponse("/landing/rassvet.html", {"request": request})

@app.get("/bahor", response_class=HTMLResponse)
async def bahor_landing(request: Request):
    # Страница ЖК Бахор
    return templates.TemplateResponse("/landing/bahor.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login_form.html", {"request": request})


@app.post("/login")
async def login(
        username: str = Form(...),
        password: str = Form(...),
):
    logger.info(f"Login attempt for user: {username}")

    user = get_user_by_login(login=username)
    if not user or not verify_password(password, user.hashed_password):
        logger.info("Invalid credentials")
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")

    token = create_access_token(
        data={"sub": user.login, "role_id": user.role_id},
        expires_delta=timedelta(minutes=60)
    )
    logger.info(f"Token generated: {token[:20]}...")

    redirect_url = ROLE_REDIRECTS.get(
        user.role_id,
        "/dashboard/default"
    )
    logger.info(f"Redirect URL: {redirect_url}")

    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER
    )

    # Устанавливаем токен в куки
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,
        samesite="lax"  # Добавляем это для лучшей совместимости с редиректами
    )

    return response


@app.get("/profile", response_class=HTMLResponse, name="user_profile")
async def home(request: Request, current_user=Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


@app.get("/user/me", response_model=UserRead)
async def read_users_me(current_user=Depends(get_current_user_from_cookie)):
    return current_user


# Эндпоинт для выхода из системы (logout)
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    # Удаляем cookie с токеном
    response.delete_cookie("access_token")
    return response


# @app.middleware("http")
# async def auth_middleware(request: Request, call_next):
#     path = request.url.path
#     logger.info(f"Request path: {path}")

#     # --- Публичные пути ---
#     # Пути, которые НЕ требуют аутентификации
#     # Используем startswith для /static и /docs и т.д.
#     public_paths_exact = {"/", "/login", "/register", "/api/auth/login", "/api/auth/register", "/complexes", "/rassvet", "/bahor"}
#     public_paths_startswith = {"/static", "/docs",
#                                "/openapi.json", "/complexes", "/api/complexes",
#                                "/excel", "/shaxmatki", "/api/shaxmatki",
#                                "/webhook", "/api/payment-options"}  # Добавь сюда /docs и /openapi.json, если используешь Swagger/OpenAPI UI

#     is_public = False
#     if path in public_paths_exact:
#         is_public = True
#     else:
#         for public_prefix in public_paths_startswith:
#             if path.startswith(public_prefix):
#                 is_public = True
#                 break

#     if is_public:
#         logger.info(f"Public path accessed: {path}")
#         response = await call_next(request)
#         return response

#     # --- Логика для защищенных путей ---
#     token = request.cookies.get("access_token")
#     logger.info(f"Cookie token: {'Token found' if token else 'No token'}")  # Не логируй сам токен целиком в продакшене

#     if not token:
#         logger.info("No token found for protected path, redirecting to login")
#         return RedirectResponse(url="/login", status_code=303)

#     try:
#         # Извлекаем токен из формата "Bearer {token}", если он есть
#         # В твоем случае токен берется из cookie, префикс "Bearer " маловероятен,
#         # но оставим на всякий случай, если источник токена изменится.
#         if token.startswith("Bearer "):
#             token = token.split(" ")[1]
#             logger.info("Extracted token from Bearer format.")

#         # Проверяем токен
#         payload = jwt.decode(
#             token,
#             SECRET_KEY
#         )
#         logger.info(f"Token payload: {payload}")  # Будь осторожен с логированием payload в продакшене

#         # Проверяем срок действия (exp)
#         exp = payload.get("exp")
#         # Используем timezone-aware datetime для корректного сравнения
#         current_time = datetime.now(timezone.utc).timestamp()

#         # Логируем время для отладки
#         logger.debug(f"Token expires at (timestamp): {exp}")
#         logger.debug(f"Current time (timestamp): {current_time}")
#         if exp:
#             logger.info(f"Token expires at (datetime): {datetime.fromtimestamp(exp, timezone.utc)}")
#             logger.info(f"Current time (datetime): {datetime.fromtimestamp(current_time, timezone.utc)}")

#         # if not exp or exp < current_time:
#         #     logger.info("Token expired")
#         #     response = RedirectResponse(url="/login", status_code=303)
#         #     response.delete_cookie("access_token", path="/", domain=None, secure=True, httponly=True)  # Указывай параметры cookie для надежного удаления
#         #     return response

#         # Добавляем информацию о пользователе в request.state для использования в эндпоинтах
#         request.state.user = payload
#         logger.info("Token validated successfully")

#         # Передаем запрос дальше по цепочке (к эндпоинту или другому middleware)
#         response = await call_next(request)
#         return response

#     except JWTError as e:
#         logger.error(f"JWT Error: {str(e)}")
#         # Если токен невалиден (ошибка подписи, неверный формат и т.д.), перенаправляем на логин
#         response = RedirectResponse(url="/login", status_code=303)
#         response.delete_cookie("access_token", path="/", domain=None, secure=True,
#                                httponly=True)  # Удаляем невалидный куки
#         return response

#     except Exception as e:
#         # Ловим другие возможные ошибки во время обработки
#         logger.error(f"Auth middleware error: {str(e)}", exc_info=True)  # exc_info=True добавит traceback в лог
#         # В случае неожиданной ошибки лучше вернуть 500 или перенаправить на страницу ошибки,
#         # но для простоты пока оставим редирект на логин.
#         # Consider returning Response("Internal Server Error", status_code=500)
#         response = RedirectResponse(url="/login", status_code=303)  # Или на страницу ошибки
#         response.delete_cookie("access_token", path="/", domain=None, secure=True, httponly=True,
#                                samesite='Lax')  # Попытаемся удалить куки на всякий случай
#         return response
