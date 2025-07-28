from enum import Enum as PyEnum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from backend.api.leads.schemas import LeadStatus


class PaymentStatus(PyEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentType(PyEnum):
    INSTALLMENT = "installment"
    FULL = "full"
    EXPENSE = "expense"


# Pydantic Schemas
class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    payment_type: PaymentType
    due_date: datetime
    description: Optional[str] = None

    class Config:
        orm_mode = True


class PaymentCreate(PaymentBase):
    lead_id: int


class PaymentResponse(PaymentBase):
    id: int
    status: PaymentStatus
    created_at: datetime


class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0)
    payment_date: datetime
    description: Optional[str] = None

    class Config:
        orm_mode = True


class TransactionCreate(TransactionBase):
    lead_id: int
    payment_id: int


class TransactionResponse(TransactionBase):
    id: int
    status: PaymentStatus
    created_at: datetime


class InstallmentPlanCreate(BaseModel):
    lead_id: int
    total_amount: float = Field(..., gt=0)
    number_of_payments: int = Field(..., gt=0)
    start_date: datetime

    @validator('number_of_payments')
    def validate_payments_number(cls, v):
        if v <= 0:
            raise ValueError('Number of payments must be positive')
        if v > 60:  # Maximum 5 years of monthly payments
            raise ValueError('Maximum number of payments exceeded')
        return v


class ExpenseBase(BaseModel):
    title: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    payment_date: datetime


    class Config:
        orm_mode = True


class ExpenseCreate(ExpenseBase):
    status: PaymentStatus
    created_by: int



class ExpenseResponse(ExpenseBase):
    id: int
    status: PaymentStatus
    created_at: datetime


class LeadFinanceResponse(BaseModel):
    id: int
    full_name: str
    total_price: float
    payment_type: str
    status: LeadStatus
    responsible_manager_id: int
    installment_period: Optional[int]
    monthly_payment: Optional[float]

    class Config:
        orm_mode = True


class ManagerStats(BaseModel):
    full_name: str
    total_leads: int
    total_amount: float
    completed_leads: int


class DashboardStats(BaseModel):
    overdue_count: int
    on_time_payments: int
    total_amount_collected: float
    pending_payments: int
