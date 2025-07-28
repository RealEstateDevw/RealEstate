from datetime import datetime, date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import get_db
from backend.api.finance.schemas import PaymentStatus
from backend.api.leads.schemas import LeadStatus, LeadState
from backend.api.rop.schemas import ExpenseCategory, RopDashboardResponse
from backend.database.models import Expense, Lead, Transaction
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/rop")


@router.get("/dashboard", response_model=RopDashboardResponse)
def get_rop_dashboard(
        db: Session = Depends(get_db),
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None)
):
    """
    Эндпоинт для дашборда Руководителя отдела продаж.
    Параметры:
    - start_date: начало периода (YYYY-MM-DD)
    - end_date: конец периода (YYYY-MM-DD)

    Возвращает:
    - total_profit: Суммарная прибыль (сумма транзакций со статусом PAID)
    - total_expenses: Общие расходы (сумма всех Expense)
    - net_profit: Чистая прибыль = total_profit - total_expenses
    - closed_deals: Список лидов со статусом CLOSED
    - household_expenses: Расходы с категорией HOUSEHOLD
    - salary_expenses: Расходы с категорией SALARY
    """

    # 1. Суммарная прибыль = сумма транзакций (Transaction) со статусом PAID
    query_total_profit = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == PaymentStatus.PAID
    )
    if start_date and end_date:
        # Фильтруем по дате транзакции
        query_total_profit = query_total_profit.filter(
            Transaction.payment_date.between(start_date, end_date)
        )
    total_profit = query_total_profit.scalar() or 0

    # 2. Общие расходы = сумма всех Expense
    query_total_expenses = db.query(func.sum(Expense.amount))
    if start_date and end_date:
        query_total_expenses = query_total_expenses.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    total_expenses = query_total_expenses.scalar() or 0

    # 3. Чистая прибыль
    net_profit = total_profit - total_expenses

    # 4. Закрытые сделки (Lead.status == LeadStatus.CLOSED)
    closed_deals_query = db.query(Lead).filter(Lead.state == LeadState.CLOSED)
    if start_date and end_date:
        # Например, фильтруем по updated_at, если хотим сделки, закрытые в этот период
        closed_deals_query = closed_deals_query.filter(
            Lead.updated_at.between(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time())
            )
        )
    closed_deals = closed_deals_query.all()

    # 5. Бытовые затраты
    household_query = db.query(Expense).filter(Expense.category == ExpenseCategory.HOUSEHOLD)
    if start_date and end_date:
        household_query = household_query.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    household_expenses = household_query.all()

    # 6. Зарплатные расходы
    salary_query = db.query(Expense).filter(Expense.category == ExpenseCategory.SALARY)
    if start_date and end_date:
        salary_query = salary_query.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    salary_expenses = salary_query.all()

    # Формируем ответ (используем схемы Pydantic)
    return RopDashboardResponse(
        total_profit=total_profit,
        total_expenses=total_expenses,
        net_profit=net_profit,
        closed_deals=closed_deals,  # LeadRead будет преобразовывать
        household_expenses=household_expenses,
        salary_expenses=salary_expenses
    )
