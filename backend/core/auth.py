from datetime import datetime, timedelta
from typing import Optional
from authlib.jose import jwt
from authlib.jose.errors import JoseError
from passlib.context import CryptContext
from settings import settings

# Используем настройки из переменных окружения
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие открытого пароля и хеша."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Возвращает хеш пароля."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт JWT-токен с указанными данными и временем жизни.
    В Authlib значение `exp` должно быть представлено как timestamp (целое число).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    header = {"alg": ALGORITHM}
    token = jwt.encode(header, to_encode, SECRET_KEY)
    # Если токен возвращается в виде байтов, декодируем в строку
    return token.decode("utf-8") if isinstance(token, bytes) else token
