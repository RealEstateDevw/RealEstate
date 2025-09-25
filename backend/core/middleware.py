import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.logging_config import request_logger
from backend.core.rate_limiter import RateLimitMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP запросов"""
    
    async def dispatch(self, request: Request, call_next):
        # Получаем информацию о запросе
        start_time = time.time()
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        
        try:
            # Выполняем запрос
            response = await call_next(request)
            
            # Вычисляем время выполнения
            process_time = time.time() - start_time
            
            # Логируем успешный запрос
            request_logger.log_request(
                method=method,
                path=path,
                status_code=response.status_code,
                response_time=process_time,
                client_ip=client_ip
            )
            
            # Добавляем заголовок с временем выполнения
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Логируем ошибку
            process_time = time.time() - start_time
            request_logger.log_error(
                method=method,
                path=path,
                error=str(e),
                client_ip=client_ip
            )
            
            logger.error(f"Request failed: {method} {path} - {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает IP адрес клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления заголовков безопасности"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Добавляем заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP заголовок (базовый)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        return response

class DatabaseConnectionMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки соединения с базой данных"""
    
    async def dispatch(self, request: Request, call_next):
        # Проверяем соединение с БД только для API запросов
        if request.url.path.startswith("/api/"):
            try:
                from backend.database import engine
                from sqlalchemy import text
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as e:
                logger.error(f"Database connection failed: {str(e)}")
                return Response(
                    content='{"error": "Database connection failed"}',
                    status_code=503,
                    media_type="application/json"
                )
        
        return await call_next(request)
