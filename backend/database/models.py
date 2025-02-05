from datetime import datetime

from backend.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Time, ARRAY, Date, JSON
from sqlalchemy.orm import relationship


# model User
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
    work_start_time = Column(Time, nullable=True)  # Время начала работы
    work_end_time = Column(Time, nullable=True)  # Время окончания работы
    work_days = Column(JSON, nullable=False)  # Рабочие дни (например, ["ПН", "ВТ", "СР"])
    role_id = Column(Integer, ForeignKey('roles.id'))  # Связь с таблицей ролей
    hashed_password = Column(String, nullable=False)  # Хеш пароля
    # Связи
    role = relationship('Role', back_populates='users')


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
