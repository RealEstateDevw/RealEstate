"""
Validators — Валидация данных на уровне бизнес-логики.

Этот модуль предоставляет функции для валидации данных,
которые не покрываются Pydantic схемами.

НАЗНАЧЕНИЕ:
-----------
- Валидация email адресов
- Валидация телефонных номеров (узбекский формат)
- Валидация паролей (сложность)
- Валидация обязательных полей
- Валидация длины строк
- Валидация положительных чисел
- Валидация диапазонов дат
- Санитизация пользовательского ввода
- Валидация параметров пагинации

ИСПОЛЬЗОВАНИЕ:
--------------
>>> from backend.core.validators import validate_phone, validate_email
>>> 
>>> phone = validate_phone("+998901234567")  # OK
>>> phone = validate_phone("123456")          # ValidationError
>>>
>>> email = validate_email("user@example.com")  # OK
>>> email = validate_email("invalid")           # ValidationError

ОСОБЕННОСТИ:
------------
- Все функции выбрасывают ValidationError при ошибке
- Функции возвращают очищенное/нормализованное значение
- Email приводится к lowercase
- Телефон очищается от лишних символов

Автор: RealEstate CRM Team
Дата создания: 2025
"""

from typing import Any, Dict, List, Optional
from fastapi import HTTPException
import re
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ИСКЛЮЧЕНИЯ
# =============================================================================

class ValidationError(HTTPException):
    """
    Кастомное исключение для ошибок валидации.
    
    Расширяет HTTPException для удобства использования в FastAPI.
    
    Args:
        detail: Описание ошибки
        field: Название поля с ошибкой (опционально)
        
    Пример:
        >>> raise ValidationError("Email уже используется", field="email")
    """
    def __init__(self, detail: str, field: str = None):
        super().__init__(status_code=400, detail=detail)
        self.field = field


# =============================================================================
# EMAIL
# =============================================================================

def validate_email(email: str) -> str:
    """
    Валидация email адреса.
    
    Проверяет:
    - Email не пустой
    - Соответствует стандартному формату (RFC 5322 simplified)
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        str: Нормализованный email (lowercase, trimmed)
        
    Raises:
        ValidationError: Если email невалиден
        
    Пример:
        >>> email = validate_email("User@Example.COM  ")
        >>> print(email)  # "user@example.com"
        
        >>> validate_email("invalid")  # ValidationError
    """
    if not email:
        raise ValidationError("Email не может быть пустым")
    
    # RFC 5322 упрощённый паттерн
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Неверный формат email адреса")
    
    # Приводим к lowercase и убираем пробелы
    return email.lower().strip()


# =============================================================================
# ТЕЛЕФОН
# =============================================================================

def validate_phone(phone: str) -> str:
    """
    Валидация номера телефона (узбекский формат).
    
    Формат: +998XXXXXXXXX (обязательно +998 и 9 цифр)
    
    Проверяет:
    - Номер не пустой
    - Соответствует узбекскому формату
    
    Автоматически очищает номер от лишних символов:
    - "+998 90 123 45 67" → "+998901234567"
    - "+998-(90)-123-45-67" → "+998901234567"
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        str: Очищенный номер в формате +998XXXXXXXXX
        
    Raises:
        ValidationError: Если номер невалиден
        
    Пример:
        >>> phone = validate_phone("+998 90 123 45 67")
        >>> print(phone)  # "+998901234567"
        
        >>> validate_phone("1234567")  # ValidationError
    """
    if not phone:
        raise ValidationError("Номер телефона не может быть пустым")
    
    # Убираем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем формат узбекского номера: +998 и 9 цифр
    if not re.match(r'^\+998\d{9}$', clean_phone):
        raise ValidationError("Неверный формат номера телефона. Используйте формат +998XXXXXXXXX")
    
    return clean_phone


# =============================================================================
# ПАРОЛЬ
# =============================================================================

def validate_password(password: str) -> str:
    """
    Валидация пароля (сложность).
    
    Требования:
    - Минимум 8 символов
    - Хотя бы одна буква (a-z, A-Z)
    - Хотя бы одна цифра (0-9)
    
    Args:
        password: Пароль для проверки
        
    Returns:
        str: Валидный пароль (без изменений)
        
    Raises:
        ValidationError: Если пароль не соответствует требованиям
        
    Пример:
        >>> validate_password("password123")  # OK
        >>> validate_password("12345678")     # ValidationError (нет букв)
        >>> validate_password("password")     # ValidationError (нет цифр)
        >>> validate_password("pass1")        # ValidationError (короткий)
        
    Security Note:
        Для повышения безопасности рекомендуется:
        - Увеличить минимальную длину до 12 символов
        - Требовать спецсимволы (!@#$%)
        - Проверять пароль против списка слабых паролей
    """
    if not password:
        raise ValidationError("Пароль не может быть пустым")
    
    if len(password) < 8:
        raise ValidationError("Пароль должен содержать минимум 8 символов")
    
    if not re.search(r'[A-Za-z]', password):
        raise ValidationError("Пароль должен содержать хотя бы одну букву")
    
    if not re.search(r'\d', password):
        raise ValidationError("Пароль должен содержать хотя бы одну цифру")
    
    return password


# =============================================================================
# ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
# =============================================================================

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Проверка наличия обязательных полей в словаре.
    
    Проверяет что все поля из required_fields присутствуют
    и не являются None или пустой строкой.
    
    Args:
        data: Словарь с данными
        required_fields: Список обязательных полей
        
    Returns:
        Dict: Тот же словарь data (для chaining)
        
    Raises:
        ValidationError: Если какие-то поля отсутствуют
        
    Пример:
        >>> data = {"name": "John", "email": "john@example.com"}
        >>> validate_required_fields(data, ["name", "email"])  # OK
        
        >>> data = {"name": "John"}
        >>> validate_required_fields(data, ["name", "email"])  # ValidationError
        
        >>> data = {"name": "John", "email": ""}
        >>> validate_required_fields(data, ["name", "email"])  # ValidationError
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Обязательные поля не заполнены: {', '.join(missing_fields)}")
    
    return data


# =============================================================================
# ДЛИНА СТРОКИ
# =============================================================================

def validate_string_length(value: str, min_length: int = 1, max_length: int = 255, field_name: str = "Поле") -> str:
    """
    Валидация длины строки.
    
    Args:
        value: Строка для проверки
        min_length: Минимальная длина (по умолчанию 1)
        max_length: Максимальная длина (по умолчанию 255)
        field_name: Название поля для сообщения об ошибке
        
    Returns:
        str: Очищенная строка (strip())
        
    Raises:
        ValidationError: Если длина не в допустимом диапазоне
        
    Пример:
        >>> validate_string_length("  Hello  ", 3, 10, "Name")  # "Hello"
        >>> validate_string_length("AB", 3, 10, "Name")         # ValidationError (короткое)
        >>> validate_string_length("Very long text...", 1, 10)  # ValidationError (длинное)
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} должно быть строкой")
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} должно содержать минимум {min_length} символов")
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} должно содержать максимум {max_length} символов")
    
    return value.strip()


# =============================================================================
# ПОЛОЖИТЕЛЬНОЕ ЧИСЛО
# =============================================================================

def validate_positive_number(value: Any, field_name: str = "Значение") -> float:
    """
    Валидация положительного числа.
    
    Args:
        value: Значение для проверки (может быть int, float, str)
        field_name: Название поля для сообщения об ошибке
        
    Returns:
        float: Валидное положительное число
        
    Raises:
        ValidationError: Если значение не число или не положительное
        
    Пример:
        >>> validate_positive_number(100, "Цена")      # 100.0
        >>> validate_positive_number("50.5", "Цена")   # 50.5
        >>> validate_positive_number(-10, "Цена")      # ValidationError
        >>> validate_positive_number("abc", "Цена")    # ValidationError
    """
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} должно быть числом")
    
    if num_value <= 0:
        raise ValidationError(f"{field_name} должно быть положительным числом")
    
    return num_value


# =============================================================================
# ДИАПАЗОН ДАТ
# =============================================================================

def validate_date_range(start_date: str, end_date: str) -> tuple:
    """
    Валидация диапазона дат.
    
    Проверяет что:
    - Обе даты в валидном ISO формате
    - Дата начала раньше даты окончания
    
    Args:
        start_date: Дата начала (ISO формат: "2025-01-01T00:00:00Z")
        end_date: Дата окончания (ISO формат)
        
    Returns:
        tuple: (datetime_start, datetime_end)
        
    Raises:
        ValidationError: Если формат невалиден или start >= end
        
    Пример:
        >>> start, end = validate_date_range(
        ...     "2025-01-01T00:00:00Z",
        ...     "2025-12-31T23:59:59Z"
        ... )
        
        >>> validate_date_range("2025-12-31", "2025-01-01")  # ValidationError (обратный порядок)
    """
    from datetime import datetime
    
    try:
        # Преобразуем ISO строку в datetime
        # replace('Z', '+00:00') для совместимости с Python < 3.11
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValidationError("Неверный формат даты. Используйте ISO формат")
    
    if start >= end:
        raise ValidationError("Дата начала должна быть раньше даты окончания")
    
    return start, end


# =============================================================================
# САНИТИЗАЦИЯ
# =============================================================================

def sanitize_input(value: str) -> str:
    """
    Очистка пользовательского ввода от потенциально опасных символов.
    
    Удаляет:
    - HTML теги (<script>, <div>, и т.д.)
    - Опасные символы (<, >, ", ')
    
    ВАЖНО: Это базовая защита, не заменяет полноценную защиту от XSS!
    Для HTML контента используйте специализированные библиотеки (bleach).
    
    Args:
        value: Строка для очистки
        
    Returns:
        str: Очищенная строка
        
    Пример:
        >>> sanitize_input("<script>alert('xss')</script>Hello")
        # "alertxssHello"
        
        >>> sanitize_input("User's <b>name</b>")
        # "Users name"
        
    Security Note:
        Для пользовательского HTML используйте:
        - bleach.clean() — для очистки HTML
        - MarkupSafe — для экранирования в templates
    """
    if not isinstance(value, str):
        return str(value)
    
    # Убираем HTML теги
    clean_value = re.sub(r'<[^>]+>', '', value)
    
    # Убираем потенциально опасные символы
    clean_value = re.sub(r'[<>"\']', '', clean_value)
    
    return clean_value.strip()


# =============================================================================
# ПАГИНАЦИЯ
# =============================================================================

def validate_pagination(page: int = 1, size: int = 10) -> tuple:
    """
    Валидация параметров пагинации.
    
    Проверяет:
    - page >= 1 (страницы начинаются с 1)
    - 1 <= size <= 100 (размер страницы в разумных пределах)
    
    Args:
        page: Номер страницы (начиная с 1)
        size: Размер страницы (количество элементов)
        
    Returns:
        tuple: (page, size) — валидные значения
        
    Raises:
        ValidationError: Если параметры вне допустимого диапазона
        
    Пример:
        >>> page, size = validate_pagination(1, 20)  # OK
        >>> page, size = validate_pagination(0, 20)  # ValidationError (page < 1)
        >>> page, size = validate_pagination(1, 200) # ValidationError (size > 100)
        
    Usage в эндпоинтах:
        >>> @app.get("/items")
        >>> def get_items(page: int = 1, size: int = 10):
        ...     page, size = validate_pagination(page, size)
        ...     offset = (page - 1) * size
        ...     items = db.query(Item).offset(offset).limit(size).all()
        ...     return items
    """
    if page < 1:
        raise ValidationError("Номер страницы должен быть больше 0")
    
    if size < 1 or size > 100:
        raise ValidationError("Размер страницы должен быть от 1 до 100")
    
    return page, size
