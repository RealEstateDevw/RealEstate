from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CustomHTTPException(HTTPException):
    """Кастомное HTTP исключение с дополнительной информацией"""
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
    """Ошибка базы данных"""
    def __init__(self, detail: str = "Ошибка базы данных", context: Dict[str, Any] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DATABASE_ERROR",
            context=context
        )

class ValidationError(CustomHTTPException):
    """Ошибка валидации"""
    def __init__(self, detail: str, field: str = None, context: Dict[str, Any] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            field=field,
            context=context
        )

class AuthenticationError(CustomHTTPException):
    """Ошибка аутентификации"""
    def __init__(self, detail: str = "Ошибка аутентификации", context: Dict[str, Any] = None):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            context=context
        )

class AuthorizationError(CustomHTTPException):
    """Ошибка авторизации"""
    def __init__(self, detail: str = "Недостаточно прав доступа", context: Dict[str, Any] = None):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="AUTHORIZATION_ERROR",
            context=context
        )

class NotFoundError(CustomHTTPException):
    """Ошибка - ресурс не найден"""
    def __init__(self, detail: str = "Ресурс не найден", context: Dict[str, Any] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="NOT_FOUND",
            context=context
        )

class ConflictError(CustomHTTPException):
    """Ошибка конфликта"""
    def __init__(self, detail: str = "Конфликт данных", context: Dict[str, Any] = None):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT_ERROR",
            context=context
        )

class RateLimitError(CustomHTTPException):
    """Ошибка превышения лимита запросов"""
    def __init__(self, detail: str = "Превышен лимит запросов", context: Dict[str, Any] = None):
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            context=context
        )

class ExternalServiceError(CustomHTTPException):
    """Ошибка внешнего сервиса"""
    def __init__(self, detail: str = "Ошибка внешнего сервиса", context: Dict[str, Any] = None):
        super().__init__(
            status_code=502,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR",
            context=context
        )

def create_error_response(
    status_code: int,
    detail: str,
    error_code: str = None,
    field: str = None,
    context: Dict[str, Any] = None
) -> JSONResponse:
    """Создание стандартизированного ответа об ошибке"""
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

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Обработчик HTTP исключений"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    
    if isinstance(exc, CustomHTTPException):
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
            field=exc.field,
            context=exc.context
        )
    
    return create_error_response(
        status_code=exc.status_code,
        detail=exc.detail
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Обработчик ошибок валидации"""
    logger.warning(f"Validation Error: {exc.errors()} - Path: {request.url.path}")
    
    errors = []
    for error in exc.errors():
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
    """Обработчик общих исключений"""
    logger.error(f"Unhandled Exception: {str(exc)} - Path: {request.url.path}", exc_info=True)
    
    return create_error_response(
        status_code=500,
        detail="Внутренняя ошибка сервера",
        error_code="INTERNAL_SERVER_ERROR"
    )
