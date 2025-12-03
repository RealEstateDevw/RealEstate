# 🔧 Core — Ядро приложения

## Описание

Модуль `backend/core/` содержит ключевые компоненты приложения: аутентификацию, dependency injection, обработку ошибок, middleware, валидаторы и утилиты.

## Структура

```
backend/core/
├── auth.py               # Аутентификация (JWT, bcrypt)
├── deps.py               # Dependency Injection
├── exceptions.py         # Обработка ошибок
├── middleware.py         # HTTP Middleware
├── validators.py         # Валидаторы данных
├── logging_config.py     # Конфигурация логирования
├── rate_limiter.py       # Rate limiting
├── cache_utils.py        # Кэширование (Redis)
├── static.py             # Статические файлы
├── excel_importer.py     # Импорт из Excel
├── google_sheets.py      # Интеграция с Google Sheets
└── plan_cache.py         # Кэш планировок
```

## Ключевые модули

### 🔐 auth.py — Аутентификация

Обеспечивает безопасность приложения.

**Функции:**

```python
# Хеширование паролей
get_password_hash(password: str) -> str
verify_password(plain: str, hashed: str) -> bool

# JWT токены
create_access_token(data: dict, expires_delta: timedelta) -> str
```

**Использование:**

```python
from backend.core.auth import get_password_hash, create_access_token

# При регистрации
hashed = get_password_hash("user_password")
user = User(login="john", hashed_password=hashed)

# При логине
if verify_password(plain_password, user.hashed_password):
    token = create_access_token(data={"sub": user.login})
```

**Технологии:**
- **Authlib** — для JWT (НЕ python-jose!)
- **Passlib** — для bcrypt хеширования
- **HS256** — алгоритм подписи

**Конфигурация (.env):**
```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

### 🔗 deps.py — Dependency Injection

Предоставляет зависимости для FastAPI эндпоинтов.

**Функции:**

```python
# Для API эндпоинтов (Bearer token)
get_current_user(token: str) -> User

# Для HTML страниц (HTTP-only cookie)
get_current_user_from_cookie(access_token: str) -> User
```

**Использование:**

```python
from fastapi import Depends
from backend.core.deps import get_current_user_from_cookie

@app.get("/dashboard")
async def dashboard(user = Depends(get_current_user_from_cookie)):
    return {"user": user.login, "role": user.role.name}
```

**Процесс:**
1. Извлечение токена (из header или cookie)
2. Декодирование и валидация JWT
3. Проверка срока действия
4. Загрузка пользователя из БД
5. Возврат User объекта

---

### ⚠️ exceptions.py — Обработка ошибок

Централизованная обработка всех исключений.

**Кастомные исключения:**

```python
from backend.core.exceptions import NotFoundError, ValidationError

# В эндпоинте
user = db.query(User).get(user_id)
if not user:
    raise NotFoundError("Пользователь не найден")

# Автоматически конвертируется в:
# {"error": {"code": "NOT_FOUND", "message": "...", "status_code": 404}}
```

**Доступные исключения:**

Класс | HTTP код | Назначение
------|----------|------------
`DatabaseError` | 500 | Ошибки БД
`ValidationError` | 400 | Ошибки валидации
`AuthenticationError` | 401 | Ошибки аутентификации
`AuthorizationError` | 403 | Недостаточно прав
`NotFoundError` | 404 | Ресурс не найден
`ConflictError` | 409 | Конфликт данных (дубликат)
`RateLimitError` | 429 | Превышен лимит запросов
`ExternalServiceError` | 502 | Ошибка внешнего API

**Обработчики:**

Регистрируются в `main.py`:

```python
from backend.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
```

---

### 🛡️ middleware.py — HTTP Middleware

Middleware для обработки всех HTTP запросов.

**Доступные middleware:**

#### LoggingMiddleware
Логирует все запросы и ответы.

```python
# Логирует:
# - Метод и путь
# - Статус код
# - Время выполнения
# - IP адрес клиента
# - Ошибки (с traceback)
```

#### SecurityHeadersMiddleware
Добавляет заголовки безопасности.

```python
# Добавляет:
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - X-XSS-Protection: 1; mode=block
# - Referrer-Policy: strict-origin-when-cross-origin
```

#### RateLimitMiddleware
Защита от DDOS и abuse.

```python
# Лимиты:
# - 100 запросов в минуту (по умолчанию)
# - Отслеживание по IP адресу
# - 429 Too Many Requests при превышении
```

**Использование:**

```python
from backend.core.middleware import LoggingMiddleware, SecurityHeadersMiddleware

app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

---

### ✅ validators.py — Валидаторы

Валидация данных на уровне бизнес-логики.

**Функции:**

```python
# Email
validate_email("user@example.com") -> "user@example.com"

# Телефон (узбекский формат)
validate_phone("+998 90 123 45 67") -> "+998901234567"

# Пароль (сложность)
validate_password("SecurePass123") -> "SecurePass123"

# Обязательные поля
validate_required_fields(data, ["name", "email"]) -> data

# Длина строки
validate_string_length("Hello", min=3, max=10) -> "Hello"

# Положительное число
validate_positive_number(100, "Цена") -> 100.0

# Диапазон дат
validate_date_range("2025-01-01", "2025-12-31") -> (datetime, datetime)

# Санитизация
sanitize_input("<script>alert('xss')</script>") -> "alertxss"

# Пагинация
validate_pagination(page=1, size=20) -> (1, 20)
```

**Использование:**

```python
from backend.core.validators import validate_phone, validate_email

@app.post("/users/register")
def register(email: str, phone: str):
    # Автоматически валидирует и нормализует
    email = validate_email(email)  # lowercase, trimmed
    phone = validate_phone(phone)  # +998XXXXXXXXX
    
    # Если невалидно — выбросит ValidationError (400)
```

---

## Дополнительные утилиты

### logging_config.py

Конфигурация логирования.

```python
# Логи пишутся в:
# - logs/app_YYYYMMDD.log (все логи)
# - logs/errors_YYYYMMDD.log (только ошибки)
# - Консоль (в development)

# Формат:
# 2025-12-03 10:00:00 | INFO | endpoint | Message
```

### rate_limiter.py

Rate limiting для защиты от DDOS.

```python
# Настройка:
RATE_LIMIT = 100  # запросов
RATE_WINDOW = 60  # секунд (1 минута)

# При превышении:
# HTTP 429 Too Many Requests
```

### cache_utils.py

Кэширование в Redis.

```python
from backend.core.cache_utils import cache_get, cache_set

# Использование
value = cache_get("key")
if value is None:
    value = expensive_operation()
    cache_set("key", value, ttl=3600)  # 1 час
```

### excel_importer.py

Импорт данных из Excel файлов.

```python
from backend.core.excel_importer import import_leads_from_excel

# Импорт лидов из Excel
leads = import_leads_from_excel("leads.xlsx")
```

### google_sheets.py

Интеграция с Google Sheets API.

```python
from backend.core.google_sheets import export_to_sheets

# Экспорт данных в Google таблицы
export_to_sheets(data, spreadsheet_id="...")
```

---

## Безопасность

### Checklist

- ✅ Пароли хешируются через bcrypt
- ✅ JWT токены подписаны SECRET_KEY
- ✅ HTTP-only cookies для защиты от XSS
- ✅ Security headers (DENY, nosniff, и т.д.)
- ✅ Rate limiting для защиты от DDOS
- ✅ Валидация и санитизация ввода
- ✅ HTTPS в production (настраивается в nginx)

### Рекомендации

1. **SECRET_KEY** — обязательно измените в production!
2. **HTTPS** — используйте только HTTPS в production
3. **CORS** — настройте CORS для фронтенда
4. **Rate Limiting** — настройте под свою нагрузку
5. **Логирование** — регулярно проверяйте логи ошибок

---

## Конфигурация

### Переменные окружения (.env)

```env
# Безопасность
SECRET_KEY=your-very-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# База данных
DATABASE_URL=sqlite:///./crm_v3.db

# Redis (для кэша)
REDIS_URL=redis://localhost:6379/0

# Логирование
LOG_LEVEL=INFO
LOG_DIR=logs

# Rate Limiting
RATE_LIMIT=100
RATE_WINDOW=60
```

### Production настройки

```python
# В settings.py
DEBUG = False  # Выключить debug режим
ALLOWED_HOSTS = ["yourdomain.com"]
CORS_ORIGINS = ["https://yourdomain.com"]
```

---

## Разработка

### Добавление нового валидатора

1. Добавить функцию в `validators.py`:

```python
def validate_inn(inn: str) -> str:
    """Валидация ИНН"""
    if not inn.isdigit() or len(inn) != 9:
        raise ValidationError("Неверный формат ИНН")
    return inn
```

2. Использовать в эндпоинтах:

```python
from backend.core.validators import validate_inn

@app.post("/companies")
def create_company(inn: str):
    inn = validate_inn(inn)
    ...
```

### Добавление нового middleware

1. Создать класс в `middleware.py`:

```python
class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # До запроса
        print("Before request")
        
        response = await call_next(request)
        
        # После запроса
        print("After request")
        
        return response
```

2. Зарегистрировать в `main.py`:

```python
from backend.core.middleware import CustomMiddleware

app.add_middleware(CustomMiddleware)
```

---

## Тестирование

### Примеры тестов

```python
# tests/test_auth.py
from backend.core.auth import get_password_hash, verify_password

def test_password_hashing():
    password = "SecurePass123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False

# tests/test_validators.py
from backend.core.validators import validate_phone

def test_phone_validation():
    assert validate_phone("+998 90 123 45 67") == "+998901234567"
    
    with pytest.raises(ValidationError):
        validate_phone("1234567")
```

---

## FAQ

**Q: Почему Authlib, а не python-jose?**  
A: Authlib более современная, активно поддерживается и имеет лучшую производительность.

**Q: Можно ли изменить алгоритм JWT на RS256?**  
A: Да, измените `ALGORITHM` в `.env` и используйте RSA ключи вместо SECRET_KEY.

**Q: Как настроить разные лимиты для разных эндпоинтов?**  
A: Используйте декоратор с параметрами или создайте отдельные middleware.

---

**Автор:** RealEstate CRM Team  
**Дата:** 2025

