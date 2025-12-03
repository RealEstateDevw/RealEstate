"""
ROP API — REST API для руководителя отдела продаж.

НАЗНАЧЕНИЕ:
-----------
Этот модуль предоставляет функционал для РОП (Руководитель отдела продаж):
- Просмотр финансового дашборда
- Управление расходами компании
- Анализ прибыльности
- Контроль закрытых сделок

РОЛЬ РОП:
---------
Руководитель отдела продаж отвечает за:
- Общую стратегию продаж
- Финансовые показатели отдела
- Управление бюджетом (доходы и расходы)
- Принятие решений о найме и увольнении
- Установку KPI для МОП и продажников

АРХИТЕКТУРА:
------------
Router → Models → Database → Aggregations

ИСПОЛЬЗОВАНИЕ:
--------------
Все эндпоинты доступны по префиксу /api/rop/

Примеры:
    GET /api/rop/dashboard — финансовый дашборд
    GET /api/rop/dashboard?start_date=2025-12-01&end_date=2025-12-31 — за период

Автор: RealEstate CRM Team
Дата создания: 2025
"""

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

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(prefix="/api/rop")


# =============================================================================
# ДАШБОРД И АНАЛИТИКА
# =============================================================================

@router.get("/dashboard", response_model=RopDashboardResponse)
def get_rop_dashboard(
        db: Session = Depends(get_db),
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None)
):
    """
    Финансовый дашборд для руководителя отдела продаж.
    
    Показывает полную финансовую картину отдела за выбранный период:
    - Доходы (оплаченные транзакции)
    - Расходы (все категории)
    - Чистая прибыль
    - Закрытые сделки
    - Детализация расходов
    
    Args:
        db: Сессия БД (автоматически через Depends)
        
        start_date: Начало периода (формат: YYYY-MM-DD)
            Если не указан — берутся данные с начала времён
            Пример: 2025-12-01
            
        end_date: Конец периода (формат: YYYY-MM-DD)
            Если не указан — берутся данные до текущего момента
            Пример: 2025-12-31
            
    Returns:
        RopDashboardResponse: Финансовый дашборд со следующими полями:
        
            total_profit: float
                Суммарная прибыль (сумма всех оплаченных транзакций)
                Включает все типы платежей: аванс, ипотека, рассрочка
                
            total_expenses: float
                Общие расходы компании (все категории)
                Включает: зарплаты, бытовые расходы, маркетинг, и т.д.
                
            net_profit: float
                Чистая прибыль = total_profit - total_expenses
                Основной показатель эффективности отдела
                
            closed_deals: List[Lead]
                Список закрытых сделок за период
                Каждая сделка содержит:
                - ID лида
                - Имя клиента
                - Продажник
                - Дата закрытия
                - Сумма сделки
                
            household_expenses: List[Expense]
                Бытовые расходы (категория HOUSEHOLD)
                Примеры: аренда офиса, коммунальные услуги, канцтовары
                
            salary_expenses: List[Expense]
                Зарплатные расходы (категория SALARY)
                Включает зарплаты всех сотрудников
                
    Примеры запросов:
        >>> GET /api/rop/dashboard
        >>> # Все данные без фильтра по датам
        
        >>> GET /api/rop/dashboard?start_date=2025-12-01&end_date=2025-12-31
        >>> # Данные за декабрь 2025
        
        >>> GET /api/rop/dashboard?start_date=2025-01-01
        >>> # Данные с начала 2025 года по сегодня
        
    Пример ответа:
        >>> {
        ...   "total_profit": 5000000,
        ...   "total_expenses": 1200000,
        ...   "net_profit": 3800000,
        ...   "closed_deals": [
        ...     {
        ...       "id": 123,
        ...       "client_name": "Иван Петров",
        ...       "assigned_to": {"id": 5, "name": "Продажник Иванов"},
        ...       "closing_date": "2025-12-15",
        ...       "total_amount": 500000
        ...     },
        ...     ...
        ...   ],
        ...   "household_expenses": [
        ...     {
        ...       "id": 45,
        ...       "category": "HOUSEHOLD",
        ...       "amount": 50000,
        ...       "description": "Аренда офиса",
        ...       "payment_date": "2025-12-01"
        ...     },
        ...     ...
        ...   ],
        ...   "salary_expenses": [
        ...     {
        ...       "id": 78,
        ...       "category": "SALARY",
        ...       "amount": 30000,
        ...       "description": "Зарплата Иванова",
        ...       "payment_date": "2025-12-05"
        ...     },
        ...     ...
        ...   ]
        ... }
        
    Использование РОП:
        Этот дашборд помогает РОП:
        1. Оценить финансовое состояние отдела
        2. Принять решение о найме новых сотрудников
        3. Оптимизировать расходы
        4. Установить KPI для МОП и продажников
        5. Спланировать бюджет на следующий период
        
    Расчёты:
        1. total_profit:
           SELECT SUM(amount) FROM transactions 
           WHERE status = 'PAID' 
           AND payment_date BETWEEN start_date AND end_date
           
        2. total_expenses:
           SELECT SUM(amount) FROM expenses 
           WHERE payment_date BETWEEN start_date AND end_date
           
        3. net_profit:
           total_profit - total_expenses
           
        4. closed_deals:
           SELECT * FROM leads 
           WHERE state = 'CLOSED' 
           AND updated_at BETWEEN start_date AND end_date
           
    Performance Note:
        Запрос использует агрегатные функции (SUM) и может быть медленным
        на больших объёмах данных. Рекомендуется:
        - Создать индексы на payment_date и status
        - Использовать материализованные представления для часто используемых периодов
        - Кэшировать результаты
    """
    
    # -------------------------------------------------------------------------
    # 1. РАСЧЁТ СУММАРНОЙ ПРИБЫЛИ
    # -------------------------------------------------------------------------
    # Суммируем все оплаченные транзакции (Transaction.status == PAID)
    query_total_profit = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == PaymentStatus.PAID
    )
    
    # Применяем фильтр по датам, если указаны
    if start_date and end_date:
        query_total_profit = query_total_profit.filter(
            Transaction.payment_date.between(start_date, end_date)
        )
    
    # Выполняем запрос (scalar возвращает одно значение)
    total_profit = query_total_profit.scalar() or 0

    # -------------------------------------------------------------------------
    # 2. РАСЧЁТ ОБЩИХ РАСХОДОВ
    # -------------------------------------------------------------------------
    # Суммируем все расходы (Expense) независимо от категории
    query_total_expenses = db.query(func.sum(Expense.amount))
    
    # Применяем фильтр по датам
    if start_date and end_date:
        query_total_expenses = query_total_expenses.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    
    total_expenses = query_total_expenses.scalar() or 0

    # -------------------------------------------------------------------------
    # 3. РАСЧЁТ ЧИСТОЙ ПРИБЫЛИ
    # -------------------------------------------------------------------------
    # Простая формула: доходы минус расходы
    net_profit = total_profit - total_expenses

    # -------------------------------------------------------------------------
    # 4. ЗАКРЫТЫЕ СДЕЛКИ
    # -------------------------------------------------------------------------
    # Получаем все лиды со статусом CLOSED за период
    closed_deals_query = db.query(Lead).filter(Lead.state == LeadState.CLOSED)
    
    # Фильтруем по дате обновления (когда лид был закрыт)
    if start_date and end_date:
        closed_deals_query = closed_deals_query.filter(
            Lead.updated_at.between(
                datetime.combine(start_date, datetime.min.time()),  # начало дня
                datetime.combine(end_date, datetime.max.time())     # конец дня
            )
        )
    
    closed_deals = closed_deals_query.all()

    # -------------------------------------------------------------------------
    # 5. БЫТОВЫЕ РАСХОДЫ
    # -------------------------------------------------------------------------
    # Расходы категории HOUSEHOLD (аренда, коммунальные, и т.д.)
    household_query = db.query(Expense).filter(Expense.category == ExpenseCategory.HOUSEHOLD)
    
    if start_date and end_date:
        household_query = household_query.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    
    household_expenses = household_query.all()

    # -------------------------------------------------------------------------
    # 6. ЗАРПЛАТНЫЕ РАСХОДЫ
    # -------------------------------------------------------------------------
    # Расходы категории SALARY (зарплаты сотрудников)
    salary_query = db.query(Expense).filter(Expense.category == ExpenseCategory.SALARY)
    
    if start_date and end_date:
        salary_query = salary_query.filter(
            Expense.payment_date.between(start_date, end_date)
        )
    
    salary_expenses = salary_query.all()

    # -------------------------------------------------------------------------
    # 7. ФОРМИРОВАНИЕ ОТВЕТА
    # -------------------------------------------------------------------------
    # Pydantic схема автоматически преобразует модели в JSON
    return RopDashboardResponse(
        total_profit=total_profit,
        total_expenses=total_expenses,
        net_profit=net_profit,
        closed_deals=closed_deals,        # будет преобразовано в LeadRead[]
        household_expenses=household_expenses,
        salary_expenses=salary_expenses
    )
