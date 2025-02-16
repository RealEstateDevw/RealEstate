from datetime import timedelta, datetime

from authlib.jose import jwt
from fastapi.openapi.models import Response
from jose import JWTError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend import init_roles
from backend.api.users.main import user_router
from backend.api.leads.main import router as leads_router, lead_crud
from backend.api.users.schemas import ROLE_REDIRECTS, UserRead
from backend.core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, SECRET_KEY, ALGORITHM
from backend.core.deps import get_current_user, get_current_user_from_cookie
from backend.database import Base, engine, get_db
from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.database.attendanceservice import has_user_checked_in, register_attendance
from backend.database.userservice import get_user_by_login, get_all_users
from config import logger

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc")

app.include_router(user_router)
app.include_router(leads_router)

templates = Jinja2Templates(directory="frontend")
app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Функция, которая выполняется при старте сервера."""
    Base.metadata.create_all(bind=engine)  # Создание таблиц, если их нет
    init_roles()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return """
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Login Form</title>
      </head>
      <body>
        <h2>Вход в систему</h2>
        <!-- Форма отправляет данные методом POST на эндпоинт /token -->
        <form action="/login" method="post">
          <label for="username">Логин:</label>
          <input type="text" id="username" name="username" required>
          <br><br>
          <label for="password">Пароль:</label>
          <input type="password" id="password" name="password" required>
          <br><br>
          <button type="submit">Войти</button>
        </form>
      </body>
    </html>
    """


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
    logger.info("Cookie set in response")

    return response
    # # Проверяем наличие пользователя по логину
    # user = get_user_by_login(login=username)
    # if not user or not verify_password(password, user.hashed_password):
    #     raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    #
    # # Генерируем JWT-токен с временем жизни ACCESS_TOKEN_EXPIRE_MINUTES
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # token = create_access_token(data={"sub": user.login, "role_id": user.role_id}, expires_delta=timedelta(minutes=60))
    # redirect_url = ROLE_REDIRECTS.get(
    #     user.role_id,
    #     "/dashboard/default"  # Дефолтный редирект если роль не найдена
    # )
    # response = RedirectResponse(
    #     url=redirect_url,
    #     status_code=status.HTTP_303_SEE_OTHER  # Более правильный код для редиректа после POST
    # )
    #
    # # Устанавливаем токен в HTTP-only cookie (если требуется для дальнейшей авторизации)
    # response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    # return response


# 3. Простой эндпоинт /home для отображения страницы после входа
@app.get("/profile", response_class=HTMLResponse)
async def home(request: Request, current_user=Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


@app.get("/user/me", response_model=UserRead)
async def read_users_me(current_user=Depends(get_current_user_from_cookie)):
    return current_user


@app.get("/dashboard/sales", response_class=HTMLResponse, name="sales_dashboard")
async def sales_dashboard(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role_id != 1:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/sales-dashboard.html", {"request": request, "user": current_user})


@app.get("/dashboard/sales/add-lead", response_class=HTMLResponse)
async def add_lead(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role_id != 1:
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/add-lead-sales.html", {"request": request, "user": current_user})


@app.get("/dashboard/lead/{lead_id}", response_class=HTMLResponse)
async def lead(request: Request, lead_id: int, current_user=Depends(get_current_user_from_cookie),
               db: Session = Depends(get_db)):
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not has_user_checked_in(current_user.id):
        # Если пользователь ещё не зашел сегодня, регистрируем вход
        register_attendance(current_user.id, "check_in")
    return templates.TemplateResponse("/seller/exact_lead.html", {"request": request, "user": current_user, "lead": db_lead})


@app.get("/dashboard/admin", response_class=HTMLResponse)
async def admin(request: Request, current_user=Depends(get_current_user_from_cookie), all_users=Depends(get_all_users)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/admin/main_admin.html",
                                      {"request": request, "user": current_user, "all_users": all_users})


@app.get("/dashboard/admin/add_user", response_class=HTMLResponse)
async def add_user(request: Request, current_user=Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        return templates.TemplateResponse("index.html", {"request": request, "user": current_user})
    return templates.TemplateResponse("/seller/register-employer.html", {"request": request, "user": current_user})


# Эндпоинт для выхода из системы (logout)
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    # Удаляем cookie с токеном
    response.delete_cookie("access_token")
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.cookies.get("access_token")
    logger.info(f"Request path: {request.url.path}")
    logger.info(f"Cookie token: {token}")

    public_paths = ["/login", "/register", "/api/auth/login", "/api/auth/register", "/static"]

    if request.url.path in public_paths:
        logger.info(f"Public path accessed: {request.url.path}")
        return await call_next(request)

    if not token:
        logger.info("No token found, redirecting to login")
        return RedirectResponse(url="/login", status_code=303)

    try:
        # Извлекаем токен из формата "Bearer {token}"
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            logger.info(f"Extracted token: {token[:20]}...")

        # Проверяем токен
        payload = jwt.decode(token, SECRET_KEY)
        logger.info(f"Token payload: {payload}")

        # Проверяем срок действия
        exp = payload.get("exp")
        current_time = datetime.utcnow().timestamp()

        print(f"Token expires at: {exp}, current time: {current_time}")

        if exp and exp < current_time:
            logger.info("Token expired")
            response = RedirectResponse(url="/login", status_code=303)
            response.delete_cookie("access_token")
            return response

        # Добавляем информацию о пользователе в request.state
        request.state.user = payload
        logger.info("Token validated successfully")
        return await call_next(request)

    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("access_token")
        return response

    except Exception as e:
        logger.error(f"Auth middleware error: {str(e)}", exc_info=True)
        return RedirectResponse(url="/login", status_code=303)
