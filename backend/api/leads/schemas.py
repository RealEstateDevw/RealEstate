from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    COLD = "COLD"  # Внутреннее значение
    WARM = "WARM"
    HOT = "HOT"


class LeadState(str, Enum):
    NEW = "NEW"
    PROCESSED = "PROCESSED"
    IN_WORK = "IN_WORK"
    SENT = "SENT"
    WAITING_RESPONSE = "WAITING_RESPONSE"
    CLOSED = "CLOSED"


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
    installment_markup: Optional[float] = 10
    notes: Optional[str] = None
    next_contact_date: Optional[datetime] = None
    callbacks: List[datetime] = []

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


class CommentBase(BaseModel):
    text: str
    is_internal: bool = False


class CommentCreate(CommentBase):
    lead_id: int


class CommentResponse(CommentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author_name: str

    class Config:
        from_attributes = True


class ContractCreate(BaseModel):
    lead_id: int
    contract_number: str  # Дата подписания
    contractDate: datetime  # Дата договора
    block: str
    floor: int
    apartmentNumber: int
    rooms: int
    size: float
    totalPrice: str
    pricePerM2: str
    paymentChoice: str
    initialPayment: str
    fullName: str
    passportSeries: str
    pinfl: str
    issuedBy: str
    registrationAddress: str
    phone: str
    salesDepartment: str


# Модель ответа (пример; если вы сохраняете договор в БД, используйте ORM-модель)
class ContractResponse(BaseModel):
    id: int
    contract_number: str
    contractDate: datetime
    block: str
    floor: int
    apartmentNumber: int
    rooms: int
    size: float
    totalPrice: str
    pricePerM2: str
    paymentChoice: str
    initialPayment: str
    fullName: str
    passportSeries: str
    pinfl: str
    issuedBy: str
    registrationAddress: str
    phone: str
    salesDepartment: str
    status: str
    lead_id: int

    class Config:
        orm_mode = True


class CallbackRequest(BaseModel):
    callbackTime: datetime
