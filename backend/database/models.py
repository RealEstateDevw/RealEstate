import enum
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.api.finance.schemas import PaymentStatus, PaymentType
from backend.api.leads.schemas import LeadState, LeadStatus
from backend.api.rop.schemas import ExpenseCategory
from backend.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Time, ARRAY, Date, JSON, Float, Enum, Text, \
    Boolean
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

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    # Soft-delete and reassignment support
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="leads", lazy="subquery")

    # Additional fields for lead management
    notes = Column(String, nullable=True)  # For storing additional information
    next_contact_date = Column(DateTime, nullable=True)

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
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, nullable=False, index=True)
    lang = Column(Enum(UserLang), nullable=False, default=UserLang.ru)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=ZoneInfo("Asia/Tashkent")))


class CampaignPlatform(enum.Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"


class CampaignStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


# 2) Собственно модель Campaign
class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # Название кампании
    platform = Column(Enum(CampaignPlatform), nullable=False)
    account = Column(String, nullable=False)  # Например "@Bahor.LC"

    launch_date = Column(Date, nullable=False)  # Дата запуска
    end_date = Column(Date, nullable=False)  # Дата окончания

    planned_budget = Column(Float, nullable=False)  # Планируемый бюджет
    spent_budget = Column(Float, nullable=False)  # Использовано

    views = Column(Integer, nullable=False)  # Просмотры
    clicks = Column(Integer, nullable=False)  # Переходы

    leads_total = Column(Integer, nullable=False)  # Получено лидов
    leads_active = Column(Integer, nullable=False)  # Активных лидов

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

    def __repr__(self):
        return (
            f"<Campaign(id={self.id}, name={self.name!r}, "
            f"platform={self.platform.value}, status={self.status.value})>"
        )
