from datetime import datetime

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.jose import jwt, JoseError
from backend.core.auth import SECRET_KEY
from backend.database.userservice import get_user_by_login

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Декодирует JWT-токен, проверяет его срок действия и извлекает из него идентификатор пользователя.
    Если токен недействителен или не содержит нужной информации, выбрасывается HTTPException.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(token, SECRET_KEY)
        now_timestamp = int(datetime.utcnow().timestamp())
        claims.validate_exp(now=now_timestamp, leeway=0)  # Проверка срока годности токена
        login: str = claims.get("sub")
        if login is None:
            raise credentials_exception
    except JoseError:
        raise credentials_exception

    user = get_user_by_login(login=login)
    if user is None:
        raise credentials_exception
    return user




async def get_current_user_from_cookie(
        access_token: str = Cookie(None),
):
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неавторизованный пользователь"
        )
    # Если в cookie хранится строка с префиксом "Bearer ", удаляем его:
    if access_token.startswith("Bearer "):
        access_token = access_token[len("Bearer "):]
    try:
        # Декодируем токен
        claims = jwt.decode(access_token, SECRET_KEY)
        # Преобразуем текущее время в числовой timestamp:
        now = int(datetime.utcnow().timestamp())
        # Проверяем срок действия токена; leeway можно задать в секундах (например, 10)
        claims.validate_exp(now=now, leeway=0)
        login = claims.get("sub")
        if login is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные данные токена"
            )
    except JoseError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен"
        )
    user = get_user_by_login(login=login)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    return user
