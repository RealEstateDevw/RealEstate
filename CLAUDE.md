# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a comprehensive Real Estate CRM system built with FastAPI for managing residential complexes (ЖК), apartment layouts, leads, sales, and financial accounting. The system includes role-based access control, multiple specialized dashboards, Telegram bot integration, Instagram marketing integration, and public landing pages.

## Technology Stack

**Backend:**
- FastAPI - Modern async web framework
- SQLAlchemy 2.0 - ORM with declarative base
- Alembic - Database migrations
- Authlib JWT - Token-based authentication (not python-jose for JWT encoding!)
- SQLite - Database (with WAL mode enabled)
- Celery + Redis - Asynchronous task processing
- Aiogram 3.x - Telegram bot framework
- Google Sheets API - Data integration
- FastAPI Cache - In-memory caching

**Frontend:**
- Server-side rendered HTML with Jinja2 templates
- Vanilla JavaScript
- Templates located in `frontend/` directory

## Development Commands

### Running the Application

```bash
# Development mode with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# With Docker Compose
docker-compose up -d
```

### Database Migrations

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Celery Tasks

```bash
# Run Celery worker
celery -A celery_proccess worker --loglevel=info

# Run Celery beat scheduler
celery -A celery_proccess beat --loglevel=info
```

### Dependencies

```bash
# Install dependencies
pip install -r requirements.txt

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

## Architecture

### High-Level Structure

The application follows a layered architecture with clear separation between CRM (frontend routes), API (backend endpoints), and database services:

```
backend/
├── api/              # RESTful API endpoints
│   ├── leads/        # Lead management API
│   ├── finance/      # Finance operations API
│   ├── mop/          # MOP (operations) API
│   ├── rop/          # ROP (expenses) API
│   ├── complexes/    # Residential complex data API
│   ├── draws/        # Canvas drawing data API
│   ├── instagram/    # Instagram integration API
│   └── users/        # User management API
├── crm/              # Frontend HTML route handlers
│   ├── admin/        # Admin dashboard routes
│   ├── seller/       # Sales dashboard routes
│   ├── mop/          # MOP dashboard routes
│   ├── rop/          # ROP dashboard routes
│   ├── finance/      # Finance dashboard routes
│   ├── marketing/    # Marketing dashboard routes
│   └── shaxmatki/    # Public apartment grid views
├── database/         # Database models and CRUD services
│   ├── models.py     # SQLAlchemy model definitions
│   ├── sales_service/    # Lead/sales CRUD operations
│   ├── finance_service/  # Finance CRUD operations
│   ├── mop_service/      # MOP CRUD operations
│   ├── rop_service/      # ROP CRUD operations
│   └── marketing/        # Marketing CRUD operations
├── core/             # Core utilities and middleware
│   ├── auth.py       # JWT authentication (uses Authlib)
│   ├── deps.py       # FastAPI dependencies
│   ├── middleware.py # Custom middleware
│   ├── cache_utils.py # Cache warming for landing pages
│   └── exceptions.py # Error handlers
└── bot/              # Telegram bot implementation
    └── handlers/     # Bot command handlers
```

### Key Architectural Patterns

**1. Role-Based Access Control (RBAC)**

The system defines 5 roles stored in the `roles` table:
- **Админ** (Admin) - Full system access
- **Продажник** (Salesperson) - Lead and sales management
- **МОП** (MOP) - Operations management
- **РОП** (ROP) - Expense management
- **Финансист** (Financier) - Financial operations

Roles are initialized at startup via `init_roles()` in `backend/__init__.py`.

**2. Authentication Flow**

- JWT tokens are created using **Authlib** (not python-jose for encoding)
- Tokens are stored in HTTP-only cookies (`access_token`)
- Auth middleware in `main.py` (lines 270-364) validates tokens on protected routes
- Dependency `get_current_user_from_cookie()` extracts user from token
- Public routes are defined in middleware with `public_paths_exact` and `public_paths_startswith`

**3. Database Session Management**

- Database sessions use `SessionLocal` with `expire_on_commit=False`
- SQLite is configured with WAL mode for better concurrency
- Foreign keys are explicitly enabled via pragma
- Use `get_db()` dependency for endpoint database access

**4. Dual Route Structure**

Each feature area has two route modules:
- `backend/crm/{area}/main.py` - Returns HTML templates (dashboard views)
- `backend/api/{area}/main.py` - Returns JSON responses (API endpoints)

Example: Sales feature
- `/dashboard/sales/...` routes in `backend/crm/seller/main.py` serve HTML
- `/api/leads/...` routes in `backend/api/leads/main.py` serve JSON

**5. CRUD Service Pattern**

Database operations are encapsulated in CRUD classes:
- `LeadCRUD` in `backend/database/sales_service/crud.py`
- `FinanceCRUD` in `backend/database/finance_service/crud.py`
- CRUD services accept `Session` as first parameter
- Services handle all database queries and business logic

**6. Caching Strategy**

- FastAPI Cache with InMemoryBackend initialized at startup
- Complex/apartment data is pre-warmed for landing pages via `warmup_complex_caches()`
- Cache refresh runs every 15 minutes via `_periodic_cache_warmup()`
- Cached static files use long max-age headers

### Critical Integration Points

**Google Sheets Integration**
- Credentials path set via `GOOGLE_CREDENTIALS_PATH` env var
- Multiple spreadsheet IDs for different data types (see `settings.py`)
- Used for importing apartment data and lead information

**Instagram Integration**
- OAuth flow requires `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, and `INSTAGRAM_REDIRECT_URI`
- User-specific tokens stored in `InstagramIntegration` model
- Connection flow: Admin → `/dashboard/admin/marketing/instagram/connect`

**Telegram Bot**
- Bot token required in `BOT_TOKEN` env var
- Aiogram 3.x dispatcher and bot instance
- Webhook setup commented out in `main.py` (lines 123-177)

### Landing Pages & Public Routes

- Main selection page: `/` → `frontend/landing/index.html`
- Complex-specific pages: `/rassvet`, `/bahor`
- Public apartment grids: `/shaxmatki/...` routes
- These use pre-warmed cache for performance

### Models & Relationships

**Core Models (backend/database/models.py):**
- `User` - Has role_id FK to Role, relationships to attendances, leads, comments, expenses
- `Lead` - Central sales entity with status (LeadStatus), state (LeadState), assigned user
- `Payment` - Financial tracking with payment_type and payment_status enums
- `Expense` - ROP expenses with expense_category enum
- `Campaign` - Marketing campaigns with budget tracking
- `Contract` - Sales contracts linked to leads
- `InstagramIntegration` - OAuth tokens per user

**Key Relationships:**
- User → Leads (one-to-many)
- Lead → Payments (one-to-many)
- Lead → Comments (one-to-many)
- Lead → Callbacks (one-to-many)
- User → InstagramIntegration (one-to-many)

### Middleware Stack (Order Matters!)

Applied in `main.py` lines 74-77:
1. `LoggingMiddleware` - Request/response logging
2. `SecurityHeadersMiddleware` - Security headers
3. `DatabaseConnectionMiddleware` - DB connection pooling
4. `RateLimitMiddleware` - Rate limiting (100 req/60s default)
5. `CORSMiddleware` - CORS handling (line 114-120)
6. Auth middleware (lines 270-364) - JWT validation

### Working with the Database

**Creating New Models:**
1. Add model to `backend/database/models.py`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply: `alembic upgrade head`

**CRUD Service Pattern:**
```python
# Create a new CRUD service
class MyFeatureCRUD:
    def get_items(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(MyModel).offset(skip).limit(limit).all()

    def create_item(self, db: Session, item_data: dict):
        db_item = MyModel(**item_data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
```

**Using in Endpoints:**
```python
from backend.database import get_db
crud = MyFeatureCRUD()

@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    return crud.get_items(db)
```

### Authentication Helpers

**Protecting Routes:**
```python
from backend.core.deps import get_current_user_from_cookie

@router.get("/protected")
async def protected_route(
    current_user = Depends(get_current_user_from_cookie)
):
    # current_user is a User model instance
    if current_user.role.name != "Админ":
        raise HTTPException(status_code=403)
    return {"user": current_user.login}
```

**Role Redirects:**
Defined in `backend/api/users/schemas.py` as `ROLE_REDIRECTS` dict:
- Admin → `/dashboard/admin/`
- Salesperson → `/dashboard/sales/`
- MOP → `/dashboard/mop/`
- ROP → `/dashboard/rop/`
- Financier → `/dashboard/finance/`

### Template Rendering

Templates use Jinja2 from `frontend/` directory:
```python
from config import templates

@router.get("/page")
async def page(request: Request, current_user=Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "/area/page.html",
        {"request": request, "user": current_user}
    )
```

### Environment Configuration

All settings centralized in `settings.py` using `python-dotenv`:
- Database URL (default: `sqlite:///data.db`)
- JWT secret and algorithm
- Telegram bot token
- Instagram API credentials
- Google Sheets credentials
- Email SMTP settings
- Celery broker/backend URLs

Create `.env` file in project root with required values (see README.md for template).

### Common Patterns

**Lead Status Flow:**
- LeadStatus: Новый → В работе → Потерян / Бронь / Продан
- LeadState: warm / cold / hot / sold / lost
- Status changes tracked via status change endpoints

**Payment Recording:**
- PaymentType: initial / installment / final / hybrid
- PaymentStatus: pending / completed / cancelled
- Linked to lead_id for financial tracking

**Canvas/Drawing System:**
- Complex floor plans drawn on HTML canvas
- Apartment positions stored as JSON in database
- Drawing data endpoints in `/api/draws/`

### Error Handling

Custom exception handlers in `backend/core/exceptions.py`:
- `http_exception_handler` - HTTP exceptions
- `validation_exception_handler` - Pydantic validation errors
- `general_exception_handler` - Unhandled exceptions

All handlers registered in `main.py` lines 80-83.

### Logging

Structured logging configured in `backend/core/logging_config.py`:
- INFO level for production
- Logs to console and file
- Use `config.logger` for application logging
- Request/response logged via LoggingMiddleware

## Important Notes

- **JWT Library**: This project uses **Authlib** for JWT encoding/decoding, NOT python-jose. When working with token operations, always use `authlib.jose.jwt`.
- **SQLAlchemy Version**: Using SQLAlchemy 2.0 with `future=True` mode
- **Database**: SQLite with WAL mode - suitable for development, consider PostgreSQL for production
- **Aiogram Version**: Uses Aiogram 3.x (not 2.x) - check breaking changes when modifying bot
- **Celery Tasks**: Currently references `celery_proccess` module (note spelling)
- **Instagram Integration**: Requires Facebook App setup with Basic Display API
- **Static Files**: Mounted at `/static` (long cache) and `/media` (7-day cache)
- **API Docs**: Available at `/api/docs` (Swagger) and `/api/redoc`

## Testing & Development Tips

- Use `/api/docs` for interactive API testing
- Check `data.db` file for SQLite database (excluded from git)
- Logs directory auto-created for application logs
- Temp files stored in `static/media/temp_files/`
- Role initialization runs automatically at startup
- Landing page cache warms on startup (may delay first request)
