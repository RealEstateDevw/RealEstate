"""
Dependencies — Dependency Injection для FastAPI.

Этот модуль предоставляет функции-зависимости для FastAPI эндпоинтов.
Используется паттерн Dependency Injection для получения текущего пользователя.

НАЗНАЧЕНИЕ:
-----------
- Получение и валидация JWT токена
- Проверка прав доступа
- Извлечение данных пользователя из БД

ИСПОЛЬЗОВАНИЕ:
--------------
В FastAPI эндпоинтах эти функции используются через Depends():

    @app.get("/profile")
    def get_profile(current_user = Depends(get_current_user_from_cookie)):
        return {"user": current_user.login}

ДОСТУПНЫЕ ЗАВИСИМОСТИ:
---------------------
1. get_current_user() — получить пользователя из Authorization header
2. get_current_user_from_cookie() — получить пользователя из cookie

РАЗНИЦА:
--------
- get_current_user — для API (Bearer token в header)
- get_current_user_from_cookie — для веб-страниц (token в HTTP-only cookie)

БЕЗОПАСНОСТЬ:
-------------
- Все токены валидируются через Authlib JWT
- Проверяется срок действия (exp claim)
- Пользователь загружается из БД для актуальности данных

Автор: RealEstate CRM Team
Дата создания: 2025
"""

from datetime import datetime

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.jose import jwt, JoseError
from backend.core.auth import SECRET_KEY
from backend.database.userservice import get_user_by_login

# OAuth2 схема для Swagger UI
# tokenUrl указывает, где получить токен (для документации)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")


# =============================================================================
# ЗАВИСИМОСТЬ: ПОЛЬЗОВАТЕЛЬ ИЗ AUTHORIZATION HEADER
# =============================================================================

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Получить текущего пользователя из Authorization header.
    
    Используется для API эндпоинтов, где клиент передаёт токен
    в заголовке Authorization: Bearer {token}
    
    Процесс валидации:
    1. Извлечение токена из header (через oauth2_scheme)
    2. Декодирование JWT и проверка подписи
    3. Проверка срока действия (exp claim)
    4. Извлечение логина из sub claim
    5. Загрузка пользователя из БД
    
    Args:
        token: JWT токен из Authorization header
        
    Returns:
        User: Объект пользователя из БД (с ролью и всеми данными)
        
    Raises:
        HTTPException (401): Если токен невалиден, истёк или пользователь не найден
        
    Пример:
        >>> @app.get("/api/profile")
        >>> def get_profile(user = Depends(get_current_user)):
        ...     return {"login": user.login, "role": user.role.name}
        
    Security Note:
        Эта функция НЕ проверяет роли! Для проверки ролей используйте
        дополнительные зависимости или проверки внутри эндпоинта.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Декодирование JWT токена
        claims = jwt.decode(token, SECRET_KEY)
        
        # Проверка срока действия токена
        now_timestamp = int(datetime.utcnow().timestamp())
        claims.validate_exp(now=now_timestamp, leeway=0)
        
        # Извлечение логина из payload
        login: str = claims.get("sub")
        if login is None:
            raise credentials_exception
            
    except JoseError:
        # Токен невалиден (неправильная подпись, истёк, и т.д.)
        raise credentials_exception

    # Загрузка пользователя из БД
    user = get_user_by_login(login=login)
    if user is None:
        # Пользователь был удалён после создания токена
        raise credentials_exception
        
    return user


# =============================================================================
# ЗАВИСИМОСТЬ: ПОЛЬЗОВАТЕЛЬ ИЗ COOKIE
# =============================================================================

async def get_current_user_from_cookie(
    access_token: str = Cookie(None),
):
    """
    Получить текущего пользователя из HTTP-only cookie.
    
    Используется для веб-страниц (HTML endpoints), где токен
    хранится в HTTP-only cookie для защиты от XSS атак.
    
    Процесс валидации:
    1. Извлечение токена из cookie "access_token"
    2. Удаление префикса "Bearer " (если есть)
    3. Декодирование JWT и проверка подписи
    4. Проверка срока действия (exp claim)
    5. Извлечение логина из sub claim
    6. Загрузка пользователя из БД
    
    Args:
        access_token: JWT токен из cookie (формат: "Bearer {token}" или "{token}")
        
    Returns:
        User: Объект пользователя из БД (с ролью, leads, и т.д.)
        
    Raises:
        HTTPException (401): Если:
            - Cookie отсутствует
            - Токен невалиден или истёк
            - Пользователь не найден в БД
            
    Пример:
        >>> @app.get("/dashboard")
        >>> async def dashboard(user = Depends(get_current_user_from_cookie)):
        ...     return templates.TemplateResponse(
        ...         "dashboard.html",
        ...         {"user": user}
        ...     )
        
    Security Notes:
        - Cookie должен быть HTTP-only для защиты от XSS
        - Cookie должен быть Secure в production (только HTTPS)
        - SameSite=Lax для защиты от CSRF
        
    Cookie устанавливается при логине:
        >>> response.set_cookie(
        ...     key="access_token",
        ...     value=f"Bearer {token}",
        ...     httponly=True,
        ...     secure=True,  # в production
        ...     samesite="lax"
        ... )
    """
    # Проверка наличия cookie
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неавторизованный пользователь"
        )
    
    # Удаление префикса "Bearer " если есть
    # Cookie может содержать "Bearer {token}" или просто "{token}"
    if access_token.startswith("Bearer "):
        access_token = access_token[len("Bearer "):]
    
    try:
        # Декодирование JWT токена
        claims = jwt.decode(access_token, SECRET_KEY)
        
        # Проверка срока действия токена
        # Используем UTC timestamp для сравнения
        now = int(datetime.utcnow().timestamp())
        claims.validate_exp(now=now, leeway=0)
        
        # Извлечение логина пользователя из payload
        login = claims.get("sub")
        if login is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные данные токена"
            )
            
    except JoseError:
        # JWT невалиден (неправильная подпись, формат, или истёк)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен"
        )
    
    # Загрузка пользователя из БД
    user = get_user_by_login(login=login)
    if user is None:
        # Пользователь был удалён после создания токена
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    return user
