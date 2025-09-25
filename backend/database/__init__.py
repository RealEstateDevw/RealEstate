from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from settings import settings
import logging

logger = logging.getLogger(__name__)

# Создаем движок базы данных с улучшенными настройками
engine_kwargs = {
    "echo": settings.DEBUG,  # Логирование SQL запросов в debug режиме
    "future": True,  # Использование нового API SQLAlchemy 2.0
}

# Для SQLite добавляем специальные настройки
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "poolclass": StaticPool,
        "connect_args": {
            "check_same_thread": False,  # Разрешаем использование в разных потоках
            "timeout": 30,  # Таймаут для блокировок
        },
        "pool_pre_ping": True,  # Проверка соединения перед использованием
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# Настройка для SQLite - включение foreign keys
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # WAL режим для лучшей производительности
        cursor.execute("PRAGMA synchronous=NORMAL")  # Баланс между производительностью и надежностью
        cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()

def get_db():
    """Dependency для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

