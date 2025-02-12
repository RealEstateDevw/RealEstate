from datetime import datetime

from backend.api.leads.schemas import LeadState, LeadStatus
from backend.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Time, ARRAY, Date, JSON, Float, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum


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
    reg_date = Column(DateTime, default=datetime.now())
    # Связи
    role = relationship('Role', back_populates='users', lazy="subquery")
    attendances = relationship("Attendance", back_populates="user", lazy='joined')
    leads = relationship("Lead", back_populates="user")


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
    square_meters = Column(Integer, nullable=True)
    rooms = Column(Integer, nullable=True)
    floor = Column(Integer, nullable=True)

    # Financial details
    total_price = Column(Float, nullable=False)  # Предварительная сумма
    currency = Column(String, nullable=False, default="UZS")
    payment_type = Column(String, nullable=False)  # Рассрочка/Полная
    monthly_payment = Column(Float, nullable=True)  # For installment plans
    installment_period = Column(Integer, nullable=True)  # количество месяцев рассрочки
    installment_markup = Column(Float, nullable=True)  # процент переплаты (например, 10%)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relations
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="leads")

    # Additional fields for lead management
    notes = Column(String, nullable=True)  # For storing additional information
    next_contact_date = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.full_name}')>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

