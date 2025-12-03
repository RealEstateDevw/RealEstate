"""
Модуль аутентификации и безопасности

Этот модуль отвечает за:
- Хеширование и проверку паролей (bcrypt)
- Создание и валидацию JWT токенов (Authlib)
- Управление сессиями пользователей

ВАЖНО: Используется библиотека Authlib (НЕ python-jose!) для работы с JWT.
Это критично для совместимости с остальной частью приложения.

Конфигурация:
- SECRET_KEY: Секретный ключ для подписи токенов (из .env)
- ALGORITHM: Алгоритм подписи (по умолчанию HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES: Время жизни токена в минутах

Пример использования:
    from backend.core.auth import create_access_token, verify_password

    # Проверка пароля при логине
    if verify_password(plain_password, user.hashed_password):
        token = create_access_token(data={"sub": user.login, "role_id": user.role_id})

    # Хеширование при регистрации
    hashed = get_password_hash("user_password")
"""

from datetime import datetime, timedelta
from typing import Optional
from authlib.jose import jwt
from authlib.jose.errors import JoseError
from passlib.context import CryptContext
from settings import settings

# =============================================================================
# НАСТРОЙКИ БЕЗОПАСНОСТИ
# =============================================================================

# Загружаем настройки из переменных окружения (.env файл)
# ВАЖНО: В production обязательно измените SECRET_KEY на случайную строку!
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM  # HS256 - HMAC с SHA-256
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Контекст для работы с паролями
# bcrypt - криптографически стойкий алгоритм хеширования
# "deprecated=auto" - автоматически обновляет устаревшие хеши
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# РАБОТА С ПАРОЛЯМИ
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие открытого пароля и хеша.

    Используется при логине для проверки введенного пароля против
    хеша, сохраненного в базе данных.

    Args:
        plain_password: Пароль в открытом виде (от пользователя)
        hashed_password: Bcrypt хеш из базы данных

    Returns:
        bool: True если пароль верный, False иначе

    Example:
        user = get_user_by_login("john")
        if verify_password("secret123", user.hashed_password):
            # Пароль верный, можно создавать токен
            pass
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Создает bcrypt хеш для пароля.

    Используется при регистрации пользователя или смене пароля.
    Bcrypt автоматически генерирует соль (salt) для каждого пароля.

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Bcrypt хеш (начинается с $2b$)

    Example:
        hashed = get_password_hash("user_password")
        new_user = User(login="john", hashed_password=hashed)

    Security Note:
        Никогда не храните пароли в открытом виде!
        Всегда используйте эту функцию перед сохранением в БД.
    """
    return pwd_context.hash(password)


# =============================================================================
# JWT ТОКЕНЫ
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT токен с заданными данными и временем жизни.

    JWT (JSON Web Token) используется для stateless аутентификации.
    Токен содержит информацию о пользователе и подписывается SECRET_KEY.

    ВАЖНО: Используется библиотека Authlib, не python-jose!

    Структура токена:
        Header: {"alg": "HS256"}
        Payload: {
            "sub": "user_login",      # Subject - логин пользователя
            "role_id": 1,              # ID роли пользователя
            "exp": 1234567890          # Expiration - timestamp истечения
        }
        Signature: HMACSHA256(header + payload, SECRET_KEY)

    Args:
        data: Данные для включения в токен (обычно sub и role_id)
        expires_delta: Время жизни токена (если None, используется настройка)

    Returns:
        str: JWT токен в формате "xxxxx.yyyyy.zzzzz"

    Example:
        # При логине
        token = create_access_token(
            data={"sub": user.login, "role_id": user.role_id},
            expires_delta=timedelta(hours=24)
        )
        # Токен сохраняется в HTTP-only cookie

    Security Notes:
        - Токен подписан, но не зашифрован (не храните секреты в payload!)
        - Клиент не может изменить токен без нарушения подписи
        - После истечения (exp) токен становится невалидным
    """
    # Копируем данные, чтобы не изменять оригинал
    to_encode = data.copy()

    # Вычисляем время истечения токена
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Используем значение по умолчанию из настроек
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Добавляем exp (expiration) в payload
    # ВАЖНО: Authlib требует timestamp (float), не datetime объект!
    to_encode.update({"exp": expire.timestamp()})

    # Создаем заголовок токена с алгоритмом подписи
    header = {"alg": ALGORITHM}

    # Кодируем токен: header + payload + signature
    token = jwt.encode(header, to_encode, SECRET_KEY)

    # Authlib может вернуть bytes или str в зависимости от версии
    # Приводим к строке для совместимости
    return token.decode("utf-8") if isinstance(token, bytes) else token
