from datetime import timedelta

from starlette import status
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from backend.api.users.main import user_router
from backend.core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from backend.core.deps import get_current_user, get_current_user_from_cookie
from backend.database import Base, engine
from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.database.userservice import get_user_by_login

Base.metadata.create_all(bind=engine)

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc")

app.include_router(user_router)

templates = Jinja2Templates(directory="frontend")
app.mount("/media", StaticFiles(directory="media"), name="media")


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
    # Проверяем наличие пользователя по логину
    user = get_user_by_login(login=username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")

    # Генерируем JWT-токен с временем жизни ACCESS_TOKEN_EXPIRE_MINUTES
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.login}, expires_delta=access_token_expires)

    # Создаем RedirectResponse на страницу /home
    response = RedirectResponse(url="/home", status_code=status.HTTP_302_FOUND)

    # Устанавливаем токен в HTTP-only cookie (если требуется для дальнейшей авторизации)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response


# 3. Простой эндпоинт /home для отображения страницы после входа
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, current_user=Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("profile.html", {"request": request, "data": current_user})


# Эндпоинт для выхода из системы (logout)
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    # Удаляем cookie с токеном
    response.delete_cookie("access_token")
    return response
