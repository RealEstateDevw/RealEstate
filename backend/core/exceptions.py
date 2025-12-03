"""
Exceptions — Централизованная обработка ошибок.

Этот модуль предоставляет:
1. Кастомные исключения для разных типов ошибок
2. Обработчики исключений для FastAPI
3. Стандартизированный формат ответов об ошибках

АРХИТЕКТУРА:
------------
┌──────────────────┐
│  Эндпоинт        │
│  raise NotFound  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│  Exception Handler           │
│  http_exception_handler()    │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Стандартный JSON ответ      │
│  {                           │
│    "error": {                │
│      "code": "NOT_FOUND",    │
│      "message": "...",       │
│      "status_code": 404      │
│    }                         │
│  }                           │
└──────────────────────────────┘

КАСТОМНЫЕ ИСКЛЮЧЕНИЯ:
---------------------
- CustomHTTPException — базовое исключение
- DatabaseError (500) — ошибки БД
- ValidationError (400) — ошибки валидации
- AuthenticationError (401) — ошибки аутентификации
- AuthorizationError (403) — недостаточно прав
- NotFoundError (404) — ресурс не найден
- ConflictError (409) — конфликт данных
- RateLimitError (429) — превышен лимит запросов
- ExternalServiceError (502) — ошибка внешнего API

ОБРАБОТЧИКИ:
------------
- http_exception_handler — для HTTPException
- validation_exception_handler — для RequestValidationError
- general_exception_handler — для всех остальных

ИСПОЛЬЗОВАНИЕ:
--------------
>>> from backend.core.exceptions import NotFoundError
>>> 
>>> @app.get("/users/{id}")
>>> def get_user(id: int):
...     user = db.query(User).get(id)
...     if not user:
...         raise NotFoundError("Пользователь не найден")
...     return user

Автор: RealEstate CRM Team
Дата создания: 2025
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# КАСТОМНЫЕ ИСКЛЮЧЕНИЯ
# =============================================================================

class CustomHTTPException(HTTPException):
    """
    Базовое кастомное HTTP исключение.
    
    Расширяет стандартный FastAPI HTTPException дополнительными полями:
    - error_code: Машиночитаемый код ошибки
    - field: Поле, в котором произошла ошибка
    - context: Дополнительная информация
    
    Args:
        status_code: HTTP статус код (400, 401, 404, и т.д.)
        detail: Человекочитаемое описание ошибки
        error_code: Код ошибки (например, "USER_NOT_FOUND")
        field: Название поля с ошибкой (например, "email")
        context: Дополнительный контекст (словарь)
        
    Пример:
        >>> raise CustomHTTPException(
        ...     status_code=400,
        ...     detail="Email уже используется",
        ...     error_code="EMAIL_CONFLICT",
        ...     field="email",
        ...     context={"existing_user_id": 123}
        ... )
    """
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error_code: str = None,
        field: str = None,
        context: Dict[str, Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.field = field
        self.context = context or {}


class DatabaseError(CustomHTTPException):
    """
    Ошибка базы данных (500 Internal Server Error).
    
    Выбрасывается при:
    - Ошибках подключения к БД
    - SQL ошибках
    - Нарушении ограничений (constraints)
    
    Пример:
        >>> try:
        ...     db.commit()
        ... except SQLAlchemyError as e:
        ...     raise DatabaseError("Не удалось сохранить данные")
    """
    def __init__(self, detail: str = "Ошибка базы данных", context: Dict[str, Any] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DATABASE_ERROR",
            context=context
        )


class ValidationError(CustomHTTPException):
    """
    Ошибка валидации данных (400 Bad Request).
    
    Используется когда данные не проходят бизнес-валидацию
    (помимо Pydantic валидации).
    
    Пример:
        >>> if age < 18:
        ...     raise ValidationError(
        ...         "Возраст должен быть 18+",
        ...         field="age"
        ...     )
    """
    def __init__(self, detail: str, field: str = None, context: Dict[str, Any] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            field=field,
            context=context
        )


class AuthenticationError(CustomHTTPException):
    """
    Ошибка аутентификации (401 Unauthorized).
    
    Выбрасывается при:
    - Неверном пароле
    - Отсутствии токена
    - Невалидном токене
    
    Пример:
        >>> if not verify_password(password, user.hashed_password):
        ...     raise AuthenticationError("Неверный пароль")
    """
    def __init__(self, detail: str = "Ошибка аутентификации", context: Dict[str, Any] = None):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            context=context
        )


class AuthorizationError(CustomHTTPException):
    """
    Ошибка авторизации (403 Forbidden).
    
    Выбрасывается когда пользователь аутентифицирован,
    но не имеет прав на действие.
    
    Пример:
        >>> if user.role.name != "Админ":
        ...     raise AuthorizationError("Требуются права администратора")
    """
    def __init__(self, detail: str = "Недостаточно прав доступа", context: Dict[str, Any] = None):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="AUTHORIZATION_ERROR",
            context=context
        )


class NotFoundError(CustomHTTPException):
    """
    Ошибка — ресурс не найден (404 Not Found).
    
    Выбрасывается когда запрашиваемый ресурс не существует.
    
    Пример:
        >>> user = db.query(User).get(user_id)
        >>> if not user:
        ...     raise NotFoundError(f"Пользователь {user_id} не найден")
    """
    def __init__(self, detail: str = "Ресурс не найден", context: Dict[str, Any] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="NOT_FOUND",
            context=context
        )


class ConflictError(CustomHTTPException):
    """
    Ошибка конфликта данных (409 Conflict).
    
    Выбрасывается при:
    - Попытке создать дубликат (UNIQUE constraint)
    - Конфликте версий данных
    
    Пример:
        >>> if db.query(User).filter_by(email=email).first():
        ...     raise ConflictError("Email уже используется", field="email")
    """
    def __init__(self, detail: str = "Конфликт данных", context: Dict[str, Any] = None):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT_ERROR",
            context=context
        )


class RateLimitError(CustomHTTPException):
    """
    Ошибка превышения лимита запросов (429 Too Many Requests).
    
    Выбрасывается RateLimitMiddleware при превышении лимита.
    
    Пример:
        >>> if request_count > 100:
        ...     raise RateLimitError("Слишком много запросов, попробуйте позже")
    """
    def __init__(self, detail: str = "Превышен лимит запросов", context: Dict[str, Any] = None):
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            context=context
        )


class ExternalServiceError(CustomHTTPException):
    """
    Ошибка внешнего сервиса (502 Bad Gateway).
    
    Выбрасывается при ошибках интеграций:
    - Instagram API недоступен
    - Google Sheets API ошибка
    - Telegram Bot API недоступен
    
    Пример:
        >>> try:
        ...     response = requests.get(instagram_api_url)
        ...     response.raise_for_status()
        ... except requests.RequestException:
        ...     raise ExternalServiceError("Instagram API недоступен")
    """
    def __init__(self, detail: str = "Ошибка внешнего сервиса", context: Dict[str, Any] = None):
        super().__init__(
            status_code=502,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR",
            context=context
        )


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def create_error_response(
    status_code: int,
    detail: str,
    error_code: str = None,
    field: str = None,
    context: Dict[str, Any] = None
) -> JSONResponse:
    """
    Создать стандартизированный JSON ответ об ошибке.
    
    Формат ответа:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Описание ошибки",
            "status_code": 400,
            "field": "email",  // опционально
            "context": {...}   // опционально
        }
    }
    
    Args:
        status_code: HTTP статус код
        detail: Описание ошибки
        error_code: Машиночитаемый код ошибки
        field: Поле с ошибкой (опционально)
        context: Дополнительный контекст (опционально)
        
    Returns:
        JSONResponse: Стандартизированный ответ
    """
    error_data = {
        "error": {
            "code": error_code or "UNKNOWN_ERROR",
            "message": detail,
            "status_code": status_code
        }
    }
    
    if field:
        error_data["error"]["field"] = field
    
    if context:
        error_data["error"]["context"] = context
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )


# =============================================================================
# ОБРАБОТЧИКИ ИСКЛЮЧЕНИЙ
# =============================================================================

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Обработчик HTTP исключений.
    
    Обрабатывает:
    - FastAPI HTTPException
    - Starlette HTTPException
    - Кастомные исключения (CustomHTTPException)
    
    Логирует предупреждение и возвращает стандартизированный JSON.
    
    Регистрация в main.py:
        >>> app.add_exception_handler(HTTPException, http_exception_handler)
    """
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    
    # Если это кастомное исключение — возвращаем расширенную информацию
    if isinstance(exc, CustomHTTPException):
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
            field=exc.field,
            context=exc.context
        )
    
    # Стандартное HTTPException
    return create_error_response(
        status_code=exc.status_code,
        detail=exc.detail
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic.
    
    Обрабатывает ошибки валидации входных данных (request body, query params).
    Преобразует ошибки Pydantic в читаемый формат.
    
    Формат ошибки Pydantic:
        {"loc": ["body", "email"], "msg": "invalid email", "type": "value_error.email"}
    
    Формат ответа:
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации данных",
                "status_code": 422,
                "context": {
                    "errors": [
                        {
                            "field": "body.email",
                            "message": "invalid email",
                            "type": "value_error.email"
                        }
                    ]
                }
            }
        }
    
    Регистрация в main.py:
        >>> app.add_exception_handler(RequestValidationError, validation_exception_handler)
    """
    logger.warning(f"Validation Error: {exc.errors()} - Path: {request.url.path}")
    
    # Преобразуем ошибки Pydantic в читаемый формат
    errors = []
    for error in exc.errors():
        # loc — путь к полю (["body", "email"] → "body.email")
        field = ".".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    return create_error_response(
        status_code=422,
        detail="Ошибка валидации данных",
        error_code="VALIDATION_ERROR",
        context={"errors": errors}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик неожиданных исключений.
    
    Ловит все исключения, которые не были обработаны другими обработчиками.
    Логирует полный traceback и возвращает безопасный ответ клиенту.
    
    ВАЖНО: В production НЕ возвращаем детали ошибки клиенту
    для предотвращения утечки информации о системе.
    
    Регистрация в main.py:
        >>> app.add_exception_handler(Exception, general_exception_handler)
    """
    # Логируем полный traceback для отладки
    logger.error(
        f"Unhandled Exception: {str(exc)} - Path: {request.url.path}",
        exc_info=True  # Включает traceback в лог
    )
    
    return create_error_response(
        status_code=500,
        detail="Внутренняя ошибка сервера",
        error_code="INTERNAL_SERVER_ERROR"
    )
