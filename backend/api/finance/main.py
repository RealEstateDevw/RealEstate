from datetime import timedelta, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session, joinedload

from backend import get_db
from backend.api.leads.schemas import LeadStatus, LeadState
from backend.database.finance_service.crud import LeadRepository, PaymentRepository, TransactionRepository, \
    FinanceStatisticsRepository, ExpenseRepository, InstallmentPaymentRepository
from backend.database.models import InstallmentPayment, Expense, Lead, Payment
from backend.database.sales_service.crud import LeadDetailService

router = APIRouter(prefix="/api/finance")

from backend.api.finance.schemas import PaymentResponse, PaymentCreate, InstallmentPlanCreate, TransactionCreate, \
    TransactionResponse, ExpenseResponse, ExpenseCreate, DashboardStats, ManagerStats, LeadFinanceResponse, \
    PaymentStatus


def get_repositories(db: Session = Depends(get_db)):
    return {
        "lead": LeadRepository(db),
        "payment": PaymentRepository(db),
        "transaction": TransactionRepository(db),
        "installment": InstallmentPaymentRepository(db),
        "expense": ExpenseRepository(db),
        "stats": FinanceStatisticsRepository(db)
    }


@router.get("/stats", response_model=dict)
async def get_finance_stats(db: Session = Depends(get_db)):
    # Текущий месяц
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    # Просроченные выплаты за текущий месяц
    overdue_payments = (
        db.query(InstallmentPayment)
        .filter(
            InstallmentPayment.due_date < datetime.utcnow(),
            InstallmentPayment.status == "pending"
        )
        .count()
    )

    # Оплаченные рассрочки вовремя за текущий месяц
    timely_payments = (
        db.query(InstallmentPayment)
        .filter(
            InstallmentPayment.due_date >= current_month,
            InstallmentPayment.due_date <= datetime.utcnow(),
            InstallmentPayment.status == "paid"
        )
        .count()
    )

    # Просроченные выплаты за предыдущий месяц
    previous_overdue_payments = (
        db.query(InstallmentPayment)
        .filter(
            InstallmentPayment.due_date >= previous_month,
            InstallmentPayment.due_date < current_month,
            InstallmentPayment.status == "pending"
        )
        .count()
    )

    # Оплаченные рассрочки вовремя за предыдущий месяц
    previous_timely_payments = (
        db.query(InstallmentPayment)
        .filter(
            InstallmentPayment.due_date >= previous_month,
            InstallmentPayment.due_date < current_month,
            InstallmentPayment.status == "paid"
        )
        .count()
    )
    print(overdue_payments, timely_payments, previous_overdue_payments, previous_timely_payments)
    return {
        "overdue_payments": overdue_payments,  # Просроченные выплаты за текущий месяц
        "timely_payments": timely_payments,  # Оплаченные вовремя за текущий месяц
        "previous_overdue_payments": previous_overdue_payments,  # За предыдущий месяц
        "previous_timely_payments": previous_timely_payments  # За предыдущий месяц
    }


# API Endpoints
@router.post("/payments/", response_model=PaymentResponse)
async def create_payment(
        payment: PaymentCreate,
        repos: dict = Depends(get_repositories)
):
    lead = repos["lead"].get_by_id(payment.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return repos["payment"].create_payment(payment.dict())


@router.post("/installments/plan")
async def create_installment_plan_api(
        plan: InstallmentPlanCreate,
        repos: dict = Depends(get_repositories)
):
    lead = repos["lead"].get_by_id(plan.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return repos["installment"].create_installment_plan(
        lead_id=plan.lead_id,
        total_amount=plan.total_amount,
        number_of_payments=plan.number_of_payments,
        start_date=plan.start_date
    )


@router.post("/transactions/", response_model=TransactionResponse)
async def create_transaction(
        transaction: TransactionCreate,
        repos: dict = Depends(get_repositories)
):
    payment = repos["payment"].get_by_id(transaction.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return repos["transaction"].create_transaction(transaction.dict())


@router.get("/leads/{lead_id}/payments", response_model=List[PaymentResponse])
async def get_lead_payments(
        lead_id: int = Path(..., title="The ID of the lead"),
        repos: dict = Depends(get_repositories)
):
    lead = repos["lead"].get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return repos["payment"].get_lead_payments(lead_id)


@router.get("/overdue", response_model=List[PaymentResponse])
async def get_overdue_payments(
        repos: dict = Depends(get_repositories)
):
    return repos["payment"].get_overdue_payments()


@router.post("/expenses/", response_model=ExpenseResponse)
async def create_expense(
        expense: ExpenseCreate,
        repos: dict = Depends(get_repositories)
):
    return repos["expense"].create_expense(expense.dict())


@router.get("/statistics/dashboard", response_model=DashboardStats)
async def get_dashboard_statistics(
        repos: dict = Depends(get_repositories)
):
    return repos["stats"].get_dashboard_statistics()


@router.get("/statistics/managers", response_model=List[ManagerStats])
async def get_manager_statistics(
        repos: dict = Depends(get_repositories)
):
    return repos["stats"].get_manager_statistics()


@router.get("/leads/installments", response_model=List[LeadFinanceResponse])
async def get_installment_leads(
        status: Optional[LeadState] = None,
        manager_id: Optional[int] = None,
        repos: dict = Depends(get_repositories)
):
    return repos["lead"].get_all_installment_leads(status=status, manager_id=manager_id)


@router.put("/payments/{payment_id}/status")
async def update_payment_status(
        payment_id: int,
        status: PaymentStatus,
        repos: dict = Depends(get_repositories)
):
    payment = repos["payment"].update_payment_status(payment_id, status)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/payments/monthly-summary")
async def get_monthly_payment_summary(
        year: int = Query(..., description="Year for summary"),
        month: int = Query(..., description="Month for summary"),
        repos: dict = Depends(get_repositories)
):
    return repos["stats"].get_monthly_summary(year, month)


@router.get("/statuses", response_model=dict)
async def get_lead_payment_statuses(
        db: Session = Depends(get_db),
):
    closed_leads = (
        db.query(Lead)
        .options(joinedload(Lead.user))
        .filter(Lead.state == "CLOSED")
        .all()
    )

    # Лиды на выплате (ожидают оплаты, например, status = "pending" в InstallmentPayment)
    leads_for_payment = (
        db.query(Lead)
        .join(Payment)
        .filter(Payment.status == "PENDING")
        .distinct()
        .all()
    )

    # Выплаченные лиды (status = "paid" в InstallmentPayment)
    paid_leads = (
        db.query(Lead)
        .join(Payment)
        .filter(Payment.status == "PAID")
        .distinct()
        .all()
    )

    # Закупки на выплате (предполагаем модель Purchase с аналогичным статусом)
    purchases_for_payment = (
        db.query(Expense)
        .filter(Expense.status == "PENDING")
        .all()
    )

    # Выплаченные закупки
    paid_purchases = (
        db.query(Expense)
        .filter(Expense.status == "PAID")
        .all()
    )
    return {
        "closed_leads": [lead.to_dict() for lead in closed_leads],
        "leads_for_payment": [lead.to_dict() for lead in leads_for_payment],
        "paid_leads": [lead.to_dict() for lead in paid_leads],
        "purchases_for_payment": [purchase.to_dict() for purchase in purchases_for_payment],
        "paid_purchases": [purchase.to_dict() for purchase in paid_purchases]
    }


@router.get("/leads/{lead_id}")
async def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    try:
        lead_detail_service = LeadDetailService(db)
        lead_details = lead_detail_service.get_lead_details(lead_id)
        if lead_details is None:
            raise HTTPException(status_code=404, detail="Лид не найден")
        return lead_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
