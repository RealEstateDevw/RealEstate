# Архитектура проекта RealEstate CRM

Этот документ описывает архитектурные решения, паттерны и принципы, используемые в проекте.

## 📐 Общая архитектура

### Архитектурный стиль: Layered Architecture

```
┌─────────────────────────────────────────┐
│         Presentation Layer               │  ◄── HTML Templates (Jinja2)
│     (frontend/, backend/crm/)            │      JavaScript, CSS
└─────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│         Application Layer                │  ◄── FastAPI Routers
│        (backend/api/, main.py)           │      Request/Response handling
└─────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│         Business Logic Layer             │  ◄── CRUD Services
│      (backend/database/*_service/)       │      Business Rules
└─────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│         Data Access Layer                │  ◄── SQLAlchemy Models
│       (backend/database/models.py)       │      Database Sessions
└─────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│           Database (SQLite)              │  ◄── Persistent Storage
└─────────────────────────────────────────┘
```

## 🔑 Ключевые архитектурные решения

### 1. Разделение API и CRM маршрутов

**Проблема:** Смешивание HTML и JSON ответов в одном модуле усложняет поддержку.

**Решение:** Четкое разделение на два типа маршрутов:

```
backend/api/      → Возвращают JSON (для AJAX, мобильных приложений)
backend/crm/      → Возвращают HTML (для браузерного интерфейса)
```

**Пример:**
- `/api/leads/` - возвращает JSON список лидов
- `/dashboard/sales/` - возвращает HTML страницу с таблицей лидов

**Преимущества:**
- Легко добавить мобильное приложение (использует только API)
- SPA фронтенд может использовать существующие API
- Разделение ответственности

### 2. CRUD Service Pattern

**Проблема:** Дублирование кода запросов к БД в разных эндпоинтах.

**Решение:** Инкапсуляция всех операций с БД в CRUD классы.

```python
# Плохо ❌
@router.get("/leads/{lead_id}")
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    return lead

# Хорошо ✅
class LeadCRUD:
    def get_by_id(self, db: Session, lead_id: int):
        return db.query(Lead).filter(Lead.id == lead_id).first()

lead_crud = LeadCRUD()

@router.get("/leads/{lead_id}")
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    return lead_crud.get_by_id(db, lead_id)
```

**Преимущества:**
- Переиспользование кода
- Легче тестировать
- Единая точка изменений для запросов

### 3. Role-Based Access Control (RBAC)

**Архитектура ролей:**

```
┌─────────────────────────────────────────────────┐
│                   User                          │
│  ┌───────────────────────────────────────────┐  │
│  │  id, login, hashed_password, role_id      │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ FK
                       ▼
┌─────────────────────────────────────────────────┐
│                   Role                          │
│  ┌───────────────────────────────────────────┐  │
│  │  id, name (Админ, Продажник, МОП...)     │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Роли и их права:**

| Роль | Доступ | Основные функции |
|------|--------|------------------|
| Админ | Все модули | Управление пользователями, настройки, все операции |
| Продажник | CRM, Leads | Работа с лидами, просмотр квартир, создание сделок |
| МОП | MOP модуль | Операционное управление, отчеты |
| РОП | ROP модуль | Управление расходами, бюджетирование |
| Финансист | Finance модуль | Платежи, финансовые отчеты |

**Проверка прав:**

```python
# В эндпоинте
@router.get("/admin-only")
async def admin_route(current_user = Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"message": "Admin access granted"}
```

### 4. JWT Authentication Flow

```
┌──────────┐                                    ┌──────────┐
│  Client  │                                    │  Server  │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /login (username, password)          │
     │───────────────────────────────────────────────►
     │                                                │
     │                          2. Verify credentials │
     │                          3. Generate JWT token │
     │                          4. Set HTTP-only cookie
     │  ◄───────────────────────────────────────────┤
     │  Response: 303 Redirect + Cookie               │
     │                                                │
     │  5. GET /dashboard/* (Cookie: access_token)   │
     │───────────────────────────────────────────────►
     │                                                │
     │                          6. Validate JWT token │
     │                          7. Extract user info  │
     │  ◄───────────────────────────────────────────┤
     │  Response: HTML/JSON with user data            │
     │                                                │
```

**Компоненты:**

1. **Token Creation** (`backend/core/auth.py`):
   - Используется **Authlib** (не python-jose!)
   - Payload: `{sub: login, role_id: role_id, exp: timestamp}`
   - Срок жизни: настраивается через `ACCESS_TOKEN_EXPIRE_MINUTES`

2. **Token Storage**:
   - HTTP-only cookie (защита от XSS)
   - Имя: `access_token`
   - Формат: `Bearer {token}`

3. **Token Validation** (`main.py` auth middleware):
   - Извлечение токена из cookie
   - Декодирование через `authlib.jose.jwt.decode()`
   - Проверка срока действия (`exp`)
   - Сохранение в `request.state.user`

4. **User Extraction** (`backend/core/deps.py`):
   - Dependency `get_current_user_from_cookie()`
   - Извлекает login из токена
   - Запрашивает полный объект User из БД
   - Возвращает User instance

### 5. Database Architecture

**SQLAlchemy 2.0 + SQLite с оптимизациями:**

```python
# backend/database/__init__.py

# WAL режим для лучшей производительности
cursor.execute("PRAGMA journal_mode=WAL")

# Включение foreign keys (по умолчанию выключены в SQLite)
cursor.execute("PRAGMA foreign_keys=ON")

# Баланс между производительностью и надежностью
cursor.execute("PRAGMA synchronous=NORMAL")
```

**Модели с отношениями:**

```
User ──┐
       │ 1:N
       ├─► Lead ──┬─► Payment (1:N)
       │          ├─► Comment (1:N)
       │          ├─► Contract (1:1)
       │          └─► Callback (1:N)
       │
       ├─► Expense (1:N)
       ├─► Attendance (1:N)
       └─► InstagramIntegration (1:N)

Role ──► User (1:N)
```

**Ленивая загрузка (Lazy Loading):**

```python
# По умолчанию - lazy='select'
user.leads  # Дополнительный запрос к БД

# Eager loading для часто используемых связей
role = relationship('Role', lazy="subquery")  # Загружается сразу
attendances = relationship("Attendance", lazy='joined')  # JOIN в запросе
```

### 6. Caching Strategy

**Многоуровневое кэширование:**

1. **In-Memory Cache** (FastAPI Cache):
```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

# Инициализация при старте
FastAPICache.init(InMemoryBackend())

# Использование декоратора
@cache(expire=3600)
async def get_complex_data(complex_id: int):
    # Тяжелые вычисления
    return data
```

2. **Static Files Cache** (HTTP headers):
```python
# Static CSS/JS - долгий кеш
app.mount("/static", CachedStaticFiles(
    directory="static",
    cache_control="public, max-age=31536000, immutable"
))

# Media files - средний кеш
app.mount("/media", CachedStaticFiles(
    directory="media",
    cache_control="public, max-age=604800"
))
```

3. **Warm Cache** (предварительная загрузка):
```python
# backend/core/cache_utils.py
async def warmup_complex_caches():
    """Предзагрузка данных ЖК для лендингов"""
    # Кэшируется при старте и каждые 15 минут
    complexes = await fetch_all_complexes()
    for complex in complexes:
        await cache_complex_apartments(complex.id)
```

### 7. Middleware Pipeline

**Порядок выполнения middleware имеет значение!**

```
Request
   ▼
┌─────────────────────────┐
│  LoggingMiddleware      │  ◄── Логирует запрос/ответ
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  SecurityHeaders        │  ◄── Добавляет заголовки безопасности
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  DatabaseConnection     │  ◄── Управляет пулом соединений
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  RateLimitMiddleware    │  ◄── 100 req/60s по умолчанию
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  CORSMiddleware         │  ◄── CORS проверка
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  Auth Middleware        │  ◄── JWT валидация (custom)
└─────────┬───────────────┘
          ▼
     Route Handler
          ▼
       Response
```

**Каждый middleware может:**
- Модифицировать request
- Вызвать следующий middleware
- Модифицировать response
- Прервать цепочку (вернуть ошибку)

## 🎯 Design Patterns

### 1. Dependency Injection

FastAPI использует DI для переиспользования логики:

```python
# Dependency
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    # ... валидация токена
    return user

# Использование в нескольких эндпоинтах
@router.get("/profile")
async def profile(user = Depends(get_current_user_from_cookie)):
    return user

@router.get("/settings")
async def settings(user = Depends(get_current_user_from_cookie)):
    return {"user": user.login}
```

### 2. Repository Pattern (через CRUD)

Абстракция доступа к данным:

```python
# Интерфейс (неявный в Python)
class BaseRepository:
    def get_all(self, db: Session): ...
    def get_by_id(self, db: Session, id: int): ...
    def create(self, db: Session, data: dict): ...
    def update(self, db: Session, id: int, data: dict): ...
    def delete(self, db: Session, id: int): ...

# Реализация
class LeadRepository(BaseRepository):
    def get_all(self, db: Session):
        return db.query(Lead).all()
    # ... остальные методы
```

### 3. Service Layer

Бизнес-логика отделена от эндпоинтов:

```python
# Service класс
class LeadStatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_conversion_rate(self):
        total = self.db.query(Lead).count()
        sold = self.db.query(Lead).filter(Lead.status == "Продан").count()
        return (sold / total * 100) if total > 0 else 0

# Использование в эндпоинте
@router.get("/statistics")
async def get_stats(db: Session = Depends(get_db)):
    service = LeadStatisticsService(db)
    return {"conversion_rate": service.calculate_conversion_rate()}
```

### 4. Factory Pattern (для создания объектов)

```python
# backend/bot/main.py
def create_bot() -> Bot:
    """Фабрика для создания бота с настройками"""
    session = AiohttpSession()
    return Bot(token=settings.BOT_TOKEN, session=session, parse_mode="HTML")
```

## 🔄 Data Flow

### Типичный запрос на создание лида:

```
1. Client: POST /api/leads/
   Body: {full_name, phone, region, ...}

2. FastAPI Router (backend/api/leads/main.py)
   └─► Pydantic валидация (LeadCreate schema)

3. LeadCRUD.create()
   └─► SQLAlchemy ORM
       └─► SQL INSERT в БД

4. Response: LeadResponse (Pydantic)
   └─► JSON serialization
       └─► HTTP 201 Created
```

### Server-Side Rendering (SSR) запрос:

```
1. Client: GET /dashboard/sales/
   Cookie: access_token=Bearer_xyz

2. Auth Middleware
   └─► JWT validation
       └─► Extract user → request.state.user

3. CRM Router (backend/crm/seller/main.py)
   └─► Dependency: get_current_user_from_cookie()
       └─► User object

4. Template Rendering (Jinja2)
   └─► frontend/seller/sales-dashboard.html
       └─► {{ user.first_name }}

5. Response: HTML
   └─► HTTP 200 OK
```

## 🌐 Integration Points

### 1. Instagram Integration

**OAuth 2.0 Flow:**

```
1. User: Click "Подключить Instagram"
   └─► GET /dashboard/admin/marketing/instagram/connect

2. Redirect to Instagram:
   https://api.instagram.com/oauth/authorize
   ?client_id={INSTAGRAM_APP_ID}
   &redirect_uri={INSTAGRAM_REDIRECT_URI}
   &scope=user_profile,user_media
   &response_type=code

3. User authorizes → Instagram redirects:
   GET /api/instagram/callback?code=AUTH_CODE

4. Exchange code for token:
   POST https://api.instagram.com/oauth/access_token
   └─► Receive: access_token, user_id

5. Store in DB:
   InstagramIntegration(
       user_id=current_user.id,
       access_token=token,
       instagram_user_id=ig_user_id
   )
```

### 2. Google Sheets Integration

**Импорт данных из таблиц:**

```python
# backend/core/google_sheets.py
from google.oauth2.service_account import Credentials
import gspread

# Аутентификация
creds = Credentials.from_service_account_file(
    settings.GOOGLE_CREDENTIALS_PATH
)
client = gspread.authorize(creds)

# Чтение данных
sheet = client.open_by_key(settings.SPREADSHEET_ID_SHAXMATKA_ID)
worksheet = sheet.worksheet("Sheet1")
data = worksheet.get_all_records()

# Импорт в БД
for row in data:
    apartment = Apartment(**row)
    db.add(apartment)
db.commit()
```

### 3. Telegram Bot

**Webhook vs Polling:**

```python
# Текущая реализация: Polling (закомментирован webhook)

# Polling:
async def run_bot():
    dp = Dispatcher()
    dp.include_router(draw_router)
    await dp.start_polling(bot)

# Webhook (закомментирован в main.py):
# POST /webhook/{bot_token}
# Body: Telegram Update object
```

### 4. Celery для асинхронных задач

**Архитектура:**

```
FastAPI ──► Redis (Broker) ──► Celery Worker
                                     │
                                     ├─► Send email
                                     ├─► Generate report
                                     └─► Sync with Google Sheets
                                           │
                                           └─► Redis (Result Backend)
```

**Пример задачи:**

```python
# celery_proccess.py
from celery import Celery

app = Celery('tasks', broker=settings.CELERY_BROKER_URL)

@app.task
def send_notification_email(user_email: str, message: str):
    # Отправка email
    send_email(user_email, message)
    return f"Email sent to {user_email}"

# Вызов из FastAPI
from celery_proccess import send_notification_email
send_notification_email.delay("user@example.com", "Hello!")
```

## 🔒 Security Architecture

### 1. Authentication Security

- **JWT tokens** хранятся в HTTP-only cookies (защита от XSS)
- **Пароли** хешируются с bcrypt (backend/core/auth.py)
- **Secret key** загружается из .env (не хардкодится)
- **Token expiration** настраивается (по умолчанию 60 минут)

### 2. Authorization Security

- **Role-based access** на уровне эндпоинтов
- **Проверка владельца** для операций с данными:

```python
@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    current_user = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    # Проверка: только владелец или админ может удалить
    if lead.user_id != current_user.id and current_user.role.name != "Админ":
        raise HTTPException(status_code=403)

    db.delete(lead)
    db.commit()
```

### 3. Input Validation

- **Pydantic schemas** валидируют входные данные
- **Type hints** обеспечивают type safety
- **SQL injection защита** через SQLAlchemy ORM

### 4. Rate Limiting

```python
# RateLimitMiddleware
# По умолчанию: 100 запросов / 60 секунд
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
```

## 📊 Scaling Considerations

### Текущие ограничения (SQLite):

- ❌ Один писатель за раз (WAL режим помогает, но не решает полностью)
- ❌ Не подходит для высоконагруженных систем
- ❌ Сложности с горизонтальным масштабированием

### Рекомендации для роста:

1. **Миграция на PostgreSQL:**
```python
# settings.py
DATABASE_URL = "postgresql://user:password@localhost/realestate"
```

2. **Read Replicas** для чтения:
```python
# Мастер для записи
write_engine = create_engine(WRITE_DB_URL)

# Реплики для чтения
read_engine = create_engine(READ_DB_URL)
```

3. **Redis для кэша** вместо InMemory:
```python
from fastapi_cache.backends.redis import RedisBackend
FastAPICache.init(RedisBackend(redis_url="redis://localhost"))
```

4. **Горизонтальное масштабирование**:
- Load balancer (Nginx)
- Несколько инстансов FastAPI
- Shared PostgreSQL
- Shared Redis

## 🎓 Architectural Best Practices

1. **Single Responsibility**: Каждый модуль делает одну вещь хорошо
2. **Dependency Inversion**: Зависимость от абстракций (interfaces), не от конкретных реализаций
3. **DRY (Don't Repeat Yourself)**: CRUD сервисы избегают дублирования кода
4. **KISS (Keep It Simple)**: Простые решения где это возможно
5. **Separation of Concerns**: API ≠ CRM ≠ Database ≠ Business Logic

---

Этот документ живой и должен обновляться при изменении архитектуры проекта.
