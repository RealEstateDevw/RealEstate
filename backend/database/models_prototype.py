"""Черновые/архивные модели, оставленные для参考 старой структуры (не используются)."""

# from sqlalchemy import (
#     Column, Integer, String, Float, Numeric, DateTime, ForeignKey, func
# )
# from sqlalchemy.orm import relationship
# import datetime
# from backend.database import Base
#
#
# class Salesperson(Base):
#     """
#     Модель для менеджера/продажника (привязка сделок к определённому сотруднику).
#     """
#     __tablename__ = 'salespersons'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     full_name = Column(String(255), nullable=False)
#     phone = Column(String(50), nullable=True)
#     email = Column(String(255), nullable=True)
#
#     # Если нужно хранить даты создания/обновления
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     updated_at = Column(
#         DateTime,
#         default=datetime.datetime.now,
#         onupdate=datetime.datetime.now
#     )
#
#     # Связь с Deal: один менеджер может вести множество сделок
#     deals = relationship("Deal", back_populates="salesperson")
#
#     # Если хотим, чтобы комментарии тоже имели "автора" из таблицы Salesperson
#     comments = relationship("Comment", back_populates="author")
#
#     def __repr__(self):
#         return f"<Salesperson(id={self.id}, name='{self.full_name}')>"
#
#
# class Lead(Base):
#     __tablename__ = 'leads'
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)
#     city = Column(String, nullable=False)
#     phone_number = Column(String, nullable=False)
#     contact_channel_id = Column(Integer, ForeignKey('contact_channels.id'))
#     status_id = Column(Integer, ForeignKey('statuses.id'))
#     payment_type = Column(String, nullable=False)  # Рассрочка или Полная оплата
#     estimated_amount = Column(Numeric, nullable=False)  # Предварительная сумма
#     date = Column(DateTime, nullable=False)  # Дата добавления лида
#     deal_status = Column(String, nullable=False)  # В работе, Ожидает ответа и т. д.
#
#     # Связи
#     status = relationship('Status', back_populates='leads')
#     contact_channel = relationship('ContactChannel', back_populates='leads')
#     property_details = relationship('PropertyDetail', back_populates='lead', uselist=False)
#     messages = relationship('Message', back_populates='lead')
#
#
# class Lead(Base):
#     """
#     Модель для лида (потенциального клиента).
#     """
#     __tablename__ = 'leads'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     full_name = Column(String(255), nullable=False)
#     phone_number = Column(String(50), nullable=False)
#     source = Column(String(100), nullable=False)  # например, 'Instagram Target'
#     city = Column(String(100), nullable=False)
#     status_id = Column(Integer, ForeignKey('statuses.id'))
#     payment_type = Column(String, nullable=False)  # Рассрочка или Полная оплата
#     estimated_amount = Column(Numeric, nullable=False)  # Предварительная сумма
#     date = Column(DateTime, nullable=False)  # Дата добавления лида
#     deal_status = Column(String, nullable=False)
#
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     updated_at = Column(
#         DateTime,
#         default=datetime.datetime.now,
#         onupdate=datetime.datetime.now
#     )
#
#     status = relationship('Status', back_populates='leads')
#
#
#     def __repr__(self):
#         return f"<Lead(id={self.id}, name='{self.full_name}')>"
#
#
# class Property(Base):
#     """
#     Модель для объекта недвижимости.
#     """
#     __tablename__ = 'properties'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     square_meters = Column(Float, nullable=True)  # Площадь, 180.0 и т.д.
#     rooms_count = Column(Integer, nullable=True)  # Количество комнат
#     floor = Column(Integer, nullable=True)  # Этаж
#     payment_type = Column(String(50), nullable=True)
#     base_price = Column(Numeric(18, 2), nullable=True)  # Предварительная сумма
#     monthly_payment = Column(Numeric(18, 2), nullable=True)  # Ежемес. оплата
#     payment_months = Column(Integer, nullable=True)  # Срок рассрочки (в мес.)
#
#     # Связь с Deal: один объект может быть в нескольких сделках
#     deals = relationship("Deal", back_populates="property")
#
#     def __repr__(self):
#         return f"<Property(id={self.id}, square={self.square_meters})>"
#
#
# class Deal(Base):
#     """
#     Модель для сделки (opportunity).
#     """
#     __tablename__ = 'deals'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
#     property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
#     salesperson_id = Column(Integer, ForeignKey('salespersons.id'), nullable=True)
#
#     purchase_type = Column(String(100), nullable=True)  # 'Для себя', 'Для инвестиций' и т.д.
#     status = Column(String(50), nullable=True)  # 'Новый', 'Бронирование', 'Договор'...
#
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     updated_at = Column(
#         DateTime,
#         default=datetime.datetime.now,
#         onupdate=datetime.datetime.now
#     )
#
#     # Связи
#     lead = relationship("Lead", back_populates="deals")
#     property = relationship("Property", back_populates="deals")
#     salesperson = relationship("Salesperson", back_populates="deals")
#
#     chat_messages = relationship("ChatMessage", back_populates="deal")
#     comments = relationship("Comment", back_populates="deal")
#     deal_actions = relationship("DealAction", back_populates="deal")
#
#     def __repr__(self):
#         return f"<Deal(id={self.id}, lead_id={self.lead_id}, property_id={self.property_id})>"
#
#
# class ChatMessage(Base):
#     """
#     Модель для хранения истории переписки (чат с клиентом).
#     """
#     __tablename__ = 'chat_messages'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     deal_id = Column(Integer, ForeignKey('deals.id'), nullable=False)
#
#     sender_type = Column(String(50), nullable=True)  # 'client' или 'manager' и т.д.
#     message_text = Column(String, nullable=False)
#
#     created_at = Column(DateTime, default=datetime.datetime.now)
#
#     # Связь с Deal
#     deal = relationship("Deal", back_populates="chat_messages")
#
#     def __repr__(self):
#         return f"<ChatMessage(id={self.id}, deal_id={self.deal_id})>"
#
#
# class Comment(Base):
#     """
#     Модель для хранения комментариев менеджера по конкретной сделке.
#     """
#     __tablename__ = 'comments'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     deal_id = Column(Integer, ForeignKey('deals.id'), nullable=False)
#
#     # Если хотим сохранять автора комментария
#     author_id = Column(Integer, ForeignKey('salespersons.id'), nullable=True)
#
#     comment_text = Column(String, nullable=False)
#     created_at = Column(DateTime, default=datetime.datetime.now)
#
#     # Связи
#     deal = relationship("Deal", back_populates="comments")
#     author = relationship("Salesperson", back_populates="comments")
#
#     def __repr__(self):
#         return f"<Comment(id={self.id}, deal_id={self.deal_id})>"
#
#
# class DealAction(Base):
#     """
#     Модель для фиксирования ключевых действий по сделке
#     (например, 'Фиксация клиента', 'Бронирование', 'Заключение договора').
#     """
#     __tablename__ = 'deal_actions'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     deal_id = Column(Integer, ForeignKey('deals.id'), nullable=False)
#
#     action_type = Column(String(50), nullable=False)  # 'fix_client', 'booking' и т.п.
#     status = Column(String(50), nullable=True)  # 'выполнено', 'ожидается', ...
#     created_at = Column(DateTime, default=datetime.datetime.now)
#     completed_at = Column(DateTime, nullable=True)
#
#     # Связь с Deal
#     deal = relationship("Deal", back_populates="deal_actions")
#
#     def __repr__(self):
#         return f"<DealAction(id={self.id}, action_type={self.action_type})>"
