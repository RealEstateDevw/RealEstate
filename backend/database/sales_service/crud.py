import random
from datetime import timedelta, datetime

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import joinedload, noload
from sqlalchemy import desc, or_, func, and_, String, cast
from sqlalchemy.orm import Session
from datetime import datetime

from typing import Optional, List, Dict, Any, Union
from fastapi.encoders import jsonable_encoder

from backend.api.finance.schemas import PaymentType, PaymentStatus
from backend.api.leads.schemas import LeadCreate, LeadStatus, LeadState, LeadUpdate
from backend.api.mop.schemas import convert_user_to_search_result, convert_lead_to_search_result, SearchResponse, \
    convert_expense_to_search_result
from backend.database.models import Lead, User, InstallmentPayment, Payment, Expense, Role


class LeadCRUD:
    def get_random_salesperson_id(self, db: Session) -> int:
        """Находит ID случайного активного продажника."""
        # ... (код функции остается без изменений, как в предыдущем ответе) ...
        try:
            salespeople = db.query(User).join(Role).filter(Role.name == "Продажник").all()
            if not salespeople:
                raise NoResultFound("Не найдено пользователей с ролью продажника для назначения лида.")
            assigned_user = random.choice(salespeople)
            print(f"Лид будет назначен случайному продажнику: ID={assigned_user.id}")
            return assigned_user.id
        except NoResultFound as e:
            raise e
        except Exception as e:
            print(f"Ошибка при поиске случайного продажника: {e}")
            raise Exception("Ошибка базы данных при поиске пользователя.") from e

    def create_lead(self, db: Session, lead: LeadCreate) -> Lead:
        """
        Создает лид. Если user_id предоставлен, использует его.
        Если user_id не предоставлен, назначает случайного продажника.
        """
        final_user_id: int

        # --- Условная логика назначения user_id ---
        if lead.user_id is not None:
            # ID пользователя предоставлен - используем его
            print(f"Лид создается с предоставленным user_id: {lead.user_id}")
            # --- ДОПОЛНИТЕЛЬНАЯ ВАЛИДАЦИЯ (РЕКОМЕНДУЕТСЯ) ---
            # Проверим, существует ли такой пользователь и имеет ли он нужную роль
            user = db.query(User).filter(User.id == lead.user_id).first()
            if not user:
                raise ValueError(f"Пользователь с предоставленным ID={lead.user_id} не найден.")
            # Можно добавить проверку роли, если это важно
            # if user.role.name != SALESPERSON_ROLE_NAME:
            #    raise ValueError(f"Пользователь ID={lead.user_id} не имеет роли '{SALESPERSON_ROLE_NAME}'.")
            # --- КОНЕЦ ВАЛИДАЦИИ ---
            final_user_id = lead.user_id
        else:
            # ID пользователя НЕ предоставлен - назначаем случайного
            print("user_id не предоставлен, назначаем случайного продажника...")
            try:
                final_user_id = self.get_random_salesperson_id(db)
            except NoResultFound as e:
                # Если случайный продажник не найден
                print(f"Ошибка при назначении случайного продажника: {e}")
                raise e  # Пробрасываем ошибку для обработки в эндпоинте

        # --- Создание объекта БД ---
        try:
            # Создаем ORM объект Lead, явно указывая user_id
            # Используем lead.dict(exclude={'user_id'}) чтобы случайно не передать None, если он был
            lead_data_dict = lead.dict(exclude={'user_id'})
            db_lead = Lead(
                **lead_data_dict,
                user_id=final_user_id  # Используем определенный ID
            )
            db.add(db_lead)
            db.commit()
            db.refresh(db_lead)
            print(f"Лид ID={db_lead.id} успешно создан и назначен пользователю ID={final_user_id}")
            return db_lead
        except IntegrityError as e:
            db.rollback()
            print(f"Ошибка целостности БД при создании лида: {e}")
            # Можно проверить, не дубликат ли это (например, по телефону)
            raise ValueError(f"Не удалось создать лид. Возможно, дубликат или неверные данные. {e}") from e
        except Exception as e:
            db.rollback()
            print(f"Ошибка при сохранении лида в БД: {e}")
            raise Exception("Не удалось сохранить лид в базе данных.") from e

    def get_lead(self, db: Session, lead_id: int) -> Optional[Lead]:
        return db.query(Lead).filter(Lead.id == lead_id).first()

    def get_leads(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            status: Optional[LeadStatus] = None,
            state: Optional[LeadState] = None,
            region: Optional[str] = None,
            payment_type: Optional[str] = None
    ) -> List[Lead]:
        # Exclude leads without an assigned salesperson
        query = db.query(Lead).filter(Lead.user_id.isnot(None), Lead.state != 'INACTIVE')
        query = query.options(noload(Lead.callbacks))
        if status:
            query = query.filter(Lead.status == status)
        if state:
            query = query.filter(Lead.state == state)
        if region:
            query = query.filter(Lead.region == region)
        if payment_type:
            query = query.filter(Lead.payment_type == payment_type)

        return query.order_by(desc(Lead.created_at)).offset(skip).limit(limit).all()

    def update_lead(self, db: Session, lead_id: int, lead_update: LeadUpdate) -> Optional[Lead]:
        db_lead = self.get_lead(db, lead_id)
        if not db_lead:
            return None

        update_data = lead_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_lead, field, value)

        db.commit()
        db.refresh(db_lead)
        return db_lead

    def delete_lead(self, db: Session, lead_id: int) -> bool:
        db_lead = self.get_lead(db, lead_id)
        if not db_lead:
            return False

        db.delete(db_lead)
        db.commit()
        return True

    def unassign_lead(self, db: Session, lead_id: int) -> bool:
        """
        Убирает привязку лида к продавцу, устанавливая user_id в None.
        Возвращает True, если операция успешна, иначе False.
        """
        db_lead = self.get_lead(db, lead_id)
        if not db_lead:
            return False

        db_lead.user_id = None
        db.commit()
        return True

    def get_leads_by_user(self, db: Session, user_id: int, include_callbacks: bool = False, skip: int = 0,
                          limit: int = 100) -> List[Lead]:
        query = db.query(Lead).filter(Lead.user_id == user_id,
                                      Lead.state != 'INACTIVE').order_by(desc(Lead.created_at))

        if include_callbacks:
            query = query.options(joinedload(Lead.callbacks))

        return query.offset(skip).limit(limit).all()

    def search_leads(
            self,
            db: Session,
            query: str,
            limit: int = 10
    ) -> List[Lead]:
        """
        Search leads by multiple fields:
        - full_name
        - phone
        - region
        """
        search_query = f"%{query}%"
        return db.query(Lead).filter(
            or_(
                Lead.full_name.ilike(search_query),
                Lead.phone.ilike(search_query),
                Lead.region.ilike(search_query)
            )
        ).limit(limit).all()

    def combined_search(self, db: Session, query: str, limit: int = 10) -> SearchResponse:
        """
        Search both leads and users by the provided query.
        Returns unified search results.
        """
        search_query = f"%{query}%"

        # Query Leads
        leads = db.query(Lead).filter(
            or_(
                Lead.full_name.ilike(search_query),
                Lead.phone.ilike(search_query),
                Lead.region.ilike(search_query)
            )
        ).limit(limit).all()

        # Query Users
        users = db.query(User).filter(User.role_id == 1,
                                      or_(
                                          User.first_name.ilike(search_query),
                                          User.last_name.ilike(search_query),
                                          User.phone.ilike(search_query),
                                          User.email.ilike(search_query)
                                      )
                                      ).limit(limit).all()
        # Convert to unified format
        lead_results = [convert_lead_to_search_result(lead) for lead in leads]
        user_results = [convert_user_to_search_result(user) for user in users]

        # Combine and limit results
        all_results = (lead_results + user_results)[:limit]
        total_count = len(leads) + len(users)

        return SearchResponse(
            results=all_results,
            total_count=total_count
        )

    def combined_search_finance(self, db: Session, query: str, limit: int = 10) -> SearchResponse:
        """
        Search leads, users, and expenses by the provided query.
        Returns unified search results.
        """
        search_query = f"%{query}%"

        # Query Leads
        leads = db.query(Lead).filter(
            or_(
                Lead.full_name.ilike(search_query),
                Lead.phone.ilike(search_query),
                Lead.region.ilike(search_query)
            )
        ).limit(limit).all()

        # Query Users
        users = db.query(User).filter(User.role_id == 1,
                                      or_(
                                          User.first_name.ilike(search_query),
                                          User.last_name.ilike(search_query),
                                          User.phone.ilike(search_query),
                                          User.email.ilike(search_query)
                                      )
                                      ).limit(limit).all()

        # Query Expenses
        expenses = db.query(Expense).filter(
            or_(
                Expense.title.ilike(search_query),
                cast(Expense.amount, String).ilike(search_query),  # Приводим числовое поле к строке
                Expense.description.ilike(search_query),
                Expense.status.cast(String).ilike(search_query)  # Приводим Enum к строке
            )
        ).limit(limit).all()

        # Convert to unified format
        lead_results = [convert_lead_to_search_result(lead) for lead in leads]
        user_results = [convert_user_to_search_result(user) for user in users]
        expense_results = [convert_expense_to_search_result(expense) for expense in expenses]

        # Combine and limit results
        all_results = (lead_results + user_results + expense_results)[:limit]
        total_count = len(leads) + len(users) + len(expenses)

        return SearchResponse(
            results=all_results,
            total_count=total_count
        )


class LeadStatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_statistics(self) -> Dict:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        # Get today's new leads count
        today_new_leads = self.db.query(Lead).filter(
            func.date(Lead.created_at) == today
        ).count()

        # Get yesterday's new leads count
        yesterday_new_leads = self.db.query(Lead).filter(
            func.date(Lead.created_at) == yesterday
        ).count()

        # Get today's processed leads count
        today_processed = self.db.query(Lead).filter(
            func.date(Lead.updated_at) == today,
            Lead.state.in_(['PROCESSED', 'COMPLETED'])  # Adjust based on your LeadState enum
        ).count()

        # Get yesterday's processed leads count
        yesterday_processed = self.db.query(Lead).filter(
            func.date(Lead.updated_at) == yesterday,
            Lead.state.in_(['PROCESSED', 'COMPLETED'])
        ).count()

        return {
            "new_leads": {
                "today": today_new_leads,
                "yesterday": yesterday_new_leads,
                "trend": "up" if today_new_leads > yesterday_new_leads else "down"
            },
            "processed_leads": {
                "today": today_processed,
                "yesterday": yesterday_processed,
                "trend": "up" if today_processed > yesterday_processed else "down"
            }
        }


class InactiveLeadsService:
    def __init__(self, db: Session):
        self.db = db

    def get_inactive_leads(self) -> dict:
        # Define criteria for inactive leads (e.g., no updates for 30 days)
        threshold_date = datetime.utcnow() - timedelta(days=30)

        inactive_leads = self.db.query(Lead).filter(
            or_(
                Lead.updated_at < threshold_date,
                Lead.state == 'INACTIVE'
            ),
            Lead.state != 'CLOSED'
        ).all()

        return {
            "total_count": len(inactive_leads),
            "leads": [self._format_lead(lead) for lead in inactive_leads]
        }

    def _format_lead(self, lead: Lead) -> dict:
        return {
            "id": lead.id,
            "full_name": lead.full_name,
            "date": lead.created_at.strftime("%d.%m.%Y"),
            "contact_source": lead.contact_source,
            "region": lead.region,
            "phone": lead.phone,
            "payment_type": lead.payment_type,
            "total_price": lead.total_price,
            "user": f"{lead.user.first_name} {lead.user.last_name}" if lead.user else "Не назначен",
            "state": lead.state.value if hasattr(lead.state, 'value') else str(lead.state)
        }


class UnassignedLeadsService:
    def __init__(self, db: Session):
        self.db = db

    def get_unassigned_leads(self) -> dict:
        """
        Returns leads that are active but not assigned to any salesperson.
        """
        unassigned_leads = self.db.query(Lead).filter(
            Lead.user_id.is_(None),
            Lead.is_active == True
        ).all()

        return {
            "total_count": len(unassigned_leads),
            "leads": [self._format_lead(lead) for lead in unassigned_leads]
        }

    def _format_lead(self, lead: 'Lead') -> dict:
        return {
            "id": lead.id,
            "full_name": lead.full_name,
            "date": lead.created_at.strftime("%d.%m.%Y"),
            "contact_source": lead.contact_source,
            "region": lead.region,
            "phone": lead.phone,
            "payment_type": lead.payment_type,
            "total_price": lead.total_price,
            "user": "Не назначен",
            "state": lead.state.value if hasattr(lead.state, 'value') else str(lead.state)
        }


class LeadFilterService:
    def __init__(self, db: Session):
        self.db = db

    def get_filtered_leads(self, user_id: Optional[int] = None) -> dict:
        """Get leads filtered by user_id if provided, otherwise get all leads"""
        # Base query for new leads (поступления)
        new_leads_query = self.db.query(Lead).filter(

            or_(Lead.state == 'NEW', Lead.state == 'IN_WORK')
        )

        # Base query for processed leads (обработано)
        processed_leads_query = self.db.query(Lead).filter(
            Lead.state == 'PROCESSED'
        )

        # Leads with installment (на рассылке)
        mailing_leads_query = self.db.query(Lead).join(InstallmentPayment).filter(
            Lead.payment_type == "Рассрочка",  # Используем .value
            InstallmentPayment.status == PaymentStatus.PENDING,  # Используем .value
            InstallmentPayment.due_date >= datetime.utcnow()  # Не просроченные платежи
        )

        # Paid leads (оплачено)
        paid_leads_query = self.db.query(Lead).filter(
            or_(
                # Для полной оплаты: все платежи в Payment оплачены
                and_(
                    Lead.payment_type == "Единовременно",  # Используем .value
                    ~Lead.payments.any(Payment.status != PaymentStatus.PAID)  # Используем .value
                ),
                # Для рассрочки: все платежи в InstallmentPayment оплачены
                and_(
                    Lead.payment_type == "Рассрочка",  # Используем .value
                    ~Lead.installment_payments.any(InstallmentPayment.status != PaymentStatus.PAID)  # Используем .value
                )
            )
        )

        # Overdue leads (просрочено)
        overdue_leads_query = self.db.query(Lead).join(InstallmentPayment).filter(
            InstallmentPayment.status == PaymentStatus.PENDING,  # Используем .value
            InstallmentPayment.due_date < datetime.utcnow()  # Платежи просрочены
        )

        # Apply user filter if specified
        if user_id is not None:
            new_leads_query = new_leads_query.filter(Lead.user_id == user_id)
            processed_leads_query = processed_leads_query.filter(Lead.user_id == user_id)
            mailing_leads_query = mailing_leads_query.filter(Lead.user_id == user_id)
            paid_leads_query = paid_leads_query.filter(Lead.user_id == user_id)
            overdue_leads_query = overdue_leads_query.filter(Lead.user_id == user_id)

        # Execute queries
        new_leads = new_leads_query.all()
        processed_leads = processed_leads_query.all()
        mailing_leads = mailing_leads_query.all()
        paid_leads = paid_leads_query.all()
        overdue_leads = overdue_leads_query.all()

        return {
            "new_leads": {
                "count": len(new_leads),
                "leads": [self._format_lead(lead) for lead in new_leads]
            },
            "processed_leads": {
                "count": len(processed_leads),
                "leads": [self._format_lead(lead) for lead in processed_leads]
            },
            "mailing_leads": {  # На рассылке (рассрочка, ожидающие оплаты)
                "count": len(mailing_leads),
                "leads": [self._format_lead(lead) for lead in mailing_leads]
            },
            "paid_leads": {  # Оплачено
                "count": len(paid_leads),
                "leads": [self._format_lead(lead) for lead in paid_leads]
            },
            "overdue_leads": {  # Просрочено
                "count": len(overdue_leads),
                "leads": [self._format_lead(lead) for lead in overdue_leads]
            }
        }

    def _format_lead(self, lead: Lead) -> dict:
        # Определяем статус лида на основе платежей ("на рассылке", "оплачено", "просрочено")
        if lead.installment_payments:
            # Проверяем статусы платежей в InstallmentPayment
            has_overdue = any(
                payment.status == PaymentStatus.PENDING and payment.due_date < datetime.utcnow()
                for payment in lead.installment_payments
            )
            all_paid = all(
                payment.status == PaymentStatus.PAID
                for payment in lead.installment_payments
            )
            has_pending = any(
                payment.status == PaymentStatus.PENDING and payment.due_date >= datetime.utcnow()
                for payment in lead.installment_payments
            )

            if has_overdue:
                lead_status = "просрочено"
            elif all_paid:
                lead_status = "оплачено"
            elif has_pending:
                lead_status = "на рассрочке"
            else:
                lead_status = "не определен"
        else:
            # Если нет платежей по рассрочке, проверяем полные платежи
            if lead.payment_type == "Единовременно":
                all_paid = all(
                    payment.status == PaymentStatus.PAID
                    for payment in lead.payments
                )
                lead_status = "оплачено" if all_paid else "не определен"
            else:
                lead_status = "не определен"

        # Находим следующий неоплаченный платеж (для дедлайна)
        next_payment = next(
            (p for p in lead.installment_payments if p.status == PaymentStatus.PENDING),
            None
        )
        next_due_date = next_payment.due_date.strftime("%d.%m.%Y") if next_payment else None
        is_next_due_date_overdue = next_payment and next_payment.due_date < datetime.utcnow()

        return {
            "id": lead.id,
            "full_name": lead.full_name,
            "date": lead.created_at.strftime("%d.%m.%Y"),
            "contact_source": lead.contact_source,
            "region": lead.region,
            "phone": lead.phone,
            "payment_type": lead.payment_type.value if hasattr(lead.payment_type, 'value') else str(lead.payment_type),
            "total_price": lead.total_price,
            "currency": lead.currency,
            "user": f"{lead.user.first_name} {lead.user.last_name}" if lead.user else "Не назначен",
            "state": lead.state.value if hasattr(lead.state, 'value') else str(lead.state),
            "status": lead_status,
            "next_due_date": next_due_date,  # Добавляем дату следующего платежа
            "is_next_due_date_overdue": is_next_due_date_overdue  # Добавляем флаг просрочки
        }


class SalesLeadsService:

    def __init__(self, db: Session):
        self.db = db

    def get_sales_stats(self, user_id: Optional[int] = None) -> dict:
        """Get sales representatives and their lead statistics"""
        if user_id:
            # Get specific user stats
            return self._get_user_stats(user_id)

        # Get all users stats
        users = self.db.query(User).filter(User.role_id == 1).all()
        return {
            "total_stats": self._get_total_stats(),
            "sales_reps": [self._get_user_stats(user.id) for user in users]
        }

    def _get_user_stats(self, user_id: int) -> dict:
        user = self.db.query(User).get(user_id)
        if not user:
            return None

        # Новые лиды
        new_leads_count = self.db.query(Lead).filter(
            Lead.user_id == user_id,
            or_(Lead.state == 'NEW', Lead.state == 'IN_WORK')
        ).count()

        # Обработанные лиды
        processed_leads_count = self.db.query(Lead).filter(
            Lead.user_id == user_id,
            Lead.state == 'PROCESSED'
        ).count()

        # Лиды "на рассылке" (рассрочка, ожидающие оплаты)
        mailing_leads_count = self.db.query(Lead).filter(
            Lead.user_id == user_id,
            Lead.payment_type == 'Рассрочка',
        ).count()

        # Оплаченные лиды
        paid_leads_count = self.db.query(Lead).filter(
            Lead.user_id == user_id,
            or_(
                # Для полной оплаты: все платежи в Payment оплачены
                and_(
                    Lead.payment_type == "Единовременно",
                    ~Lead.payments.any(Payment.status != PaymentStatus.PAID)
                ),
                # Для рассрочки: все платежи в InstallmentPayment оплачены
                and_(
                    Lead.payment_type == "Рассрочка",
                    ~Lead.installment_payments.any(InstallmentPayment.status != PaymentStatus.PAID)
                )
            )
        ).count()

        return {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "status": self._get_user_status(user),
            "stats": {
                "new_leads": new_leads_count,
                "processed_leads": processed_leads_count,
                "mailing_leads": mailing_leads_count,
                "paid_leads": paid_leads_count
            }
        }

    def _get_total_stats(self) -> dict:
        # Общее количество новых лидов
        total_new = self.db.query(Lead).filter(or_(Lead.state == 'NEW', Lead.state == 'IN_WORK')).count()

        # Общее количество обработанных лидов
        total_processed = self.db.query(Lead).filter(Lead.state == 'PROCESSED').count()

        # Общее количество лидов "на рассылке"
        total_mailing = self.db.query(Lead).filter(
            Lead.payment_type == "Рассрочка",
        ).count()

        # Общее количество оплаченных лидов
        total_paid = self.db.query(Lead).filter(
            or_(
                # Для полной оплаты: все платежи в Payment оплачены
                and_(
                    Lead.payment_type == "Единовременно",
                    ~Lead.payments.any(Payment.status != PaymentStatus.PAID)
                ),
                # Для рассрочки: все платежи в InstallmentPayment оплачены
                and_(
                    Lead.payment_type == "Рассрочка",
                    ~Lead.installment_payments.any(InstallmentPayment.status != PaymentStatus.PAID)
                )
            )
        ).count()

        return {
            "new_leads": total_new,
            "processed_leads": total_processed,
            "mailing_leads": total_mailing,
            "paid_leads": total_paid
        }

    def _get_user_status(self, user: User) -> str:
        now = datetime.utcnow()

        if hasattr(user, 'last_login') and user.last_login:
            time_diff = now - user.last_login

            if time_diff < timedelta(minutes=10):
                return "Онлайн"
            elif time_diff < timedelta(hours=1):
                return "Недавно был в сети"
            elif time_diff < timedelta(days=1):
                return "Был в сети сегодня"
            elif time_diff < timedelta(days=7):
                return "Был в сети на этой неделе"
            else:
                return "Давно не заходил"


class LeadDetailService:
    def __init__(self, db: Session):
        self.db = db

    def get_lead_details(self, lead_id: int) -> dict:
        """Get detailed information about a specific lead"""
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None

        # Подсчитываем погашенную сумму и количество оплаченных месяцев
        paid_payments = [p for p in lead.installment_payments if p.status == PaymentStatus.PAID.value]
        paid_amount = sum(p.amount for p in paid_payments)
        paid_months = len(paid_payments)

        # Формируем историю платежей
        payment_history = [
            {
                "payment_number": p.payment_number,
                "amount": p.amount,
                "due_date": p.due_date.strftime("%d.%m.%Y"),
                "status": p.status,
                "is_overdue": p.status == PaymentStatus.PENDING and p.due_date < datetime.utcnow()
            }
            for p in lead.installment_payments
        ]

        # Находим следующий неоплаченный платеж (для дедлайна)
        next_payment = next(
            (p for p in lead.installment_payments if p.status == PaymentStatus.PENDING),
            None
        )
        next_due_date = next_payment.due_date.strftime("%d.%m.%Y") if next_payment else None
        is_next_due_date_overdue = next_payment and next_payment.due_date < datetime.utcnow()

        # Определяем статус лида
        if lead.installment_payments:
            has_overdue = any(
                payment.status == PaymentStatus.OVERDUE.value and payment.due_date < datetime.utcnow()
                for payment in lead.installment_payments
            )
            all_paid = all(
                payment.status == PaymentStatus.PAID.value
                for payment in lead.installment_payments
            )
            has_pending = any(
                payment.status == PaymentStatus.PENDING.value and payment.due_date >= datetime.utcnow()
                for payment in lead.installment_payments
            )

            if has_overdue:
                lead_status = "просрочено"
            elif all_paid:
                lead_status = "оплачено"
            elif has_pending:
                lead_status = "на рассылке"
            else:
                lead_status = "не определен"
        else:
            if lead.payment_type == PaymentType.FULL.value:
                all_paid = all(
                    payment.status == PaymentStatus.PAID.value
                    for payment in lead.payments
                )
                lead_status = "оплачено" if all_paid else "не определен"
            else:
                lead_status = "не определен"

        return {
            "id": lead.id,
            "full_name": lead.full_name,
            "contact_source": lead.contact_source,
            "phone": lead.phone,
            "square_meters": lead.square_meters,
            "rooms": lead.rooms,
            "floor": lead.floor,
            "total_price": lead.total_price,
            "currency": lead.currency,
            "monthly_payment": lead.monthly_payment,
            "installment_period": lead.installment_period,
            "installment_markup": lead.installment_markup,
            "status": lead_status,
            "paid_amount": paid_amount,
            "paid_months": paid_months,
            "payment_history": payment_history,
            "next_due_date": next_due_date,
            "is_next_due_date_overdue": is_next_due_date_overdue
        }
