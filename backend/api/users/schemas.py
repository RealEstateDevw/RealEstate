# backend/api/users/schemas.py
from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, EmailStr


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
    work_days: List[str]
    hashed_password: str  # открытый пароль, который мы потом захешируем


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
    work_days: List[str]
    role_id: Optional[int] = None

    class Config:
        from_attributes = True  # чтобы можно было возвращать объекты SQLAlchemy напрямую


# Схема для ответа при логине (JWT-токен)
class Token(BaseModel):
    access_token: str
    token_type: str
