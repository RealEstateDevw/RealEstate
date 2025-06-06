from datetime import timedelta, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, Query, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse

from backend.core.deps import get_current_user, get_current_user_from_cookie
from backend.database import get_db
from backend.database.models import User, TelegramAccount, TelegramRole
from backend.database.sales_service.crud import SalesLeadsService
from backend.database.userservice import add_user, get_user_by_login, add_role, get_user_by_id, get_all_users, \
    update_user, get_by_role_employees, get_all_roles, delete_user
from backend.api.users.schemas import UserCreate, UserRead, Token, UserUpdate
from backend.core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, get_password_hash

user_router = APIRouter(prefix="/api/users")


@user_router.post("/add_user", response_model=UserRead)
async def register_user(user: UserCreate):
    # Проверяем, существует ли уже пользователь с таким логином
    if get_user_by_login(login=user.login):
        raise HTTPException(status_code=400, detail="Логин уже зарегистрирован")

    # Хешируем пароль и добавляем его в данные для создания пользователя
    # (это временное расширение объекта user, можно создать dict и добавить туда значение)
    user_data = user.model_dump()
    user_data["hashed_password"] = get_password_hash(user.hashed_password)
    # Можно удалить открытый пароль, если не нужен
    # del user_data["password"]

    # Создаём нового пользователя
    # Обратите внимание, что функция add_user ожидает объект, у которого есть атрибут hashed_password.

    new_user = add_user(UserCreate(**user_data))
    return {
        **new_user.__dict__,
        "role": new_user.role.name if new_user.role else None,  # Возвращаем название роли, если оно есть
        "role_id": new_user.role_id
    }


@user_router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = get_user_by_login(login=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login},  # В поле sub обычно помещается уникальный идентификатор пользователя
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@user_router.get("/me", response_model=UserRead)
async def read_users_me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@user_router.post("/add_role")
async def add_role_to_user(role_name: str):
    new_role = add_role(role_name)
    return new_role


@user_router.get("/get_user_by_id")
async def get_user_by_id_api(user_id: int):
    user = get_user_by_id(user_id)
    return user


@user_router.get("/get_all_users")
async def get_all_users_api():
    users = get_all_users()
    return users


@user_router.patch("/update_user")
async def update_user_api(user_id: int, user: UserUpdate):
    user = update_user(user_id, user)
    return user


@user_router.get("/employees", response_model=List[UserRead])
async def get_employees(role_id: Optional[int] = Query(None)):
    """
    Эндпоинт для получения списка сотрудников с фильтрацией по должности (role).
    Если роль не указана, возвращаем всех сотрудников.
    """
    if role_id:
        return get_by_role_employees(role_id=role_id)
    return get_all_users()


@user_router.get("/roles")
async def get_roles():
    roles = get_all_roles()
    return roles


@user_router.delete("/delete_user")
async def delete_user_api(user_id: int):
    user = delete_user(user_id)
    return user


@user_router.post("/reset_password")
async def reset_password(user_id: int, db: Session = Depends(get_db)):
    # Находим пользователя по user_id
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Назначаем временный пароль и хешируем его
    temporary_password = "qwerty123"
    user.hashed_password = get_password_hash(temporary_password)

    # Сохраняем изменения в базе данных
    db.commit()

    return {
        "message": "Пароль успешно сброшен",
        "temporary_password": temporary_password,
        "user_id": user.id,
        "user_login": user.login
    }


@user_router.get("/sales/stats")
async def get_sales_stats(
        user_id: Optional[int] = Query(None),
        db: Session = Depends(get_db)
):
    service = SalesLeadsService(db)
    return service.get_sales_stats(user_id)


@user_router.get("/{user_id}/link-telegram")
async def link_telegram(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    # Формируем deep-link. Параметр start будет 'crm_<user_id>'
    bot_username = "DxBotru_bot"  # <-- замените на реальное имя вашего бота
    param = f"sales_{user_id}"
    deep_link = f"https://t.me/DxBotru_bot?start={param}"
    return RedirectResponse(url=deep_link, status_code=302)
