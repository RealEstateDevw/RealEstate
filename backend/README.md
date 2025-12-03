# Backend Directory

Этот каталог содержит весь backend код приложения.

## 📂 Структура

```
backend/
├── api/              # REST API эндпоинты (возвращают JSON)
├── crm/              # CRM маршруты (возвращают HTML)
├── database/         # Модели БД и CRUD сервисы
├── core/             # Основные утилиты и middleware
├── bot/              # Telegram бот
└── __init__.py       # Инициализация (init_roles)
```

## 🎯 Принцип организации

### API vs CRM

**API модули** (`backend/api/*`):
- Возвращают JSON ответы
- Используются для AJAX запросов
- RESTful структура
- Пример: `GET /api/leads/` → `[{id: 1, name: "..."}, ...]`

**CRM модули** (`backend/crm/*`):
- Возвращают HTML страницы (через Jinja2)
- Используются для браузерного интерфейса
- Server-side rendering
- Пример: `GET /dashboard/sales/` → HTML страница

### Когда использовать что?

| Сценарий | Использовать |
|----------|-------------|
| AJAX запрос с фронтенда | API endpoint |
| Загрузка страницы в браузере | CRM route |
| Мобильное приложение | API endpoint |
| SPA React/Vue | API endpoint |
| Прямой переход по URL | CRM route |

## 📋 Добавление новой функциональности

### Шаг 1: Создайте модель (если нужна)

```python
# backend/database/models.py
class NewFeature(Base):
    __tablename__ = 'new_features'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

### Шаг 2: Создайте миграцию

```bash
alembic revision --autogenerate -m "Add new_features table"
alembic upgrade head
```

### Шаг 3: Создайте CRUD сервис

```python
# backend/database/feature_service/crud.py
class FeatureCRUD:
    def get_all(self, db: Session):
        return db.query(NewFeature).all()
```

### Шаг 4: Создайте API эндпоинты

```python
# backend/api/features/main.py
router = APIRouter(prefix="/api/features")

@router.get("/")
async def get_features(db: Session = Depends(get_db)):
    crud = FeatureCRUD()
    return crud.get_all(db)
```

### Шаг 5: Создайте CRM маршруты (если нужны HTML страницы)

```python
# backend/crm/features/main.py
router = APIRouter(prefix="/dashboard/features")

@router.get("/", response_class=HTMLResponse)
async def features_page(request: Request):
    return templates.TemplateResponse(
        "/features/index.html",
        {"request": request}
    )
```

### Шаг 6: Подключите роутеры в main.py

```python
# main.py
from backend.api.features.main import router as features_api
from backend.crm.features.main import router as features_crm

app.include_router(features_api)
app.include_router(features_crm)
```

## 🔑 Ключевые модули

### backend/core/

**auth.py** - JWT аутентификация
```python
from backend.core.auth import create_access_token, verify_password
```

**deps.py** - FastAPI зависимости
```python
from backend.core.deps import get_current_user_from_cookie
```

**middleware.py** - Middleware компоненты
- LoggingMiddleware
- SecurityHeadersMiddleware
- DatabaseConnectionMiddleware
- RateLimitMiddleware

### backend/database/

**models.py** - Все SQLAlchemy модели
- User, Role, Lead, Payment, etc.

**__init__.py** - Настройка БД
- engine, SessionLocal, Base
- get_db() dependency

## 🛡️ Безопасность

### Защита эндпоинтов

```python
from backend.core.deps import get_current_user_from_cookie

@router.get("/protected")
async def protected(current_user = Depends(get_current_user_from_cookie)):
    # Только аутентифицированные пользователи
    return {"user": current_user.login}
```

### Проверка ролей

```python
@router.get("/admin-only")
async def admin_only(current_user = Depends(get_current_user_from_cookie)):
    if current_user.role.name != "Админ":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "Welcome, admin!"}
```

## 📝 Соглашения о коде

1. **Именование роутеров:**
   - API: `router = APIRouter(prefix="/api/resource", tags=["resource"])`
   - CRM: `router = APIRouter(prefix="/dashboard/resource")`

2. **CRUD классы:**
   - Название: `{Model}CRUD`
   - Методы: `get_all()`, `get_by_id()`, `create()`, `update()`, `delete()`

3. **Schemas (Pydantic):**
   - Создание: `{Model}Create`
   - Обновление: `{Model}Update`
   - Чтение: `{Model}Response` или `{Model}InDB`

4. **Async/Await:**
   - Все route handlers должны быть `async def`
   - Database операции могут быть синхронными (SQLAlchemy)

## 🧪 Тестирование

```python
# tests/test_api/test_features.py
from fastapi.testclient import TestClient

def test_get_features():
    response = client.get("/api/features/")
    assert response.status_code == 200
```

## 📚 Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Смотрите CONTRIBUTING.md для детальных инструкций
