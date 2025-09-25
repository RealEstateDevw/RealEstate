"""
User Service - Управление пользователями и ролями
"""
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date
import logging
from contextlib import asynccontextmanager
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Модели данных
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    login: str
    email: EmailStr
    phone: str
    role_id: int
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None

class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    login: str
    email: str
    phone: str
    role_id: int
    role_name: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class Role(BaseModel):
    id: int
    name: str
    description: str
    permissions: List[str]

class UserList(BaseModel):
    users: List[User]
    total: int
    page: int
    size: int

# In-memory хранилище (в production - база данных)
ROLES_DB = {
    1: {"id": 1, "name": "admin", "description": "Администратор", "permissions": ["all"]},
    2: {"id": 2, "name": "seller", "description": "Продавец", "permissions": ["leads", "sales"]},
    3: {"id": 3, "name": "finance", "description": "Финансист", "permissions": ["finance", "payments"]},
    4: {"id": 4, "name": "marketing", "description": "Маркетолог", "permissions": ["marketing", "campaigns"]},
    5: {"id": 5, "name": "mop", "description": "MOP", "permissions": ["mop"]},
    6: {"id": 6, "name": "rop", "description": "ROP", "permissions": ["rop"]}
}

USERS_DB = {
    1: {
        "id": 1,
        "first_name": "Admin",
        "last_name": "User",
        "login": "admin",
        "email": "admin@realestate.com",
        "phone": "+998901234567",
        "role_id": 1,
        "is_active": True,
        "created_at": datetime.now(),
        "last_login": None
    },
    2: {
        "id": 2,
        "first_name": "Seller",
        "last_name": "User",
        "login": "seller",
        "email": "seller@realestate.com",
        "phone": "+998901234568",
        "role_id": 2,
        "is_active": True,
        "created_at": datetime.now(),
        "last_login": None
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting User Service...")
    yield
    logger.info("Shutting down User Service...")

app = FastAPI(
    title="User Service",
    description="Сервис управления пользователями и ролями",
    version="1.0.0",
    lifespan=lifespan
)

# API Endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "user-service"}

@app.get("/users", response_model=UserList)
async def get_users(
    page: int = 1,
    size: int = 10,
    role_id: Optional[int] = None,
    search: Optional[str] = None
):
    """Получение списка пользователей с пагинацией и фильтрацией"""
    users = list(USERS_DB.values())
    
    # Фильтрация по роли
    if role_id:
        users = [user for user in users if user["role_id"] == role_id]
    
    # Поиск по имени, фамилии, логину или email
    if search:
        search_lower = search.lower()
        users = [
            user for user in users
            if (search_lower in user["first_name"].lower() or
                search_lower in user["last_name"].lower() or
                search_lower in user["login"].lower() or
                search_lower in user["email"].lower())
        ]
    
    # Пагинация
    total = len(users)
    start = (page - 1) * size
    end = start + size
    paginated_users = users[start:end]
    
    # Добавляем информацию о роли
    result_users = []
    for user in paginated_users:
        role = ROLES_DB.get(user["role_id"], {})
        result_users.append(User(
            id=user["id"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            login=user["login"],
            email=user["email"],
            phone=user["phone"],
            role_id=user["role_id"],
            role_name=role.get("name", "unknown"),
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"]
        ))
    
    return UserList(
        users=result_users,
        total=total,
        page=page,
        size=size
    )

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Получение пользователя по ID"""
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = ROLES_DB.get(user["role_id"], {})
    return User(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        login=user["login"],
        email=user["email"],
        phone=user["phone"],
        role_id=user["role_id"],
        role_name=role.get("name", "unknown"),
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user["last_login"]
    )

@app.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    """Создание нового пользователя"""
    # Проверяем, что логин уникален
    for user in USERS_DB.values():
        if user["login"] == user_data.login:
            raise HTTPException(status_code=400, detail="Login already exists")
    
    # Проверяем, что email уникален
    for user in USERS_DB.values():
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Проверяем, что роль существует
    if user_data.role_id not in ROLES_DB:
        raise HTTPException(status_code=400, detail="Role not found")
    
    # Создаем нового пользователя
    new_user_id = max(USERS_DB.keys()) + 1
    new_user = {
        "id": new_user_id,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "login": user_data.login,
        "email": user_data.email,
        "phone": user_data.phone,
        "role_id": user_data.role_id,
        "is_active": True,
        "created_at": datetime.now(),
        "last_login": None
    }
    
    USERS_DB[new_user_id] = new_user
    
    role = ROLES_DB[user_data.role_id]
    return User(
        id=new_user["id"],
        first_name=new_user["first_name"],
        last_name=new_user["last_name"],
        login=new_user["login"],
        email=new_user["email"],
        phone=new_user["phone"],
        role_id=new_user["role_id"],
        role_name=role["name"],
        is_active=new_user["is_active"],
        created_at=new_user["created_at"],
        last_login=new_user["last_login"]
    )

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate):
    """Обновление пользователя"""
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Обновляем поля
    if user_data.first_name is not None:
        user["first_name"] = user_data.first_name
    if user_data.last_name is not None:
        user["last_name"] = user_data.last_name
    if user_data.email is not None:
        # Проверяем уникальность email
        for other_user in USERS_DB.values():
            if other_user["id"] != user_id and other_user["email"] == user_data.email:
                raise HTTPException(status_code=400, detail="Email already exists")
        user["email"] = user_data.email
    if user_data.phone is not None:
        user["phone"] = user_data.phone
    if user_data.role_id is not None:
        if user_data.role_id not in ROLES_DB:
            raise HTTPException(status_code=400, detail="Role not found")
        user["role_id"] = user_data.role_id
    
    role = ROLES_DB[user["role_id"]]
    return User(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        login=user["login"],
        email=user["email"],
        phone=user["phone"],
        role_id=user["role_id"],
        role_name=role["name"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user["last_login"]
    )

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Удаление пользователя"""
    if user_id not in USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    
    del USERS_DB[user_id]
    return {"message": "User deleted successfully"}

@app.put("/users/{user_id}/activate")
async def activate_user(user_id: int):
    """Активация пользователя"""
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user["is_active"] = True
    return {"message": "User activated successfully"}

@app.put("/users/{user_id}/deactivate")
async def deactivate_user(user_id: int):
    """Деактивация пользователя"""
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user["is_active"] = False
    return {"message": "User deactivated successfully"}

@app.get("/roles", response_model=List[Role])
async def get_roles():
    """Получение списка ролей"""
    return [Role(**role) for role in ROLES_DB.values()]

@app.get("/roles/{role_id}", response_model=Role)
async def get_role(role_id: int):
    """Получение роли по ID"""
    role = ROLES_DB.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return Role(**role)

@app.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: int):
    """Получение разрешений пользователя"""
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = ROLES_DB.get(user["role_id"], {})
    return {"permissions": role.get("permissions", [])}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
