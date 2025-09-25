from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from typing import Dict, Tuple
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Простой rate limiter на основе sliding window"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Проверяет, разрешен ли запрос для данного IP"""
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Удаляем старые запросы (старше окна)
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Проверяем лимит
        if len(client_requests) >= self.max_requests:
            return False
        
        # Добавляем текущий запрос
        client_requests.append(now)
        return True
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Возвращает количество оставшихся запросов"""
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Удаляем старые запросы
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        return max(0, self.max_requests - len(client_requests))
    
    def get_reset_time(self, client_ip: str) -> float:
        """Возвращает время сброса лимита"""
        client_requests = self.requests[client_ip]
        if not client_requests:
            return time.time()
        
        return client_requests[0] + self.window_seconds

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def dispatch(self, request: Request, call_next):
        # Получаем IP клиента
        client_ip = self._get_client_ip(request)
        
        # Проверяем лимит
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            remaining = self.rate_limiter.get_remaining_requests(client_ip)
            reset_time = self.rate_limiter.get_reset_time(client_ip)
            
            response = HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Превышен лимит запросов",
                        "retry_after": int(reset_time - time.time()),
                        "remaining_requests": remaining
                    }
                }
            )
            return response
        
        # Добавляем заголовки с информацией о лимитах
        response = await call_next(request)
        
        remaining = self.rate_limiter.get_remaining_requests(client_ip)
        reset_time = self.rate_limiter.get_reset_time(client_ip)
        
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает IP адрес клиента с учетом прокси"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Возвращаем IP из соединения
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"

# Создаем глобальный экземпляр rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
