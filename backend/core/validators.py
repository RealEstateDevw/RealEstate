from typing import Any, Dict, List, Optional
from fastapi import HTTPException
import re
import logging

logger = logging.getLogger(__name__)

class ValidationError(HTTPException):
    """Кастомное исключение для ошибок валидации"""
    def __init__(self, detail: str, field: str = None):
        super().__init__(status_code=400, detail=detail)
        self.field = field

def validate_email(email: str) -> str:
    """Валидация email адреса"""
    if not email:
        raise ValidationError("Email не может быть пустым")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Неверный формат email адреса")
    
    return email.lower().strip()

def validate_phone(phone: str) -> str:
    """Валидация номера телефона"""
    if not phone:
        raise ValidationError("Номер телефона не может быть пустым")
    
    # Убираем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем формат узбекского номера
    if not re.match(r'^\+998\d{9}$', clean_phone):
        raise ValidationError("Неверный формат номера телефона. Используйте формат +998XXXXXXXXX")
    
    return clean_phone

def validate_password(password: str) -> str:
    """Валидация пароля"""
    if not password:
        raise ValidationError("Пароль не может быть пустым")
    
    if len(password) < 8:
        raise ValidationError("Пароль должен содержать минимум 8 символов")
    
    if not re.search(r'[A-Za-z]', password):
        raise ValidationError("Пароль должен содержать хотя бы одну букву")
    
    if not re.search(r'\d', password):
        raise ValidationError("Пароль должен содержать хотя бы одну цифру")
    
    return password

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """Проверка обязательных полей"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Обязательные поля не заполнены: {', '.join(missing_fields)}")
    
    return data

def validate_string_length(value: str, min_length: int = 1, max_length: int = 255, field_name: str = "Поле") -> str:
    """Валидация длины строки"""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} должно быть строкой")
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} должно содержать минимум {min_length} символов")
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} должно содержать максимум {max_length} символов")
    
    return value.strip()

def validate_positive_number(value: Any, field_name: str = "Значение") -> float:
    """Валидация положительного числа"""
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} должно быть числом")
    
    if num_value <= 0:
        raise ValidationError(f"{field_name} должно быть положительным числом")
    
    return num_value

def validate_date_range(start_date: str, end_date: str) -> tuple:
    """Валидация диапазона дат"""
    from datetime import datetime
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValidationError("Неверный формат даты. Используйте ISO формат")
    
    if start >= end:
        raise ValidationError("Дата начала должна быть раньше даты окончания")
    
    return start, end

def sanitize_input(value: str) -> str:
    """Очистка пользовательского ввода от потенциально опасных символов"""
    if not isinstance(value, str):
        return str(value)
    
    # Убираем HTML теги
    clean_value = re.sub(r'<[^>]+>', '', value)
    
    # Убираем потенциально опасные символы
    clean_value = re.sub(r'[<>"\']', '', clean_value)
    
    return clean_value.strip()

def validate_pagination(page: int = 1, size: int = 10) -> tuple:
    """Валидация параметров пагинации"""
    if page < 1:
        raise ValidationError("Номер страницы должен быть больше 0")
    
    if size < 1 or size > 100:
        raise ValidationError("Размер страницы должен быть от 1 до 100")
    
    return page, size
