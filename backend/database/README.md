# Database Module

Модуль управления базой данных: модели, CRUD операции, и сервисы.

## 📂 Структура

```
backend/database/
├── __init__.py           # Настройка engine, SessionLocal, Base
├── models.py             # Все SQLAlchemy модели
├── userservice.py        # CRUD для пользователей
├── act_service.py        # Генерация актов
├── attendanceservice.py  # Учет посещаемости
├── instagram.py          # Instagram интеграция
├── sales_service/        # CRUD для продаж и лидов
├── finance_service/      # CRUD для финансов
├── mop_service/          # CRUD для МОП
├── rop_service/          # CRUD для РОП
└── marketing/            # CRUD для маркетинга
```

## 🗃️ Модели данных

### Основные модели (models.py)

#### User - Пользователи системы
```python
class User(Base):
    __tablename__ = 'users'

    id: int
    first_name: str
    last_name: str
    login: str (unique)
    email: str (unique)
    phone: str
    role_id: int → Role
    hashed_password: str
    work_days: JSON  # ["ПН", "ВТ", ...]
    work_start_time: Time
    work_end_time: Time

    # Relationships
    role: Role
    leads: List[Lead]
    attendances: List[Attendance]
    expenses_created: List[Expense]
```

#### Role - Роли пользователей
```python
class Role(Base):
    __tablename__ = 'roles'

    id: int
    name: str (unique)  # Админ, Продажник, МОП, РОП, Финансист

    # Relationships
    users: List[User]
```

#### Lead - Лиды (потенциальные клиенты)
```python
class Lead(Base):
    __tablename__ = 'leads_prototype'

    # Основные поля
    id: int
    full_name: str
    phone: str
    region: str
    contact_source: str  # Instagram, Facebook, etc.

    # Классификация
    status: LeadStatus  # Новый, В работе, Потерян, Бронь, Продан
    state: LeadState    # warm, cold, hot, sold, lost

    # Связи
    user_id: int → User (продажник)
    user: User
    payments: List[Payment]
    comments: List[Comment]
    callbacks: List[Callback]
    contract: Contract
```

#### Payment - Платежи
```python
class Payment(Base):
    __tablename__ = 'payments'

    id: int
    lead_id: int → Lead
    amount: float
    payment_date: DateTime
    payment_type: PaymentType  # initial, installment, final, hybrid
    payment_status: PaymentStatus  # pending, completed, cancelled

    # Relationships
    lead: Lead
```

#### Expense - Расходы (РОП)
```python
class Expense(Base):
    __tablename__ = 'expenses'

    id: int
    amount: float
    category: ExpenseCategory  # marketing, salary, rent, etc.
    description: str
    expense_date: Date
    created_by_id: int → User

    # Relationships
    creator: User
```

### Связи между моделями

```
User ──┬─► Lead ──┬─► Payment
       │          ├─► Comment
       │          ├─► Contract
       │          └─► Callback
       │
       ├─► Expense
       ├─► Attendance
       └─► InstagramIntegration

Role ──► User
```

## 🔧 CRUD Services

### Паттерн CRUD

Каждый сервис реализует стандартный набор операций:

```python
class BaseCRUD:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        """Получить все записи с пагинацией"""
        pass

    def get_by_id(self, db: Session, id: int):
        """Получить запись по ID"""
        pass

    def create(self, db: Session, data: dict):
        """Создать новую запись"""
        pass

    def update(self, db: Session, id: int, updates: dict):
        """Обновить запись"""
        pass

    def delete(self, db: Session, id: int):
        """Удалить запись"""
        pass
```

### LeadCRUD (sales_service/crud.py)

```python
from backend.database.sales_service.crud import LeadCRUD

lead_crud = LeadCRUD()

# Получить все лиды
leads = lead_crud.get_all(db, skip=0, limit=50)

# Получить лиды пользователя
user_leads = lead_crud.get_user_leads(db, user_id=1)

# Создать лид
new_lead = lead_crud.create_lead(db, {
    "full_name": "Иван Иванов",
    "phone": "+998901234567",
    "region": "Ташкент",
    "contact_source": "Instagram",
    "user_id": 1
})

# Обновить статус
updated = lead_crud.update_status(db, lead_id=1, status="В работе")

# Поиск
results = lead_crud.search_leads(db, query="Иван", limit=10)
```

### Специализированные сервисы

#### LeadStatisticsService
```python
from backend.database.sales_service.crud import LeadStatisticsService

service = LeadStatisticsService(db)

# Общая статистика
stats = service.get_overall_statistics()
# → {total_leads, active_leads, sold_leads, conversion_rate, ...}

# Статистика по пользователю
user_stats = service.get_user_statistics(user_id=1)
```

#### InactiveLeadsService
```python
from backend.database.sales_service.crud import InactiveLeadsService

service = InactiveLeadsService(db)

# Получить неактивные лиды (>7 дней без активности)
inactive = service.get_inactive_leads(days=7)
```

## 📊 Работа с базой данных

### Получение сессии

```python
from backend.database import get_db

# В FastAPI эндпоинте
@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return items
```

### Транзакции

```python
from backend.database import SessionLocal

db = SessionLocal()
try:
    # Операции с БД
    user = User(name="Test")
    db.add(user)
    db.commit()
    db.refresh(user)
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
```

### Eager Loading (предзагрузка связей)

```python
from sqlalchemy.orm import joinedload

# Загрузка пользователя с ролью за один запрос
user = db.query(User).options(
    joinedload(User.role)
).filter(User.id == 1).first()

# Теперь user.role не требует дополнительного запроса
print(user.role.name)
```

### Фильтрация и сортировка

```python
# Фильтрация
active_leads = db.query(Lead).filter(
    Lead.status == "В работе",
    Lead.user_id == 1
).all()

# Сортировка
recent_leads = db.query(Lead).order_by(
    Lead.created_at.desc()
).limit(10).all()

# Пагинация
page = 2
per_page = 20
leads = db.query(Lead).offset(
    (page - 1) * per_page
).limit(per_page).all()
```

### Агрегация

```python
from sqlalchemy import func

# Подсчет
total_leads = db.query(func.count(Lead.id)).scalar()

# Сумма
total_amount = db.query(
    func.sum(Payment.amount)
).filter(Payment.payment_status == "completed").scalar()

# Группировка
by_status = db.query(
    Lead.status,
    func.count(Lead.id)
).group_by(Lead.status).all()
```

## 🆕 Добавление новой модели

### 1. Определите модель в models.py

```python
class NewModel(Base):
    __tablename__ = 'new_models'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    # Foreign Key
    user_id = Column(Integer, ForeignKey('users.id'))

    # Relationship
    user = relationship('User', back_populates='new_models')
```

### 2. Добавьте обратную связь

```python
# В класс User
class User(Base):
    # ... existing fields
    new_models = relationship('NewModel', back_populates='user')
```

### 3. Создайте миграцию

```bash
alembic revision --autogenerate -m "Add new_models table"
```

### 4. Проверьте миграцию

Откройте созданный файл в `alembic/versions/` и убедитесь, что:
- Все колонки правильно определены
- Foreign keys корректны
- Индексы добавлены где нужно

### 5. Примените миграцию

```bash
alembic upgrade head
```

### 6. Создайте CRUD сервис

```python
# backend/database/new_service/crud.py
from sqlalchemy.orm import Session
from backend.database.models import NewModel

class NewModelCRUD:
    def get_all(self, db: Session):
        return db.query(NewModel).all()

    def create(self, db: Session, name: str, user_id: int):
        item = NewModel(name=name, user_id=user_id)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
```

## ⚡ Оптимизация производительности

### 1. Используйте индексы

```python
class Lead(Base):
    # Индекс на часто используемое поле
    phone = Column(String, nullable=False, index=True)

    # Составной индекс
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
    )
```

### 2. Ленивая загрузка vs Eager loading

```python
# Плохо - N+1 проблема
for lead in leads:
    print(lead.user.name)  # Каждый раз новый запрос!

# Хорошо - один JOIN запрос
leads = db.query(Lead).options(joinedload(Lead.user)).all()
for lead in leads:
    print(lead.user.name)  # Уже загружено
```

### 3. Используйте bulk операции

```python
# Плохо - много INSERT запросов
for data in bulk_data:
    db.add(Lead(**data))
    db.commit()

# Хорошо - один bulk INSERT
db.bulk_insert_mappings(Lead, bulk_data)
db.commit()
```

### 4. Select только нужные колонки

```python
# Плохо - загружает все поля
leads = db.query(Lead).all()

# Хорошо - только нужные поля
leads = db.query(Lead.id, Lead.full_name, Lead.phone).all()
```

## 🔍 Отладка SQL

### Включите логирование SQL

```python
# settings.py
DEBUG = True  # Автоматически включает echo=True в engine

# Или вручную
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Посмотрите сгенерированный SQL

```python
from sqlalchemy.dialects import postgresql, sqlite

query = db.query(Lead).filter(Lead.status == "Новый")

# Посмотреть SQL
print(str(query.statement.compile(dialect=sqlite.dialect())))
```

## 🚨 Частые ошибки

### 1. Забыли вызвать commit()

```python
# ❌ Изменения не сохранятся!
lead.status = "Продан"

# ✅ Правильно
lead.status = "Продан"
db.commit()
```

### 2. Не закрыли сессию

```python
# ❌ Утечка соединений
db = SessionLocal()
items = db.query(Item).all()

# ✅ Используйте get_db() dependency или try/finally
db = SessionLocal()
try:
    items = db.query(Item).all()
finally:
    db.close()
```

### 3. N+1 проблема

```python
# ❌ N+1 запросов
for lead in leads:
    print(lead.user.name)  # Каждый раз запрос!

# ✅ Eager loading
leads = db.query(Lead).options(joinedload(Lead.user)).all()
```

## 📚 Дополнительные ресурсы

- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- Смотрите ARCHITECTURE.md для общего обзора архитектуры БД
