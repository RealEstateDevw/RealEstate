"""ORM модели приложения (пользователи, лиды, платежи, интеграции и пр.).

Файл содержит все основные таблицы CRM/маркетинга/финансов. Группы сущностей:
- роли и пользователи (Role, User, Attendance);
- CRM: Lead, Callback, Comment, ChatMessage, Deal-related данные;
- Финансы: Contract, Payment, Transaction, InstallmentPayment, Expense;
- Маркетинг: Campaign, DrawUser;
- Справочники жилых комплексов/блоков/квартир для шахматок.

Каждая модель использует Base из backend.database и определяет отношения
через SQLAlchemy relationship для удобной навигации.
"""

import enum
from datetime import datetime, date
from zoneinfo import ZoneInfo

from backend.api.finance.schemas import PaymentStatus, PaymentType
from backend.api.leads.schemas import LeadState, LeadStatus
from backend.api.rop.schemas import ExpenseCategory
from backend.database import Base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Time, ARRAY, Date, JSON, Float, Enum, Text, \
    Boolean, UniqueConstraint
from sqlalchemy.orm import relationship


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    # Связь с таблицей пользователей
    users = relationship('User', back_populates='role')


# Таблица пользователей
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    login = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    company = Column(String, nullable=False)
    work_start_time = Column(Time, nullable=True, default="12:00:00")  # Время начала работы
    work_end_time = Column(Time, nullable=True, default="23:59:59")  # Время окончания работы
    work_days = Column(JSON, nullable=False)  # Рабочие дни (например, ["ПН", "ВТ", "СР"])
    role_id = Column(Integer, ForeignKey('roles.id'))  # Связь с таблицей ролей
    hashed_password = Column(String, nullable=False)  # Хеш пароля
    background_theme = Column(String, nullable=True, default=None)
    reg_date = Column(DateTime, default=datetime.now())
    last_login = Column(DateTime, default=datetime.now())
    # telegram_id = Column(Integer, unique=True, nullable=True, index=True)

    # Связи
    role = relationship('Role', back_populates='users', lazy="subquery")
    attendances = relationship("Attendance", back_populates="user", lazy='joined')
    leads = relationship("Lead", back_populates="user")
    comments = relationship("Comment", back_populates="author")
    expenses_created = relationship("Expense", back_populates="creator")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Attendance(Base):
    __tablename__ = 'attendances'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(Time, nullable=True)
    check_out = Column(Time, nullable=True)
    status = Column(String, nullable=True)  # например, "присутствовал", "опоздал", "отсутствовал"

    # Опционально: связь с пользователем
    user = relationship("User", back_populates="attendances")


# Таблица доступов (может быть привязана к пользователю или роли)
class Access(Base):
    __tablename__ = 'accesses'
    id = Column(Integer, primary_key=True)
    resource = Column(String, nullable=False)  # Название ресурса или раздела (например, "CRM", "Отчеты")
    permission = Column(String, nullable=False)  # Права доступа (чтение, запись, администрирование и т. д.)
    role_id = Column(Integer, ForeignKey('roles.id'))  # Доступ на уровне роли
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Индивидуальный доступ для пользователя

    # Связи
    role = relationship('Role')
    user = relationship('User')

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.user_id}')>"


class Lead(Base):
    __tablename__ = 'leads_prototype'

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)

    # Contact info
    phone = Column(String, nullable=False)
    region = Column(String, nullable=False)  # г.Ташкент, г.Бухара и т.д.
    contact_source = Column(String, nullable=False)  # Instagram, Facebook, Telegram, etc.

    # Lead classification
    status = Column(Enum(LeadStatus), nullable=False)
    state = Column(Enum(LeadState), nullable=False)

    # Property details (if applicable)
    square_meters = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)
    floor = Column(Integer, nullable=True)
    complex_name = Column(String, nullable=True)
    number_apartments = Column(Integer, nullable=True)
    block = Column(String, nullable=True)

    # Financial details
    total_price = Column(Float, nullable=False)  # Общая стоимость
    down_payment = Column(Float, nullable=True)  # Сумма первоначального взноса
    square_meters_price = Column(Float, nullable=True)  # Стоимость квадратуры
    currency = Column(String, nullable=False, default="UZS")
    down_payment_percent = Column(String, nullable=True)  # Процент первоначального взноса
    payment_type = Column(String, nullable=False)  # Рассрочка/Полная
    monthly_payment = Column(Float, nullable=True)  # For installment plans
    installment_period = Column(Integer, nullable=True)  # количество месяцев рассрочки
    installment_markup = Column(Float, nullable=True)  # процент переплаты (например, 10%)
    hybrid_final_payment = Column(Float, nullable=True)  # Остаточный платеж для гибридной рассрочки

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=True, index=True)  # Связь с рекламной кампанией
    # Soft-delete and reassignment support
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="leads", lazy="subquery")
    campaign = relationship("Campaign", back_populates="leads")

    # Additional fields for lead management
    notes = Column(String, nullable=True)  # For storing additional information
    next_contact_date = Column(DateTime, nullable=True)

    # Telegram Mini App integration
    telegram_user_id = Column(BigInteger, nullable=True, index=True)  # Telegram user ID from Mini App
    interest_score_snapshot = Column(Integer, nullable=True)  # Interest score at lead creation

    messages = relationship("ChatMessage", back_populates="lead", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="lead", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="lead", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="lead", cascade="all, delete-orphan")
    installment_payments = relationship("InstallmentPayment", back_populates="lead", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="lead", cascade="all, delete-orphan")
    callbacks = relationship("Callback", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.full_name}')>"

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}

        # Добавляем user, если он есть
        if self.user:
            data["user"] = self.user.to_dict()  # Убедись, что у User тоже есть to_dict()
        else:
            data["user"] = None

        data["is_active"] = self.is_active
        data["deleted_at"] = self.deleted_at

        return data


class Callback(Base):
    __tablename__ = 'callbacks'

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads_prototype.id'), nullable=False)
    callback_time = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    is_missed = Column(Boolean, default=False, nullable=False)  # New field for missed status
    confirmation_file = Column(String, nullable=True)  # Path or URL to voice file or other evidence
    confirmation_note = Column(String, nullable=True)  # Optional note
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with Lead
    lead = relationship("Lead", back_populates="callbacks")


class SenderRole(enum.Enum):
    CLIENT = "client"
    SALES = "sales"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads_prototype.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source = Column(String, nullable=False, default="telegram")  # 'instagram' или 'telegram'
    text = Column(String, nullable=False)

    sender_id = Column(Integer, nullable=False)

    sender_role = Column(Enum(SenderRole), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    is_from_sales = Column(Boolean, nullable=False, default=False, index=True)

    lead = relationship(
        "Lead",
        back_populates="messages",
        lazy="joined",

    )

    def __repr__(self):
        role = "Sales" if self.is_from_sales else "Client"
        ts = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"<ChatMessage(lead={self.lead_id}, sender={self.sender_id} ({role}), at={ts})>"

    def to_dict(self):
        """
        {
            'id': ...,
            'lead_id': ...,
            'text': ...,
            'sender_id': ...,
            'sender_role': 'client' или 'sales',
            'created_at': '2025-06-02T14:09:56',
            'is_from_sales': True или False
        }
        """
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "text": self.text,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role.value,
            "created_at": self.created_at.isoformat(),
            "is_from_sales": self.is_from_sales,
            "source": self.source,
        }


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads_prototype.id"))
    author_id = Column(Integer, ForeignKey("users.id"))

    lead = relationship("Lead", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads_prototype.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(Enum(PaymentType), nullable=False)
    due_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    lead = relationship("Lead", back_populates="payments")
    transactions = relationship("Transaction", back_populates="payment", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads_prototype.id'), nullable=False)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    lead = relationship("Lead", back_populates="transactions")
    payment = relationship("Payment", back_populates="transactions")


class InstallmentPayment(Base):
    __tablename__ = 'installment_payments'

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads_prototype.id'), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    payment_number = Column(Integer, nullable=False)
    total_payments = Column(Integer, nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    lead = relationship("Lead", back_populates="installment_payments")


class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(PaymentStatus), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Новое поле для категории расхода
    category = Column(Enum(ExpenseCategory), default=ExpenseCategory.HOUSEHOLD, nullable=False)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator = relationship("User", back_populates="expenses_created")

    check_photos = relationship("CheckPhotoExpense", back_populates="expense")

    def to_dict(self):
        data = {
            "id": self.id,
            "title": self.title,
            "amount": self.amount,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "payment_date": self.payment_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "category": self.category.value if self.category else None
        }
        if self.creator:
            data["creator"] = self.creator.to_dict()
        else:
            data["creator"] = None
        return data


class CheckPhotoExpense(Base):
    __tablename__ = 'check_photos'

    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey('expenses.id', name='fk_check_photos_expense_id_expenses'), nullable=False)
    photo_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    expense = relationship("Expense", back_populates="check_photos")


class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads_prototype.id'), nullable=False)
    contract_number = Column(String, nullable=False, unique=True)
    signing_date = Column(DateTime, nullable=False)
    terms = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Ожидает подтверждения")
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="contracts")


class PriceHistory(Base):
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True)
    floor = Column(Integer, nullable=False)
    unit_size = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PriceHistory(floor={self.floor}, unit_size={self.unit_size}, price={self.price}, recorded_at={self.recorded_at})>"


class TelegramRole(enum.Enum):
    client = "client"
    sales = "sales"


class TelegramAccount(Base):
    """
    Храним связь между telegram_id и вашим CRM-пользователем (User).
    Через role_id → Role в CRM можно узнать, Sales или нет. Но
    для простоты заведём здесь явное поле role (client/sales).
    """
    __tablename__ = 'telegram_accounts'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    crm_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(Enum(TelegramRole), nullable=False)
    # Время регистрации (при первом /start)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Если нужно, можно держать связь на CRM-пользователя:
    crm_user = relationship("User", backref="telegram_account", lazy="joined")


class ClientRequestStatus(enum.Enum):
    new = "new"
    taken = "taken"
    closed = "closed"


class ClientRequest(Base):
    """
    Запись каждого клика «Связаться с продажником» от клиента.
    После нажатия клиентом мы создаём эту запись со статусом 'new'.
    Когда продажник нажмёт «Взять клиента», он обновит эту запись status->'taken',
    а в поле sales_tg_id запишет telegram_id продажника.
    """
    __tablename__ = 'client_requests'

    id = Column(Integer, primary_key=True)
    client_tg_id = Column(Integer, nullable=False, index=True)
    status = Column(Enum(ClientRequestStatus), default=ClientRequestStatus.new, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    taken_at = Column(DateTime, nullable=True)
    # Когда продажник «берёт» клиента, запомним его telegram_id
    sales_tg_id = Column(Integer, nullable=True)

    # Когда продажник «закрывает» запрос (после завершения общения), можно ставить status='closed'
    closed_at = Column(DateTime, nullable=True)

    # Опционально: можно хранить lead_id, если сразу привязали к лид-карточке
    lead_id = Column(Integer, ForeignKey("leads_prototype.id"), nullable=True)

    # Связь на Lead (если привязали)
    lead = relationship("Lead", backref="client_requests", lazy="joined")


class UserLang(enum.Enum):
    ru = "ru"
    uz = "uz"


class DrawUser(Base):
    __tablename__ = 'draw_users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, nullable=False, index=True)
    lang = Column(Enum(UserLang), nullable=False, default=UserLang.ru)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=ZoneInfo("Asia/Tashkent")))


class CampaignPlatform(enum.Enum):
    """Платформы для рекламных кампаний."""
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TELEGRAM = "TELEGRAM"
    GOOGLE = "GOOGLE"
    TIKTOK = "TIKTOK"


class CampaignStatus(enum.Enum):
    """Статусы рекламных кампаний."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class Campaign(Base):
    """
    Рекламная кампания маркетинга.

    Хранит данные о рекламной кампании, включая бюджет, метрики
    и UTM-параметры для отслеживания переходов.
    """
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # Название кампании
    platform = Column(Enum(CampaignPlatform), nullable=False)
    account = Column(String, nullable=True)  # Например "@Bahor.LC"

    # Даты
    launch_date = Column(Date, nullable=False)  # Дата запуска
    end_date = Column(Date, nullable=True)  # Дата окончания

    # Бюджет
    planned_budget = Column(Float, nullable=False, default=0)  # Планируемый бюджет
    spent_budget = Column(Float, nullable=False, default=0)  # Использовано

    # Метрики (обновляются автоматически или вручную)
    views = Column(Integer, nullable=False, default=0)  # Просмотры
    clicks = Column(Integer, nullable=False, default=0)  # Переходы на сайт/mini app

    # UTM-параметры для трекинга
    utm_source = Column(String, unique=True, nullable=True)  # Уникальный идентификатор кампании
    utm_medium = Column(String, nullable=True)  # Тип трафика (cpc, banner, email)
    utm_campaign = Column(String, nullable=True)  # Название кампании для UTM
    utm_link = Column(String, nullable=True)  # Полная сгенерированная ссылка

    # Целевой URL (куда ведёт ссылка)
    target_url = Column(String, nullable=True, default="https://t.me/bahor_lc_bot/app")

    status = Column(
        Enum(CampaignStatus),
        nullable=False,
        default=CampaignStatus.ACTIVE
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=ZoneInfo("UTC"))
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=ZoneInfo("UTC")),
        onupdate=lambda: datetime.now(tz=ZoneInfo("UTC"))
    )

    # Связь с лидами
    leads = relationship("Lead", back_populates="campaign", lazy="dynamic")

    def __repr__(self):
        return (
            f"<Campaign(id={self.id}, name={self.name!r}, "
            f"platform={self.platform.value}, status={self.status.value})>"
        )

    @property
    def leads_count(self) -> int:
        """Общее количество лидов с этой кампании."""
        return self.leads.count() if self.leads else 0

    @property
    def deals_count(self) -> int:
        """Количество сделок (лиды со статусом 'Закрыт')."""
        from backend.api.leads.schemas import LeadState
        return self.leads.filter_by(state=LeadState.CLOSED).count() if self.leads else 0

    @property
    def cr_lead(self) -> float:
        """CR_lead = (Лиды / Переходы) × 100%."""
        if self.clicks == 0:
            return 0.0
        return round((self.leads_count / self.clicks) * 100, 2)

    @property
    def cr_sale(self) -> float:
        """CR_sale = (Сделки / Лиды) × 100%."""
        if self.leads_count == 0:
            return 0.0
        return round((self.deals_count / self.leads_count) * 100, 2)

    @property
    def cr_total(self) -> float:
        """CR_total = (Сделки / Переходы) × 100%."""
        if self.clicks == 0:
            return 0.0
        return round((self.deals_count / self.clicks) * 100, 2)

    @property
    def cpa(self) -> float:
        """CPA = Бюджет / Лиды (стоимость привлечения лида)."""
        if self.leads_count == 0:
            return 0.0
        return round(self.spent_budget / self.leads_count, 2)

    @property
    def cps(self) -> float:
        """CPS = Бюджет / Сделки (стоимость привлечения сделки)."""
        if self.deals_count == 0:
            return 0.0
        return round(self.spent_budget / self.deals_count, 2)

    @property
    def cost_per_click(self) -> float:
        """Стоимость одного перехода."""
        if self.clicks == 0:
            return 0.0
        return round(self.spent_budget / self.clicks, 2)

    @property
    def health_status(self) -> str:
        """
        Двухфакторная оценка здоровья кампании.

        Returns:
            'danger' - CR_total низкий + CPS высокий → выключить
            'success' - CR_total высокий + CPS низкий → масштабировать
            'warning_sales' - CR_lead высокий + CR_sale низкий → проблема продаж
            'warning_creative' - CR_lead низкий + CR_sale высокий → проблема креатива
            'neutral' - нет данных или нормальные показатели
        """
        # Пороговые значения (можно настроить)
        CR_TOTAL_LOW = 1.0  # менее 1% конверсия в сделку - низкая
        CR_TOTAL_HIGH = 5.0  # более 5% - высокая
        CPS_HIGH = 100.0  # более $100 за сделку - дорого
        CR_LEAD_LOW = 5.0  # менее 5% лидов от переходов - низкая
        CR_LEAD_HIGH = 15.0  # более 15% - высокая
        CR_SALE_LOW = 10.0  # менее 10% сделок от лидов - низкая
        CR_SALE_HIGH = 30.0  # более 30% - высокая

        # Недостаточно данных
        if self.clicks < 100:
            return "neutral"

        # CR_total низкий + CPS высокий → выключить
        if self.cr_total < CR_TOTAL_LOW and self.cps > CPS_HIGH:
            return "danger"

        # CR_total высокий + CPS низкий → масштабировать
        if self.cr_total > CR_TOTAL_HIGH and (self.cps < CPS_HIGH or self.cps == 0):
            return "success"

        # CR_lead высокий + CR_sale низкий → проблема продаж
        if self.cr_lead > CR_LEAD_HIGH and self.cr_sale < CR_SALE_LOW:
            return "warning_sales"

        # CR_lead низкий + CR_sale высокий → проблема креатива
        if self.cr_lead < CR_LEAD_LOW and self.cr_sale > CR_SALE_HIGH:
            return "warning_creative"

        return "neutral"


class ResidentialComplex(Base):
    __tablename__ = 'residential_complexes'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=True)
    city = Column(String, nullable=True)
    address = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Настройки рассрочки
    installment_months = Column(Integer, nullable=False, default=36)
    installment_start_date = Column(Date, nullable=False, default=date(2025, 12, 1))
    hybrid_installment_enabled = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    apartments = relationship("ApartmentUnit", back_populates="complex", cascade="all, delete-orphan")
    contract_entries = relationship("ContractRegistryEntry", back_populates="complex", cascade="all, delete-orphan")
    price_entries = relationship("ChessboardPriceEntry", back_populates="complex", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ResidentialComplex(id={self.id}, name={self.name!r})>"


class ApartmentUnit(Base):
    __tablename__ = 'apartment_units'

    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey('residential_complexes.id', ondelete='CASCADE'), nullable=False, index=True)
    block_name = Column(String, nullable=False)
    unit_type = Column(String, nullable=True)
    status = Column(String, nullable=False)
    rooms = Column(Integer, nullable=True)
    unit_number = Column(String, nullable=False)
    area_sqm = Column(Float, nullable=True)
    floor = Column(Integer, nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    complex = relationship("ResidentialComplex", back_populates="apartments")
    contracts = relationship("ContractRegistryEntry", back_populates="apartment")

    __table_args__ = (
        UniqueConstraint('complex_id', 'block_name', 'floor', 'unit_number', name='uq_apartment_unit'),
    )

    def __repr__(self):
        return (
            f"<ApartmentUnit(id={self.id}, complex={self.complex_id}, block={self.block_name!r}, "
            f"unit={self.unit_number!r}, status={self.status!r})>"
        )


class ContractRegistryEntry(Base):
    __tablename__ = 'contract_registry_entries'

    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey('residential_complexes.id', ondelete='CASCADE'), nullable=False, index=True)
    apartment_id = Column(Integer, ForeignKey('apartment_units.id', ondelete='SET NULL'), nullable=True, index=True)
    contract_number = Column(String, nullable=False)
    contract_date = Column(Date, nullable=False)
    block_name = Column(String, nullable=True)
    floor = Column(Integer, nullable=True)
    apartment_number = Column(String, nullable=True)
    rooms = Column(Integer, nullable=True)
    area_sqm = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    price_per_sqm = Column(Float, nullable=True)
    down_payment_percent = Column(Float, nullable=True)
    down_payment_amount = Column(Float, nullable=True)
    buyer_full_name = Column(String, nullable=False)
    buyer_passport_series = Column(String, nullable=True)
    buyer_pinfl = Column(String, nullable=True)
    issued_by = Column(String, nullable=True)
    registration_address = Column(Text, nullable=True)
    phone_number = Column(String, nullable=True)
    sales_department = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    complex = relationship("ResidentialComplex", back_populates="contract_entries")
    apartment = relationship("ApartmentUnit", back_populates="contracts")

    __table_args__ = (
        UniqueConstraint('complex_id', 'contract_number', name='uq_contract_registry_contract'),
    )

    def __repr__(self):
        return f"<ContractRegistryEntry(id={self.id}, contract={self.contract_number!r})>"


class ChessboardPriceEntry(Base):
    __tablename__ = 'chessboard_price_entries'

    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey('residential_complexes.id', ondelete='CASCADE'), nullable=False, index=True)
    floor = Column(Integer, nullable=False)
    category_key = Column(String, nullable=False)
    price_per_sqm = Column(Float, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    complex = relationship("ResidentialComplex", back_populates="price_entries")

    __table_args__ = (
        UniqueConstraint('complex_id', 'floor', 'category_key', name='uq_chessboard_price_entry'),
    )

    def __repr__(self):
        return (
            f"<ChessboardPriceEntry(id={self.id}, complex={self.complex_id}, floor={self.floor}, "
            f"category={self.category_key!r})>"
        )


# =============================================================================
# TELEGRAM MINI APP MODELS
# =============================================================================

class TelegramMiniAppUser(Base):
    """
    Пользователи Telegram Mini App.
    Связывает Telegram ID с источником рекламы (PAYLOAD).
    """
    __tablename__ = 'telegram_miniapp_users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    source_payload = Column(String(100), nullable=False, default="telegram")  # PAYLOAD из рекламы
    lead_id = Column(Integer, ForeignKey("leads_prototype.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interest_scores = relationship("ApartmentInterestScore", back_populates="user", cascade="all, delete-orphan")
    lead_requests = relationship("MiniAppLeadRequest", back_populates="user", cascade="all, delete-orphan")
    lead = relationship("Lead", backref="telegram_miniapp_user")

    def __repr__(self):
        return f"<TelegramMiniAppUser(id={self.id}, telegram_id={self.telegram_id})>"


class ApartmentInterestScore(Base):
    """
    Скоринг интересов по квартирам для каждого пользователя.

    Система баллов:
    - +1 за каждый просмотр карточки
    - +1 за каждые 10 секунд на карточке (max +12)
    - +5 за добавление в избранное
    - +3 за просмотр условий оплаты
    - +2 за просмотр на карте
    """
    __tablename__ = 'apartment_interest_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('telegram_miniapp_users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Apartment identification
    complex_name = Column(String, nullable=False, index=True)
    block_name = Column(String, nullable=False)
    floor = Column(Integer, nullable=False)
    unit_number = Column(String, nullable=False)
    area_sqm = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)

    # Score components
    view_count = Column(Integer, nullable=False, default=0)        # +1 за просмотр
    time_score = Column(Integer, nullable=False, default=0)        # +1/10сек, max 12
    favorites_bonus = Column(Integer, nullable=False, default=0)   # +5
    payment_view_bonus = Column(Integer, nullable=False, default=0)  # +3
    map_view_bonus = Column(Integer, nullable=False, default=0)    # +2
    total_score = Column(Integer, nullable=False, default=0)

    # Timing
    last_viewed_at = Column(DateTime, nullable=True)
    total_time_seconds = Column(Integer, nullable=False, default=0)  # max 180

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("TelegramMiniAppUser", back_populates="interest_scores")

    __table_args__ = (
        UniqueConstraint('user_id', 'complex_name', 'block_name', 'floor', 'unit_number',
                         name='uq_interest_user_apartment'),
    )

    def __repr__(self):
        return f"<ApartmentInterestScore(user={self.user_id}, apartment={self.unit_number}, score={self.total_score})>"

    def recalculate_total(self):
        """Пересчитать total_score с учетом freshness bonus."""
        base_score = (
            self.view_count +
            self.time_score +
            self.favorites_bonus +
            self.payment_view_bonus +
            self.map_view_bonus
        )

        # Freshness bonus
        freshness_bonus = 0
        if self.last_viewed_at:
            now = datetime.utcnow()
            hours_since = (now - self.last_viewed_at).total_seconds() / 3600
            if hours_since < 1:
                freshness_bonus = 3
            elif hours_since < 24:
                freshness_bonus = 2
            elif hours_since < 168:  # 7 days
                freshness_bonus = 1

        self.total_score = base_score + freshness_bonus
        return self.total_score


class MiniAppLeadRequestType(enum.Enum):
    """Тип заявки из Mini App."""
    LEAVE_REQUEST = "leave_request"  # Оставить заявку
    BOOK = "book"                    # Забронировать
    QUESTION = "question"            # Есть вопрос


class MiniAppLeadRequestStatus(enum.Enum):
    """Статус заявки из Mini App."""
    PENDING = "pending"      # Ожидает подтверждения в боте
    CONFIRMED = "confirmed"  # Пользователь подтвердил
    DECLINED = "declined"    # Пользователь отказался
    CONVERTED = "converted"  # Конвертирован в Lead


class MiniAppLeadRequest(Base):
    """
    Заявки из Mini App.
    Связывает действие пользователя в Mini App с ботом и CRM.
    """
    __tablename__ = 'miniapp_lead_requests'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('telegram_miniapp_users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Request type and status
    request_type = Column(Enum(MiniAppLeadRequestType), nullable=False)
    status = Column(Enum(MiniAppLeadRequestStatus), nullable=False, default=MiniAppLeadRequestStatus.PENDING)

    # Apartment context (optional for "question" type)
    complex_name = Column(String, nullable=True)
    block_name = Column(String, nullable=True)
    floor = Column(Integer, nullable=True)
    unit_number = Column(String, nullable=True)
    area_sqm = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)
    price_snapshot = Column(Float, nullable=True)
    payment_type_interest = Column(String, nullable=True)  # какой тип оплаты смотрел

    # Interest score at request time
    interest_score = Column(Integer, nullable=True)

    # Resulting lead
    lead_id = Column(Integer, ForeignKey("leads_prototype.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("TelegramMiniAppUser", back_populates="lead_requests")
    lead = relationship("Lead", backref="miniapp_requests")

    def __repr__(self):
        return f"<MiniAppLeadRequest(id={self.id}, type={self.request_type.value}, status={self.status.value})>"
