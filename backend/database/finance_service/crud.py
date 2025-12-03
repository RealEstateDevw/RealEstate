"""Репозитории и задачи для финансового блока CRM.

Содержит набор классов-репозиториев для работы с платежами, транзакциями,
расходами и статистикой, а также Celery-таск для планового обновления
статусов рассрочек. Все методы рассчитаны на синхронные сессии SQLAlchemy.
"""

import logging

from celery.app import shared_task
from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from backend.api.leads.schemas import LeadState
from backend.database.models import Payment, Transaction, PaymentStatus, InstallmentPayment, Expense, User, Lead


class LeadRepository:
    """Запросы к лидам, использующимся в финансовых сценариях."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, lead_id: int) -> Optional[Lead]:
        return self.db.query(Lead).filter(Lead.id == lead_id).first()

    def get_all_installment_leads(self, status: Optional[str] = None) -> List[Lead]:
        query = self.db.query(Lead).filter(Lead.payment_type == "Рассрочка")
        if status:
            query = query.filter(Lead.state == status)
        return query.all()

    def get_leads_by_manager(self, manager_id: int) -> List[Lead]:
        return self.db.query(Lead) \
            .filter(Lead.responsible_manager_id == manager_id) \
            .all()


class PaymentRepository:
    """CRUD по платежам (Payment) с утилитами поиска просрочек."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: int) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def get_lead_payments(self, lead_id: int) -> List[Payment]:
        return self.db.query(Payment) \
            .filter(Payment.lead_id == lead_id) \
            .order_by(Payment.due_date) \
            .all()

    def create_payment(self, payment_data: dict) -> Payment:
        payment = Payment(**payment_data)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_overdue_payments(self) -> List[Payment]:
        return self.db.query(Payment) \
            .filter(
            Payment.status == PaymentStatus.PENDING,
            Payment.due_date < datetime.now()
        ).all()

    def update_payment_status(self, payment_id: int, status: PaymentStatus) -> Optional[Payment]:
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = status
            self.db.commit()
            self.db.refresh(payment)
        return payment


class TransactionRepository:
    """Создание и получение транзакций по лидy."""

    def __init__(self, db: Session):
        self.db = db

    def create_transaction(self, transaction_data: dict) -> Transaction:
        transaction = Transaction(**transaction_data)
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_lead_transactions(self, lead_id: int) -> List[Transaction]:
        return self.db.query(Transaction) \
            .filter(Transaction.lead_id == lead_id) \
            .order_by(Transaction.payment_date.desc()) \
            .all()


class InstallmentPaymentRepository:
    """Формирование графика рассрочки и получение платежей по лидам."""

    def __init__(self, db: Session):
        self.db = db

    def create_installment_plan(self, lead_id: int, total_amount: float,
                                number_of_payments: int, start_date: datetime) -> List[InstallmentPayment]:
        monthly_amount = total_amount / number_of_payments
        payments = []

        for i in range(number_of_payments):
            payment = InstallmentPayment(
                lead_id=lead_id,
                amount=monthly_amount,
                due_date=start_date + timedelta(days=30 * i),
                payment_number=i + 1,
                total_payments=number_of_payments,
                status=PaymentStatus.PENDING
            )
            payments.append(payment)

        self.db.add_all(payments)
        self.db.commit()
        return payments

    def get_lead_installments(self, lead_id: int) -> List[InstallmentPayment]:
        return self.db.query(InstallmentPayment) \
            .filter(InstallmentPayment.lead_id == lead_id) \
            .order_by(InstallmentPayment.payment_number) \
            .all()


class ExpenseRepository:
    """Работа с расходами (создание/список с фильтром по статусу)."""

    def __init__(self, db: Session):
        self.db = db

    def create_expense(self, expense_data: dict) -> Expense:
        expense = Expense(**expense_data)
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def get_all_expenses(self, status: Optional[PaymentStatus] = None) -> List[Expense]:
        query = self.db.query(Expense)
        if status:
            query = query.filter(Expense.status == status)
        return query.order_by(Expense.payment_date.desc()).all()


class FinanceStatisticsRepository:
    """Сбор агрегированной статистики по менеджерам и просрочкам."""

    def __init__(self, db: Session):
        self.db = db

    def get_manager_statistics(self) -> dict:
        return self.db.query(
            User.full_name,
            func.count(Lead.id).label('total_leads'),
            func.sum(Lead.total_price).label('total_amount'),
            func.count(case([(Lead.state == LeadState.CLOSED, 1)])).label('completed_leads')
        ).join(Lead, User.id == Lead.user_id) \
            .group_by(User.id, User.full_name) \
            .all()

    def get_overdue_statistics(self) -> dict:
        today = datetime.now()
        month_start = today.replace(day=1)

        return {
            "overdue_count": self.db.query(Payment) \
                .filter(
                Payment.status == PaymentStatus.PENDING,
                Payment.due_date < today
            ).count(),
            "on_time_payments": self.db.query(Payment) \
                .filter(
                Payment.status == PaymentStatus.PAID,
                Payment.due_date >= month_start
            ).count()
        }


# from celery import shared_task


def check_and_update_installment_payments(db_session):
    """
    Периодическая задача для обновления статусов платежей по рассрочке

    Args:
        db_session: SQLAlchemy сессия базы данных
    Returns:
        dict: Статистика обновления
    """
    try:
        current_date = datetime.utcnow()
        updated_count = 0

        # Оптимизированный запрос с использованием update() вместо all()
        result = db_session.query(InstallmentPayment).filter(
            and_(
                InstallmentPayment.status == PaymentStatus.PENDING,
                InstallmentPayment.due_date < current_date
            )
        ).update(
            {
                'status': PaymentStatus.OVERDUE,
                'updated_at': current_date  # Предполагаю, что можно добавить это поле
            },
            synchronize_session='fetch'
        )

        updated_count = result

        # Обновляем время изменения связанных лидов
        overdue_lead_ids = db_session.query(InstallmentPayment.lead_id).filter(
            and_(
                InstallmentPayment.status == PaymentStatus.OVERDUE,
                InstallmentPayment.due_date < current_date
            )
        ).distinct().all()

        if overdue_lead_ids:
            lead_ids = [lead_id[0] for lead_id in overdue_lead_ids]
            db_session.query(Lead).filter(
                Lead.id.in_(lead_ids)
            ).update(
                {'updated_at': current_date},
                synchronize_session='fetch'
            )

        db_session.commit()

        logging.info(f"Successfully updated {updated_count} installment payments to OVERDUE")
        return {
            'status': 'success',
            'updated_count': updated_count,
            'timestamp': current_date.isoformat()
        }

    except Exception as e:
        db_session.rollback()
        logging.error(f"Error updating installment payments: {str(e)}")
        raise
    finally:
        db_session.close()


@shared_task(bind=True, max_retries=3)
def daily_installment_status_update(self):
    """
    Celery таск для ежедневного обновления статусов платежей
    """
    try:
        from backend.database import get_db
        db = get_db()  # Убедитесь, что импорт соответствует вашему проекту
        result = check_and_update_installment_payments(db)
        return result
    except Exception as e:
        logging.error(f"Task failed: {str(e)}")
        # Повторяем попытку через 5 минут в случае ошибки
        raise self.retry(countdown=300, exc=e)
