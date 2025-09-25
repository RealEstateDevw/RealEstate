import logging
import sys
from pathlib import Path
from datetime import datetime
from settings import settings

def setup_logging():
    """Настройка системы логирования"""
    
    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка уровня логирования
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Настройка root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler для общих логов
    file_handler = logging.FileHandler(
        log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # File handler для ошибок
    error_handler = logging.FileHandler(
        log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Настройка логгеров для внешних библиотек
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Логирование запуска
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

def get_logger(name: str) -> logging.Logger:
    """Получение логгера с заданным именем"""
    return logging.getLogger(name)

class RequestLogger:
    """Логгер для HTTP запросов"""
    
    def __init__(self):
        self.logger = logging.getLogger("request")
    
    def log_request(self, method: str, path: str, status_code: int, 
                   response_time: float, client_ip: str = None):
        """Логирование HTTP запроса"""
        self.logger.info(
            f"{method} {path} - {status_code} - {response_time:.3f}s - {client_ip or 'unknown'}"
        )
    
    def log_error(self, method: str, path: str, error: str, 
                  client_ip: str = None):
        """Логирование ошибки запроса"""
        self.logger.error(
            f"ERROR {method} {path} - {error} - {client_ip or 'unknown'}"
        )

# Создаем глобальный экземпляр
request_logger = RequestLogger()
