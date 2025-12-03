# Руководство для разработчиков

Добро пожаловать в проект RealEstate CRM! Это руководство поможет вам быстро начать работу и понять структуру проекта.

## 📋 Содержание

- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [Архитектурные принципы](#архитектурные-принципы)
- [Работа с базой данных](#работа-с-базой-данных)
- [Добавление новой функциональности](#добавление-новой-функциональности)
- [Стандарты кода](#стандарты-кода)
- [Тестирование](#тестирование)
- [Деплой](#деплой)

## 🚀 Быстрый старт

### Шаг 1: Клонирование и настройка окружения

```bash
# Клонируем репозиторий
git clone <repository-url>
cd RealEstate

# Создаем виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt
```

### Шаг 2: Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Database
DATABASE_URL=sqlite:///data.db

# JWT Settings
SECRET_KEY=your_secret_key_here_CHANGE_THIS
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Telegram Bot (опционально)
BOT_TOKEN=your_bot_token_here

# Instagram Integration (опционально)
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/instagram/callback

# Google Sheets (опционально)
GOOGLE_SHEETS_API_KEY=your_api_key
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json

# Email Settings (для уведомлений)
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Celery (для асинхронных задач)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=True

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Шаг 3: Инициализация базы данных

```bash
# Применяем миграции
alembic upgrade head

# База данных создастся автоматически при первом запуске
# Роли инициализируются автоматически
```

### Шаг 4: Создание первого пользователя

Вы можете создать пользователя через API или напрямую в коде:

```python
# Используйте endpoint POST /api/users/register
# или выполните скрипт для создания админа
```

### Шаг 5: Запуск приложения

```bash
# Запуск в режиме разработки
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Приложение будет доступно по адресу:
# http://localhost:8000
```

### Шаг 6: (Опционально) Запуск Celery

```bash
# В отдельном терминале запустите Redis
docker run -d -p 6379:6379 redis:alpine

# Запуск Celery worker
celery -A celery_proccess worker --loglevel=info

# В еще одном терминале - Celery beat
celery -A celery_proccess beat --loglevel=info
```

## 📁 Структура проекта

```
RealEstate/
│
├── backend/                    # Весь backend код
│   ├── api/                   # REST API эндпоинты (возвращают JSON)
│   │   ├── leads/            # API для работы с лидами
│   │   ├── finance/          # API финансовых операций
│   │   ├── mop/              # API для МОП
│   │   ├── rop/              # API для РОП
│   │   ├── users/            # API пользователей
│   │   ├── complexes/        # API жилых комплексов
│   │   ├── draws/            # API для чертежей/планировок
│   │   ├── instagram/        # API интеграции с Instagram
│   │   └── payment_options/  # API вариантов оплаты
│   │
│   ├── crm/                   # Frontend маршруты (возвращают HTML)
│   │   ├── admin/            # Админ панель
│   │   ├── seller/           # Панель продажника
│   │   ├── mop/              # Панель МОП
│   │   ├── rop/              # Панель РОП
│   │   ├── finance/          # Панель финансиста
│   │   ├── marketing/        # Панель маркетинга
│   │   └── shaxmatki/        # Публичные шахматки квартир
│   │
│   ├── database/              # Модели и CRUD операции
│   │   ├── models.py         # SQLAlchemy модели
│   │   ├── __init__.py       # Настройка БД и сессий
│   │   ├── userservice.py    # CRUD для пользователей
│   │   ├── sales_service/    # CRUD для продаж
│   │   ├── finance_service/  # CRUD для финансов
│   │   ├── mop_service/      # CRUD для МОП
│   │   ├── rop_service/      # CRUD для РОП
│   │   ├── marketing/        # CRUD для маркетинга
│   │   └── instagram.py      # CRUD для Instagram
│   │
│   ├── core/                  # Ядро приложения
│   │   ├── auth.py           # JWT аутентификация
│   │   ├── deps.py           # FastAPI зависимости
│   │   ├── middleware.py     # Middleware компоненты
│   │   ├── exceptions.py     # Обработчики ошибок
│   │   ├── cache_utils.py    # Утилиты кэширования
│   │   ├── rate_limiter.py   # Rate limiting
│   │   ├── logging_config.py # Настройка логирования
│   │   └── validators.py     # Валидаторы данных
│   │
│   └── bot/                   # Telegram бот
│       ├── main.py           # Инициализация бота
│       ├── handlers/         # Обработчики команд
│       └── states.py         # FSM состояния
│
├── frontend/                  # HTML шаблоны
│   ├── admin/                # Шаблоны админки
│   ├── seller/               # Шаблоны продажников
│   ├── mop/                  # Шаблоны МОП
│   ├── rop/                  # Шаблоны РОП
│   ├── finance/              # Шаблоны финансов
│   ├── marketing/            # Шаблоны маркетинга
│   ├── landing/              # Публичные лендинги ЖК
│   ├── shaxmatki/            # Публичные шахматки
│   ├── partials/             # Переиспользуемые части
│   ├── login.html            # Страница входа
│   └── profile.html          # Профиль пользователя
│
├── static/                    # Статические файлы
│   ├── css/                  # Стили
│   ├── js/                   # JavaScript
│   ├── images/               # Изображения
│   └── media/                # Загружаемые файлы
│
├── alembic/                   # Миграции БД
│   ├── versions/             # Файлы миграций
│   └── env.py               # Настройка Alembic
│
├── main.py                    # Точка входа приложения
├── settings.py                # Конфигурация из .env
├── config.py                  # Настройки приложения
├── requirements.txt           # Python зависимости
├── alembic.ini               # Конфигурация Alembic
├── docker-compose.yml         # Docker конфигурация
├── Dockerfile                 # Docker образ
├── .env                       # Переменные окружения (не в git)
├── data.db                    # SQLite база (не в git)
├── README.md                  # Основная документация
├── CLAUDE.md                  # Гайд для AI ассистентов
└── CONTRIBUTING.md            # Этот файл
```

## 🏗 Архитектурные принципы

### 1. Разделение ответственности

Проект следует четкому разделению:

- **API модули** (`backend/api/*`) - возвращают JSON, используются для AJAX запросов
- **CRM модули** (`backend/crm/*`) - возвращают HTML шаблоны для отображения в браузере
- **Database модули** (`backend/database/*`) - инкапсулируют всю работу с БД
- **Core модули** (`backend/core/*`) - общие утилиты и middleware

### 2. CRUD паттерн

Каждая сущность имеет свой CRUD сервис:

```python
# Пример CRUD класса
class LeadCRUD:
    def get_by_id(self, db: Session, lead_id: int):
        """Получить лид по ID"""
        return db.query(Lead).filter(Lead.id == lead_id).first()

    def create(self, db: Session, lead_data: dict):
        """Создать новый лид"""
        lead = Lead(**lead_data)
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    def update(self, db: Session, lead_id: int, updates: dict):
        """Обновить лид"""
        lead = self.get_by_id(db, lead_id)
        for key, value in updates.items():
            setattr(lead, key, value)
        db.commit()
        return lead

    def delete(self, db: Session, lead_id: int):
        """Удалить лид"""
        lead = self.get_by_id(db, lead_id)
        db.delete(lead)
        db.commit()
```

### 3. Схемы Pydantic

Используем Pydantic для валидации входных/выходных данных:

```python
from pydantic import BaseModel, Field

class LeadCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r'^\+998\d{9}$')
    region: str
    contact_source: str

class LeadResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy 2.0
```

### 4. Dependency Injection

FastAPI зависимости для переиспользования логики:

```python
from backend.core.deps import get_current_user_from_cookie

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # current_user автоматически извлекается из токена
    # db - сессия базы данных
    return {"user_id": current_user.id}
```

## 🗄 Работа с базой данных

### Создание новой модели

**Шаг 1:** Добавьте модель в `backend/database/models.py`

```python
class MyNewModel(Base):
    __tablename__ = 'my_table'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='my_items')
```

**Шаг 2:** Добавьте обратную связь в связанную модель

```python
# В модель User
class User(Base):
    # ... существующие поля
    my_items = relationship('MyNewModel', back_populates='user')
```

**Шаг 3:** Создайте миграцию

```bash
alembic revision --autogenerate -m "Add MyNewModel table"
```

**Шаг 4:** Проверьте сгенерированную миграцию

```bash
# Откройте файл в alembic/versions/
# Убедитесь, что миграция корректна
```

**Шаг 5:** Примените миграцию

```bash
alembic upgrade head
```

### Создание CRUD сервиса

Создайте файл `backend/database/my_service/crud.py`:

```python
from sqlalchemy.orm import Session
from backend.database.models import MyNewModel

class MyModelCRUD:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(MyNewModel).offset(skip).limit(limit).all()

    def get_by_id(self, db: Session, item_id: int):
        return db.query(MyNewModel).filter(MyNewModel.id == item_id).first()

    def create(self, db: Session, name: str, user_id: int):
        item = MyNewModel(name=name, user_id=user_id)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, item_id: int, name: str):
        item = self.get_by_id(db, item_id)
        if item:
            item.name = name
            db.commit()
            db.refresh(item)
        return item

    def delete(self, db: Session, item_id: int):
        item = self.get_by_id(db, item_id)
        if item:
            db.delete(item)
            db.commit()
        return True
```

## ➕ Добавление новой функциональности

### Пример: Добавление модуля "Задачи" (Tasks)

#### 1. Создайте модель

```python
# backend/database/models.py
class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default='pending')
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    due_date = Column(DateTime)

    # Связи
    assigned_to = relationship('User', foreign_keys=[assigned_to_id])
    created_by = relationship('User', foreign_keys=[created_by_id])
```

#### 2. Создайте миграцию

```bash
alembic revision --autogenerate -m "Add tasks table"
alembic upgrade head
```

#### 3. Создайте схемы Pydantic

```python
# backend/api/tasks/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to_id: int
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    assigned_to_id: int
    created_by_id: int
    created_at: datetime
    due_date: Optional[datetime]

    class Config:
        from_attributes = True
```

#### 4. Создайте CRUD сервис

```python
# backend/database/tasks_service/crud.py
from sqlalchemy.orm import Session
from backend.database.models import Task

class TaskCRUD:
    def get_user_tasks(self, db: Session, user_id: int):
        return db.query(Task).filter(Task.assigned_to_id == user_id).all()

    def create_task(self, db: Session, task_data: dict, creator_id: int):
        task = Task(**task_data, created_by_id=creator_id)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def update_status(self, db: Session, task_id: int, status: str):
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status
            db.commit()
            db.refresh(task)
        return task
```

#### 5. Создайте API эндпоинты

```python
# backend/api/tasks/main.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.api.tasks.schemas import TaskCreate, TaskResponse
from backend.database.tasks_service.crud import TaskCRUD
from backend.core.deps import get_current_user_from_cookie
from backend.database import get_db
from backend.database.models import User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
task_crud = TaskCRUD()

@router.get("/", response_model=List[TaskResponse])
async def get_my_tasks(
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Получить задачи текущего пользователя"""
    return task_crud.get_user_tasks(db, current_user.id)

@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Создать новую задачу"""
    return task_crud.create_task(
        db,
        task.model_dump(),
        current_user.id
    )

@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Обновить статус задачи"""
    task = task_crud.update_status(db, task_id, status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

#### 6. Создайте CRM маршруты (HTML)

```python
# backend/crm/tasks/main.py
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.core.deps import get_current_user_from_cookie
from config import templates

router = APIRouter(prefix="/dashboard/tasks")

@router.get("/", response_class=HTMLResponse)
async def tasks_dashboard(
    request: Request,
    current_user = Depends(get_current_user_from_cookie)
):
    """Дашборд задач"""
    return templates.TemplateResponse(
        "/tasks/dashboard.html",
        {"request": request, "user": current_user}
    )
```

#### 7. Создайте HTML шаблон

```html
<!-- frontend/tasks/dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Задачи</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <h1>Мои задачи</h1>
    <div id="tasks-container"></div>

    <script>
        // Загрузка задач через API
        fetch('/api/tasks/')
            .then(res => res.json())
            .then(tasks => {
                const container = document.getElementById('tasks-container');
                tasks.forEach(task => {
                    const div = document.createElement('div');
                    div.className = 'task-item';
                    div.innerHTML = `
                        <h3>${task.title}</h3>
                        <p>${task.description || ''}</p>
                        <span>Статус: ${task.status}</span>
                    `;
                    container.appendChild(div);
                });
            });
    </script>
</body>
</html>
```

#### 8. Подключите роутеры в main.py

```python
# main.py
from backend.api.tasks.main import router as tasks_api_router
from backend.crm.tasks.main import router as tasks_crm_router

app.include_router(tasks_api_router)
app.include_router(tasks_crm_router)
```

## 📝 Стандарты кода

### Именование

- **Файлы**: `snake_case.py`
- **Классы**: `PascalCase`
- **Функции/методы**: `snake_case()`
- **Константы**: `UPPER_SNAKE_CASE`
- **Переменные**: `snake_case`

### Комментарии

```python
# Однострочный комментарий для простых объяснений

def complex_function(param1: str, param2: int) -> dict:
    """
    Многострочный docstring для функций.

    Args:
        param1: Описание первого параметра
        param2: Описание второго параметра

    Returns:
        dict: Описание возвращаемого значения

    Raises:
        ValueError: Когда параметр невалиден
    """
    pass
```

### Type Hints

Всегда используйте type hints:

```python
from typing import List, Optional, Dict

def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def find_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
```

### Обработка ошибок

```python
from fastapi import HTTPException

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with id {user_id} not found"
        )
    return user
```

## 🧪 Тестирование

### Структура тестов

```
tests/
├── __init__.py
├── conftest.py           # Фикстуры pytest
├── test_api/
│   ├── test_leads.py
│   ├── test_users.py
│   └── test_finance.py
└── test_crud/
    ├── test_lead_crud.py
    └── test_user_crud.py
```

### Пример теста

```python
# tests/test_api/test_leads.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_lead():
    response = client.post("/api/leads/", json={
        "full_name": "Тест Тестов",
        "phone": "+998901234567",
        "region": "Ташкент",
        "contact_source": "Instagram"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Тест Тестов"

def test_get_leads():
    response = client.get("/api/leads/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

## 🚀 Деплой

### Docker

```bash
# Сборка образа
docker build -t realestate-crm .

# Запуск через docker-compose
docker-compose up -d

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down
```

### Production чеклист

- [ ] Изменить `SECRET_KEY` на случайную строку
- [ ] Установить `DEBUG=False`
- [ ] Настроить PostgreSQL вместо SQLite
- [ ] Настроить Nginx как reverse proxy
- [ ] Включить HTTPS (SSL сертификаты)
- [ ] Настроить резервное копирование БД
- [ ] Настроить мониторинг и логирование
- [ ] Ограничить CORS только нужными доменами

## 🆘 Помощь и поддержка

### Частые проблемы

**Проблема:** `ModuleNotFoundError: No module named 'backend'`
**Решение:** Убедитесь, что вы в корневой директории и виртуальное окружение активировано

**Проблема:** `alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'`
**Решение:** Удалите `alembic/versions/*` и пересоздайте миграции

**Проблема:** `sqlite3.OperationalError: database is locked`
**Решение:** Закройте все соединения с БД, перезапустите приложение

### Ресурсы

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [SQLAlchemy документация](https://docs.sqlalchemy.org/)
- [Alembic документация](https://alembic.sqlalchemy.org/)
- [Pydantic документация](https://docs.pydantic.dev/)

## 🤝 Контрибьюция

1. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
2. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
3. Запушьте в branch (`git push origin feature/AmazingFeature`)
4. Откройте Pull Request

### Чеклист PR

- [ ] Код следует стандартам проекта
- [ ] Добавлены docstrings для новых функций
- [ ] Обновлена документация (если нужно)
- [ ] Созданы миграции БД (если нужно)
- [ ] Код протестирован локально
- [ ] Нет конфликтов с main веткой

---

**Удачи в разработке! 🚀**
