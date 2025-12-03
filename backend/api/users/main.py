"""
Users API — REST API для управления пользователями.

НАЗНАЧЕНИЕ:
-----------
Этот модуль предоставляет эндпоинты для:
- Регистрации новых пользователей (сотрудников)
- Аутентификации и получения JWT токенов
- Управления профилями пользователей
- Управления ролями
- Смены и сброса паролей
- Интеграции с Telegram ботом

АРХИТЕКТУРА:
------------
Router → CRUD (userservice.py) → Models → Database

ОСНОВНЫЕ СУЩНОСТИ:
------------------
- User — пользователь системы (сотрудник)
- Role — роль пользователя (Админ, Продажник, МОП, РОП, Финансист)
- TelegramAccount — привязанный Telegram аккаунт

БЕЗОПАСНОСТЬ:
-------------
- Пароли хешируются через bcrypt
- JWT токены для аутентификации
- Валидация всех входных данных через Pydantic

ИСПОЛЬЗОВАНИЕ:
--------------
Все эндпоинты доступны по префиксу /api/users/

Примеры:
    POST /api/users/add_user — регистрация
    POST /api/users/token — логин
    GET /api/users/me — текущий пользователь
    GET /api/users/employees — список сотрудников
    POST /api/users/change-password — смена пароля
    DELETE /api/users/delete_user — удаление

Автор: RealEstate CRM Team
Дата создания: 2025
"""

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
from backend.api.users.schemas import UserCreate, UserRead, Token, UserUpdate, PasswordChange
from backend.core.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, get_password_hash

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

user_router = APIRouter(prefix="/api/users")


# =============================================================================
# РЕГИСТРАЦИЯ И АУТЕНТИФИКАЦИЯ
# =============================================================================

@user_router.post("/add_user", response_model=UserRead)
async def register_user(user: UserCreate):
    """
    Регистрация нового пользователя (сотрудника) в системе.
    
    Доступно только администраторам.
    
    Процесс:
    1. Проверка уникальности логина
    2. Хеширование пароля
    3. Создание пользователя в БД
    4. Возврат данных созданного пользователя
    
    Args:
        user: Данные нового пользователя (UserCreate)
            - login: Уникальный логин
            - password: Пароль (будет захеширован)
            - first_name, last_name: ФИО
            - email: Email
            - phone: Телефон
            - role_id: ID роли (1-Админ, 2-Продажник, и т.д.)
            - work_start_time, work_end_time: Рабочее время
            - work_days: Рабочие дни (JSON массив)
            
    Returns:
        UserRead: Данные созданного пользователя с ролью
        
    Raises:
        HTTPException (400): Если логин уже существует
        HTTPException (500): Если ошибка создания в БД
        
    Пример запроса:
        >>> POST /api/users/add_user
        >>> {
        ...   "login": "ivanov",
        ...   "password": "SecurePass123",
        ...   "first_name": "Иван",
        ...   "last_name": "Иванов",
        ...   "email": "ivanov@company.com",
        ...   "phone": "+998901234567",
        ...   "role_id": 2,
        ...   "work_start_time": "09:00",
        ...   "work_end_time": "18:00",
        ...   "work_days": ["ПН", "ВТ", "СР", "ЧТ", "ПТ"]
        ... }
        
    Пример ответа:
        >>> {
        ...   "id": 5,
        ...   "login": "ivanov",
        ...   "first_name": "Иван",
        ...   "last_name": "Иванов",
        ...   "email": "ivanov@company.com",
        ...   "role": "Продажник",
        ...   "role_id": 2
        ... }
        
    Security Note:
        Пароль автоматически хешируется через bcrypt.
        В БД никогда не хранится открытый пароль!
    """
    try:
        # Проверка существования пользователя с таким логином
        if get_user_by_login(login=user.login):
            raise HTTPException(status_code=400, detail="Логин уже зарегистрирован")

        # Хеширование пароля
        user_data = user.model_dump()
        user_data["hashed_password"] = get_password_hash(user.hashed_password)

        # Создание нового пользователя в БД
        new_user = add_user(UserCreate(**user_data))
        
        if new_user is None:
            raise HTTPException(status_code=500, detail="Ошибка при создании пользователя")
        
        # Формирование ответа с информацией о роли
        return {
            **new_user.__dict__,
            "role": new_user.role.name if new_user.role else None,
            "role_id": new_user.role_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании пользователя: {str(e)}")


@user_router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Аутентификация пользователя и выдача JWT токена.
    
    Используется для логина через API (Bearer token в Authorization header).
    Для веб-интерфейса используйте /login (возвращает HTTP-only cookie).
    
    Процесс:
    1. Поиск пользователя по логину
    2. Проверка пароля
    3. Генерация JWT токена
    4. Возврат токена клиенту
    
    Args:
        form_data: OAuth2 форма с username и password
            - username: Логин пользователя
            - password: Пароль в открытом виде
            
    Returns:
        Token: JWT токен и его тип
            - access_token: JWT токен (строка)
            - token_type: "bearer"
            
    Raises:
        HTTPException (400): Если логин или пароль неверны
        
    Пример запроса:
        >>> POST /api/users/token
        >>> Content-Type: application/x-www-form-urlencoded
        >>> username=ivanov&password=SecurePass123
        
    Пример ответа:
        >>> {
        ...   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ...   "token_type": "bearer"
        ... }
        
    Использование токена:
        >>> GET /api/users/me
        >>> Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        
    Security Notes:
        - Токен содержит только логин (sub claim) и срок действия (exp)
        - Токен подписан SECRET_KEY и не может быть подделан
        - Срок действия: ACCESS_TOKEN_EXPIRE_MINUTES (из .env)
    """
    # Поиск пользователя по логину
    user = get_user_by_login(login=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    
    # Проверка пароля
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")

    # Генерация JWT токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login},  # sub — стандартное поле JWT для идентификатора пользователя
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# =============================================================================
# ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
# =============================================================================

@user_router.get("/me", response_model=UserRead)
async def read_users_me(current_user: UserRead = Depends(get_current_user)):
    """
    Получить информацию о текущем аутентифицированном пользователе.
    
    Требует JWT токен в Authorization header.
    
    Args:
        current_user: Автоматически извлекается из токена через Depends(get_current_user)
        
    Returns:
        UserRead: Данные текущего пользователя
        
    Пример запроса:
        >>> GET /api/users/me
        >>> Authorization: Bearer {token}
        
    Пример ответа:
        >>> {
        ...   "id": 5,
        ...   "login": "ivanov",
        ...   "first_name": "Иван",
        ...   "last_name": "Иванов",
        ...   "email": "ivanov@company.com",
        ...   "phone": "+998901234567",
        ...   "role": "Продажник",
        ...   "role_id": 2,
        ...   "work_start_time": "09:00",
        ...   "work_end_time": "18:00"
        ... }
    """
    return current_user


@user_router.get("/get_user_by_id")
async def get_user_by_id_api(user_id: int):
    """
    Получить пользователя по его ID.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        User: Объект пользователя из БД
        
    Raises:
        HTTPException (404): Если пользователь не найден
        
    Пример:
        >>> GET /api/users/get_user_by_id?user_id=5
    """
    user = get_user_by_id(user_id)
    return user


@user_router.get("/get_all_users")
async def get_all_users_api():
    """
    Получить список всех пользователей системы.
    
    Доступно только администраторам и руководителям.
    
    Returns:
        List[User]: Список всех пользователей
        
    Пример:
        >>> GET /api/users/get_all_users
        >>> [
        ...   {"id": 1, "login": "admin", "role": "Админ"},
        ...   {"id": 2, "login": "seller1", "role": "Продажник"},
        ...   ...
        ... ]
    """
    users = get_all_users()
    return users


@user_router.get("/employees", response_model=List[UserRead])
async def get_employees(role_id: Optional[int] = Query(None)):
    """
    Получить список сотрудников с фильтрацией по роли.
    
    Если роль не указана, возвращаются все сотрудники.
    
    Args:
        role_id: ID роли для фильтрации (опционально)
            1 — Админ
            2 — Продажник
            3 — Финансист
            4 — МОП
            5 — РОП
            
    Returns:
        List[UserRead]: Список сотрудников
        
    Примеры:
        >>> GET /api/users/employees
        >>> # Все сотрудники
        
        >>> GET /api/users/employees?role_id=2
        >>> # Только продажники
    """
    if role_id:
        return get_by_role_employees(role_id=role_id)
    return get_all_users()


# =============================================================================
# УПРАВЛЕНИЕ РОЛЯМИ
# =============================================================================

@user_router.post("/add_role")
async def add_role_to_user(role_name: str):
    """
    Добавить новую роль в систему.
    
    ВНИМАНИЕ: Обычно роли создаются при инициализации БД.
    Этот эндпоинт используется редко.
    
    Args:
        role_name: Название роли
        
    Returns:
        Role: Созданная роль
        
    Пример:
        >>> POST /api/users/add_role?role_name=Новая%20роль
    """
    new_role = add_role(role_name)
    return new_role


@user_router.get("/roles")
async def get_roles():
    """
    Получить список всех ролей в системе.
    
    Returns:
        List[Role]: Список ролей
        
    Пример ответа:
        >>> [
        ...   {"id": 1, "name": "Админ", "description": "Администратор"},
        ...   {"id": 2, "name": "Продажник", "description": "Менеджер по продажам"},
        ...   ...
        ... ]
    """
    roles = get_all_roles()
    return roles


# =============================================================================
# ОБНОВЛЕНИЕ И УДАЛЕНИЕ
# =============================================================================

@user_router.patch("/update_user")
async def update_user_api(user_id: int, user: UserUpdate):
    """
    Обновить данные пользователя.
    
    Можно обновить любые поля кроме пароля (для пароля используйте /change-password).
    
    Args:
        user_id: ID пользователя для обновления
        user: Данные для обновления (все поля опциональные)
            - first_name, last_name
            - email, phone
            - role_id
            - work_start_time, work_end_time
            - work_days
            
    Returns:
        User: Обновлённый пользователь
        
    Пример:
        >>> PATCH /api/users/update_user?user_id=5
        >>> {
        ...   "first_name": "Новое имя",
        ...   "email": "newemail@company.com"
        ... }
    """
    user = update_user(user_id, user)
    return user


@user_router.delete("/delete_user")
async def delete_user_api(user_id: int):
    """
    Удалить пользователя из системы.
    
    ВНИМАНИЕ: Это удаление из БД. Используйте с осторожностью!
    Рекомендуется вместо удаления деактивировать пользователя.
    
    Args:
        user_id: ID пользователя для удаления
        
    Returns:
        dict: Результат операции
        
    Raises:
        HTTPException (404): Если пользователь не найден
        
    Пример:
        >>> DELETE /api/users/delete_user?user_id=5
    """
    user = delete_user(user_id)
    return user


# =============================================================================
# УПРАВЛЕНИЕ ПАРОЛЯМИ
# =============================================================================

@user_router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user_from_cookie)
):
    """
    Смена пароля пользователем (самостоятельно).
    
    Требует знания текущего пароля для подтверждения.
    
    Args:
        password_data: Данные для смены пароля
            - current_password: Текущий пароль
            - new_password: Новый пароль (минимум 6 символов)
        current_user: Текущий пользователь (из cookie)
        
    Returns:
        dict: Сообщение об успехе
        
    Raises:
        HTTPException (400): Если текущий пароль неверный или новый слишком короткий
        HTTPException (500): Если ошибка обновления в БД
        
    Пример запроса:
        >>> POST /api/users/change-password
        >>> {
        ...   "current_password": "OldPass123",
        ...   "new_password": "NewSecurePass456"
        ... }
        
    Пример ответа:
        >>> {"message": "Пароль успешно изменен"}
        
    Security Notes:
        - Требует аутентификации (cookie)
        - Проверяет текущий пароль
        - Минимальная длина нового пароля: 6 символов
        - Новый пароль хешируется через bcrypt
    """
    # Проверка текущего пароля
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Валидация нового пароля
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен содержать минимум 6 символов"
        )
    
    # Хеширование нового пароля
    hashed_password = get_password_hash(password_data.new_password)
    
    # Обновление в БД
    user_update = UserUpdate(password=hashed_password)
    updated_user = update_user(current_user.id, user_update)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении пароля"
        )
    
    return {"message": "Пароль успешно изменен"}


@user_router.post("/reset_password")
async def reset_password(user_id: int, db: Session = Depends(get_db)):
    """
    Сброс пароля пользователя администратором.
    
    Доступно только администраторам.
    Устанавливает временный пароль "qwerty123".
    
    Args:
        user_id: ID пользователя, чей пароль нужно сбросить
        db: Сессия БД (автоматически)
        
    Returns:
        dict: Сообщение об успехе с временным паролем
        
    Raises:
        HTTPException (404): Если пользователь не найден
        
    Пример запроса:
        >>> POST /api/users/reset_password?user_id=5
        
    Пример ответа:
        >>> {
        ...   "message": "Пароль успешно сброшен",
        ...   "temporary_password": "qwerty123",
        ...   "user_id": 5,
        ...   "user_login": "ivanov"
        ... }
        
    ВАЖНО: Пользователь должен сменить временный пароль после первого входа!
    
    TODO: 
        - Генерировать случайный временный пароль
        - Отправлять пароль на email
        - Требовать смену пароля при первом входе
    """
    # Поиск пользователя
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Установка временного пароля
    temporary_password = "qwerty123"
    user.hashed_password = get_password_hash(temporary_password)

    # Сохранение в БД
    db.commit()

    return {
        "message": "Пароль успешно сброшен",
        "temporary_password": temporary_password,
        "user_id": user.id,
        "user_login": user.login
    }


# =============================================================================
# СТАТИСТИКА И АНАЛИТИКА
# =============================================================================

@user_router.get("/sales/stats")
async def get_sales_stats(
        user_id: Optional[int] = Query(None),
        db: Session = Depends(get_db)
):
    """
    Получить статистику продаж пользователя.
    
    Показывает:
    - Количество лидов
    - Количество закрытых сделок
    - Общую сумму продаж
    - Конверсию
    
    Args:
        user_id: ID пользователя (если None — статистика по всем)
        db: Сессия БД (автоматически)
        
    Returns:
        dict: Статистика продаж
        
    Пример ответа:
        >>> {
        ...   "user_id": 5,
        ...   "leads_count": 50,
        ...   "closed_deals": 12,
        ...   "total_sales": 600000,
        ...   "conversion_rate": 0.24
        ... }
    """
    service = SalesLeadsService(db)
    return service.get_sales_stats(user_id)


# =============================================================================
# ИНТЕГРАЦИЯ С TELEGRAM
# =============================================================================

@user_router.get("/{user_id}/link-telegram")
async def link_telegram(user_id: int, db: Session = Depends(get_db)):
    """
    Создать deep-link для привязки Telegram аккаунта.
    
    Процесс:
    1. Пользователь открывает эту ссылку
    2. Перенаправляется в Telegram бота
    3. Бот регистрирует связь пользователя с Telegram
    4. Пользователь получает уведомления в Telegram
    
    Args:
        user_id: ID пользователя CRM
        db: Сессия БД (автоматически)
        
    Returns:
        RedirectResponse: Перенаправление на Telegram бота
        
    Raises:
        HTTPException (404): Если пользователь не найден
        
    Пример:
        >>> GET /api/users/5/link-telegram
        >>> # Перенаправление на https://t.me/DxBotru_bot?start=sales_5
        
    Формат deep-link:
        https://t.me/{bot_username}?start=sales_{user_id}
        
    Бот должен обработать параметр start и создать запись в TelegramAccount.
    """
    # Проверка существования пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    
    # Формирование deep-link
    bot_username = "DxBotru_bot"  # TODO: Вынести в настройки
    param = f"sales_{user_id}"
    deep_link = f"https://t.me/{bot_username}?start={param}"
    
    return RedirectResponse(url=deep_link, status_code=302)
