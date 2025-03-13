from typing import Optional, List

from pydantic import BaseModel

from backend.database.models import Lead, User, Expense


class SearchResultBase(BaseModel):
    id: int
    type: str  # 'lead', 'user' или 'expense'
    name: str
    phone: Optional[str] = None  # Теперь это поле необязательное
    email: Optional[str] = None
    region: Optional[str] = None
    amount: Optional[float] = None  # Для выплат
    status: Optional[str] = None  # Для выплат
    payment_date: Optional[str] = None  # Для выплат
    created_at: Optional[str] = None  # Для выплат

    class Config:
        orm_mode = True

class SearchResponse(BaseModel):
    results: List[SearchResultBase]
    total_count: int


def convert_lead_to_search_result(lead: Lead) -> SearchResultBase:
    return SearchResultBase(
        id=lead.id,
        type='lead',
        name=lead.full_name,
        phone=lead.phone,
        region=lead.region,
    )

def convert_user_to_search_result(user: User) -> SearchResultBase:
    return SearchResultBase(
        id=user.id,
        type='user',
        name=f"{user.first_name} {user.last_name}".strip(),
        phone=user.phone,
        email=user.email
    )


def convert_expense_to_search_result(expense: Expense) -> SearchResultBase:
    return SearchResultBase(
        id=expense.id,
        type='expense',
        name=expense.title,
        amount=expense.amount,
        status=expense.status.value,  # Преобразуем Enum в строку
        payment_date=expense.payment_date.strftime("%Y-%m-%d %H:%M"),
        created_at=expense.created_at.strftime("%Y-%m-%d %H:%M")
    )
