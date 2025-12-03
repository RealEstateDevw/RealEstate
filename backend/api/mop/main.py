"""
MOP API — REST API для менеджера отдела продаж.

НАЗНАЧЕНИЕ:
-----------
Этот модуль предоставляет функционал для МОП (Менеджер отдела продаж):
- Поиск по лидам и пользователям
- Мониторинг работы продажников
- Управление лидами команды

РОЛЬ МОП:
---------
Менеджер отдела продаж отвечает за:
- Распределение лидов между продажниками
- Мониторинг качества работы продажников
- Контроль закрытия сделок
- Обучение новых продажников

АРХИТЕКТУРА:
------------
Router → CRUD (sales_service) → Models → Database

ИСПОЛЬЗОВАНИЕ:
--------------
Все эндпоинты доступны по префиксу /api/mop/

Примеры:
    GET /api/mop/search?query=Иван — поиск лидов и пользователей

Автор: RealEstate CRM Team
Дата создания: 2025
"""

from typing import List, Union

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import get_db
from backend.api.leads.main import lead_crud
from backend.api.leads.schemas import LeadSearchResponse
from backend.api.mop.schemas import SearchResponse
from backend.api.users.schemas import UserSearchResponse

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(prefix="/api/mop")


# =============================================================================
# ПОИСК
# =============================================================================

@router.get("/search", response_model=SearchResponse)
async def search_leads_and_users(
        query: str = Query(..., min_length=1, description="Search query"),
        limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
        db: Session = Depends(get_db)
):
    """
    Комбинированный поиск по лидам и пользователям.
    
    МОП может искать:
    - Лиды по имени клиента, телефону, региону
    - Пользователей (продажников) по имени, email, телефону
    
    Процесс:
    1. Выполняется поиск в таблице Leads
    2. Выполняется поиск в таблице Users
    3. Результаты объединяются и возвращаются
    
    Args:
        query: Поисковый запрос (минимум 1 символ)
            Примеры:
            - "Иван" — найдёт клиентов и продажников по имени
            - "+998901234567" — найдёт по телефону
            - "gmail.com" — найдёт по email
            
        limit: Максимальное количество результатов (1-50, по умолчанию 10)
        
        db: Сессия БД (автоматически через Depends)
        
    Returns:
        SearchResponse: Объединённые результаты поиска
            - leads: List[LeadSearchResponse] — найденные лиды
            - users: List[UserSearchResponse] — найденные пользователи
            - total: int — общее количество результатов
            
    Raises:
        HTTPException (400): Если query пустой
        HTTPException (500): Если ошибка при поиске в БД
        
    Примеры запросов:
        >>> GET /api/mop/search?query=Иван&limit=20
        >>> # Найдёт всех клиентов и сотрудников с именем "Иван"
        
        >>> GET /api/mop/search?query=%2B998901234567
        >>> # Найдёт лиды и пользователей с телефоном +998901234567
        >>> # (URL-encoded: + → %2B)
        
    Пример ответа:
        >>> {
        ...   "leads": [
        ...     {
        ...       "id": 123,
        ...       "client_name": "Иван Петров",
        ...       "phone_number": "+998901234567",
        ...       "status": "в работе",
        ...       "assigned_to": {"id": 5, "name": "Продажник Иванов"}
        ...     }
        ...   ],
        ...   "users": [
        ...     {
        ...       "id": 5,
        ...       "first_name": "Иван",
        ...       "last_name": "Иванов",
        ...       "role": "Продажник",
        ...       "email": "ivanov@company.com"
        ...     }
        ...   ],
        ...   "total": 2
        ... }
        
    Использование:
        МОП может использовать этот эндпоинт для:
        - Быстрого поиска лида клиента
        - Проверки, кто работает с клиентом
        - Поиска контактов продажников
        
    Performance Note:
        Поиск выполняется с использованием LIKE,
        что может быть медленным на больших таблицах.
        Для production рекомендуется использовать full-text search.
    """
    try:
        # Вызов функции комбинированного поиска из lead_crud
        results = lead_crud.combined_search(db=db, query=query, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {str(e)}"
        )
