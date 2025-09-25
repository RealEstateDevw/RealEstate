"""
Auth Service - Аутентификация и авторизация
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
import logging
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Модели данных
class UserLogin(BaseModel):
    login: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

class UserInfo(BaseModel):
    id: int
    login: str
    role: str
    first_name: str
    last_name: str

# In-memory хранилище пользователей (в production - база данных)
USERS_DB = {
    1: {
        "id": 1,
        "login": "admin",
        "hashed_password": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": "admin",
        "first_name": "Admin",
        "last_name": "User"
    },
    2: {
        "id": 2,
        "login": "seller",
        "hashed_password": bcrypt.hashpw("seller123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": "seller",
        "first_name": "Seller",
        "last_name": "User"
    }
}

# JWT токены (в production - Redis)
ACTIVE_TOKENS = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Auth Service...")
    yield
    logger.info("Shutting down Auth Service...")

app = FastAPI(
    title="Auth Service",
    description="Сервис аутентификации и авторизации",
    version="1.0.0",
    lifespan=lifespan
)

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем, что токен активен
        if credentials.credentials not in ACTIVE_TOKENS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(user_id=user_id, role=role)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_by_login(login: str) -> Optional[dict]:
    """Поиск пользователя по логину"""
    for user in USERS_DB.values():
        if user["login"] == login:
            return user
    return None

# API Endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "auth-service"}

@app.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Аутентификация пользователя"""
    user = get_user_by_login(user_credentials.login)
    
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "role": user["role"]}, 
        expires_delta=access_token_expires
    )
    
    # Сохраняем токен как активный
    ACTIVE_TOKENS[access_token] = {
        "user_id": user["id"],
        "role": user["role"],
        "created_at": datetime.utcnow()
    }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/logout")
async def logout(token_data: TokenData = Depends(verify_token)):
    """Выход пользователя (отзыв токена)"""
    # В реальном приложении нужно найти токен по user_id
    # Здесь упрощенная версия
    return {"message": "Successfully logged out"}

@app.get("/me", response_model=UserInfo)
async def get_current_user(token_data: TokenData = Depends(verify_token)):
    """Получение информации о текущем пользователе"""
    user = USERS_DB.get(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(
        id=user["id"],
        login=user["login"],
        role=user["role"],
        first_name=user["first_name"],
        last_name=user["last_name"]
    )

@app.post("/verify")
async def verify_token_endpoint(token_data: TokenData = Depends(verify_token)):
    """Проверка токена"""
    return {
        "valid": True,
        "user_id": token_data.user_id,
        "role": token_data.role
    }

@app.get("/users/{user_id}")
async def get_user(user_id: int, token_data: TokenData = Depends(verify_token)):
    """Получение информации о пользователе по ID"""
    # Проверяем права доступа
    if token_data.role != "admin" and token_data.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(
        id=user["id"],
        login=user["login"],
        role=user["role"],
        first_name=user["first_name"],
        last_name=user["last_name"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
