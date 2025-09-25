"""
API Gateway - Единая точка входа для всех микросервисов
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import logging
from typing import Dict, Any
import asyncio
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация микросервисов
SERVICES = {
    "auth": "http://localhost:8001",
    "user": "http://localhost:8002", 
    "complex": "http://localhost:8003",
    "lead": "http://localhost:8004",
    "finance": "http://localhost:8005",
    "marketing": "http://localhost:8006",
    "notification": "http://localhost:8007"
}

# HTTP клиент для запросов к микросервисам
http_client = httpx.AsyncClient(timeout=30.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting API Gateway...")
    yield
    logger.info("Shutting down API Gateway...")
    await http_client.aclose()

app = FastAPI(
    title="RealEstate API Gateway",
    description="Единая точка входа для всех микросервисов",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ServiceRegistry:
    """Реестр микросервисов с проверкой здоровья"""
    
    def __init__(self):
        self.services = SERVICES.copy()
        self.health_status = {}
    
    async def check_health(self, service_name: str) -> bool:
        """Проверка здоровья микросервиса"""
        try:
            service_url = self.services[service_name]
            response = await http_client.get(f"{service_url}/health")
            is_healthy = response.status_code == 200
            self.health_status[service_name] = is_healthy
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            self.health_status[service_name] = False
            return False
    
    async def get_healthy_service(self, service_name: str) -> str:
        """Получение URL здорового микросервиса"""
        if await self.check_health(service_name):
            return self.services[service_name]
        else:
            raise HTTPException(
                status_code=503, 
                detail=f"Service {service_name} is unavailable"
            )

# Глобальный реестр сервисов
service_registry = ServiceRegistry()

async def proxy_request(
    service_name: str, 
    path: str, 
    method: str = "GET",
    data: Dict[str, Any] = None,
    params: Dict[str, Any] = None,
    headers: Dict[str, str] = None
) -> JSONResponse:
    """Проксирование запроса к микросервису"""
    try:
        service_url = await service_registry.get_healthy_service(service_name)
        target_url = f"{service_url}{path}"
        
        # Подготавливаем заголовки
        request_headers = headers or {}
        if "authorization" in request_headers:
            request_headers["Authorization"] = request_headers.pop("authorization")
        
        # Выполняем запрос
        if method.upper() == "GET":
            response = await http_client.get(target_url, params=params, headers=request_headers)
        elif method.upper() == "POST":
            response = await http_client.post(target_url, json=data, params=params, headers=request_headers)
        elif method.upper() == "PUT":
            response = await http_client.put(target_url, json=data, params=params, headers=request_headers)
        elif method.upper() == "DELETE":
            response = await http_client.delete(target_url, params=params, headers=request_headers)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        return JSONResponse(
            content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable")
    except Exception as e:
        logger.error(f"Proxy request failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Проверка здоровья API Gateway"""
    return {"status": "healthy", "service": "api-gateway"}

# Auth Service routes
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(request: Request, path: str):
    """Проксирование запросов к Auth Service"""
    return await proxy_request(
        "auth", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# User Service routes
@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def user_proxy(request: Request, path: str):
    """Проксирование запросов к User Service"""
    return await proxy_request(
        "user", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Complex Service routes
@app.api_route("/complexes/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def complex_proxy(request: Request, path: str):
    """Проксирование запросов к Complex Service"""
    return await proxy_request(
        "complex", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Lead Service routes
@app.api_route("/leads/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def lead_proxy(request: Request, path: str):
    """Проксирование запросов к Lead Service"""
    return await proxy_request(
        "lead", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Finance Service routes
@app.api_route("/finance/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def finance_proxy(request: Request, path: str):
    """Проксирование запросов к Finance Service"""
    return await proxy_request(
        "finance", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Marketing Service routes
@app.api_route("/marketing/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def marketing_proxy(request: Request, path: str):
    """Проксирование запросов к Marketing Service"""
    return await proxy_request(
        "marketing", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Notification Service routes
@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notification_proxy(request: Request, path: str):
    """Проксирование запросов к Notification Service"""
    return await proxy_request(
        "notification", 
        f"/{path}", 
        request.method,
        await request.json() if request.method in ["POST", "PUT"] else None,
        dict(request.query_params),
        dict(request.headers)
    )

# Frontend routes (статические файлы)
@app.get("/")
async def root():
    """Главная страница"""
    return {"message": "RealEstate API Gateway", "version": "1.0.0"}

@app.get("/services/status")
async def services_status():
    """Статус всех микросервисов"""
    status = {}
    for service_name in SERVICES.keys():
        is_healthy = await service_registry.check_health(service_name)
        status[service_name] = {
            "healthy": is_healthy,
            "url": SERVICES[service_name]
        }
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
