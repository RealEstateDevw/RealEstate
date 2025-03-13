from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from backend.api.finance.schemas import PaymentStatus
from backend.api.leads.schemas import LeadInDB


class ExpenseCategory(str, Enum):
    HOUSEHOLD = "HOUSEHOLD"  # Бытовые затраты
    SALARY = "SALARY"  # Зарплатные расходы
    OTHER = "OTHER"

class ExpenseBase(BaseModel):
    title: str
    amount: float
    description: Optional[str]
    status: PaymentStatus
    payment_date: datetime
    category: ExpenseCategory

class ExpenseCreate(ExpenseBase):
    """Схема для создания нового расхода"""
    pass

class ExpenseRead(ExpenseBase):
    """Схема для чтения информации о расходе (ответ из API)"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class RopDashboardResponse(BaseModel):
    total_profit: float
    total_expenses: float
    net_profit: float
    closed_deals: List[LeadInDB]
    household_expenses: List[ExpenseRead]
    salary_expenses: List[ExpenseRead]