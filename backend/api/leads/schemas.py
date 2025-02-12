from pydantic import BaseModel, validator, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    COLD = "COLD"  # Внутреннее значение
    WARM = "WARM"
    HOT = "HOT"


class LeadState(str, Enum):
    POSTPONED = "POSTPONED"
    IN_PROCESSING = "IN_PROCESSING"
    IN_WORK = "IN_WORK"
    SENT = "SENT"
    WAITING_RESPONSE = "WAITING_RESPONSE"
    DECLINED = "DECLINED"


class LeadBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(...)
    region: str
    contact_source: str
    status: LeadStatus
    state: LeadState
    square_meters: Optional[int] = None
    rooms: Optional[int] = None
    floor: Optional[int] = None
    total_price: float = Field(..., gt=0)
    currency: str = "UZS"
    payment_type: str
    monthly_payment: Optional[float] = None
    installment_period: Optional[int] = None
    installment_markup: Optional[float] = None
    notes: Optional[str] = None
    next_contact_date: Optional[datetime] = None

    class Config:
        use_enum_values = True  # Это важно для корректной сериализации



class LeadCreate(LeadBase):
    user_id: int


class LeadUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None)
    region: Optional[str] = None
    contact_source: Optional[str] = None
    status: Optional[LeadStatus] = None
    state: Optional[LeadState] = None
    square_meters: Optional[int] = None
    rooms: Optional[int] = None
    floor: Optional[int] = None
    total_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    payment_type: Optional[str] = None
    monthly_payment: Optional[float] = None
    installment_period: Optional[int] = None
    installment_markup: Optional[float] = None
    notes: Optional[str] = None
    next_contact_date: Optional[datetime] = None


class LeadInDB(LeadBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class LeadSearchResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    region: str
    status: LeadStatus
    state: LeadState
    total_price: float
    payment_type: str
    contact_source: str

    class Config:
        orm_mode = True
        use_enum_values = True
