from datetime import date, time
from enum import IntEnum
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr


class WorkDay(BaseModel):
    name: str
    active: bool

    class Config:
        # Добавляем конфигурацию для сериализации
        json_encoders = {
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat()
        }
        # Разрешаем преобразование в словарь
        from_attributes = True


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    login: str
    phone: str
    email: EmailStr
    company: str
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    work_days: List[WorkDay] = None
    role_id: Optional[int] = 1
    hashed_password: str  # открытый пароль, который мы потом захешируем

    class Config:
        # Добавляем конфигурацию для сериализации
        json_encoders = {
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat()
        }
        # Разрешаем преобразование в словарь
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    login: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    work_days: Optional[List[str]] = None
    role_id: Optional[int] = None
    background_theme: Optional[str] = None

    class Config:
        orm_mode = True


class RoleRead(BaseModel):
    id: int
    name: str


class UserRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_date: date
    login: str
    phone: str
    email: EmailStr
    company: str
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    work_days: Optional[List[WorkDay]] = None
    role_id: Optional[int] = None
    role: Union[RoleRead, str] = None
    background_theme: Optional[str] = None
    checkin_time: Optional[bool] = None
    work_status: Optional[str] = None

    class Config:
        from_attributes = True  # чтобы можно было возвращать объекты SQLAlchemy напрямую


# Схема для ответа при логине (JWT-токен)
class Token(BaseModel):
    access_token: str
    token_type: str


class UserRole(IntEnum):
    SALES = 1
    MOP = 2
    ROP = 3
    FINANCE = 4
    ADMIN = 5


ROLE_REDIRECTS = {
    UserRole.SALES: "/dashboard/sales",
    UserRole.MOP: "/dashboard/mop",
    UserRole.ROP: "/dashboard/rop",
    UserRole.FINANCE: "/dashboard/finance",
    UserRole.ADMIN: "/dashboard/admin",
}


class UserSearchResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
