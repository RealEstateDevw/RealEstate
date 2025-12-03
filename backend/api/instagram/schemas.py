"""
Instagram Schemas — Pydantic модели для валидации данных Instagram API.

Этот модуль определяет схемы данных для:
1. Профиля Instagram (InstagramProfile)
2. Медиа контента (InstagramMediaItem, InstagramMediaResponse)
3. Настроек API (InstagramSettingsCreate, InstagramSettingsResponse)
4. Служебных ответов (AuthUrlResponse, DisconnectResponse, StatusResponse)

СТРУКТУРА МОДУЛЯ:
-----------------
┌─────────────────────────────────────────────────────────────────┐
│                        RESPONSE SCHEMAS                         │
├─────────────────────────────────────────────────────────────────┤
│  InstagramProfile        │ Данные профиля Instagram            │
│  InstagramStatusResponse │ Статус подключения + профиль        │
│  InstagramMediaItem      │ Один пост из Instagram              │
│  InstagramMediaResponse  │ Список постов                       │
│  AuthUrlResponse         │ URL для OAuth авторизации           │
│  DisconnectResponse      │ Результат отключения                │
├─────────────────────────────────────────────────────────────────┤
│                        SETTINGS SCHEMAS                         │
├─────────────────────────────────────────────────────────────────┤
│  InstagramSettingsCreate │ Входные данные для сохранения       │
│  InstagramSettingsResponse│ Данные настроек (с маской)         │
│  InstagramSettingsStatusResponse │ Статус настроек             │
└─────────────────────────────────────────────────────────────────┘

ИСПОЛЬЗОВАНИЕ:
--------------
>>> from backend.api.instagram.schemas import InstagramProfile
>>> profile = InstagramProfile(
...     id="17841400000000000",
...     username="company",
...     account_type="BUSINESS"
... )

Автор: RealEstate CRM Team
Дата создания: 2025
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


# =============================================================================
# СХЕМЫ ПРОФИЛЯ И СТАТУСА
# =============================================================================

class InstagramProfile(BaseModel):
    """
    Данные профиля Instagram пользователя.
    
    Используется для отображения информации о подключённом аккаунте
    в админ панели.
    
    Attributes:
        instagram_user_id: Уникальный ID пользователя Instagram (alias: "id")
        username: Имя пользователя (@username)
        account_type: Тип аккаунта (BUSINESS, MEDIA_CREATOR, PERSONAL)
        media_count: Количество публикаций
        token_expires_at: Дата истечения access token
        connected_at: Дата подключения аккаунта
        
    Пример JSON ответа:
        {
            "id": "17841400000000000",
            "username": "company_account",
            "account_type": "BUSINESS",
            "media_count": 42,
            "token_expires_at": "2025-03-01T12:00:00Z",
            "connected_at": "2025-01-15T10:30:00Z"
        }
    """
    instagram_user_id: str = Field(
        ...,
        alias="id",
        description="Instagram User ID (числовой идентификатор)"
    )
    username: str = Field(
        ...,
        description="Имя пользователя в Instagram (@username)"
    )
    account_type: Optional[str] = Field(
        None,
        description="Тип аккаунта: BUSINESS, MEDIA_CREATOR или PERSONAL"
    )
    media_count: Optional[int] = Field(
        None,
        description="Количество публикаций"
    )
    token_expires_at: Optional[datetime] = Field(
        None,
        description="Дата и время истечения access token"
    )
    connected_at: Optional[datetime] = Field(
        None,
        description="Дата и время подключения аккаунта"
    )

    class Config:
        populate_by_name = True  # Позволяет использовать как "id", так и "instagram_user_id"


class InstagramStatusResponse(BaseModel):
    """
    Ответ на запрос статуса подключения Instagram.
    
    Используется эндпоинтом GET /api/instagram/status для проверки,
    подключён ли Instagram аккаунт и работает ли интеграция.
    
    Attributes:
        connected: True если аккаунт подключён и токен валиден
        profile: Данные профиля (None если не подключён)
        
    Пример JSON ответа (подключён):
        {
            "connected": true,
            "profile": {
                "id": "17841400000000000",
                "username": "company_account",
                ...
            }
        }
        
    Пример JSON ответа (не подключён):
        {
            "connected": false,
            "profile": null
        }
    """
    connected: bool = Field(
        ...,
        description="True если Instagram подключён и работает"
    )
    profile: Optional[InstagramProfile] = Field(
        None,
        description="Данные профиля (если подключён)"
    )


# =============================================================================
# СХЕМЫ МЕДИА КОНТЕНТА
# =============================================================================

class InstagramMediaItem(BaseModel):
    """
    Один элемент медиа контента (пост) из Instagram.
    
    Представляет публикацию в Instagram с основными метаданными.
    
    Attributes:
        id: Уникальный ID публикации
        caption: Подпись к посту (может быть пустой)
        media_type: Тип контента (IMAGE, VIDEO, CAROUSEL_ALBUM)
        media_url: Прямой URL медиа файла (изображение или видео)
        permalink: Ссылка на пост в Instagram
        thumbnail_url: URL превью для видео (None для изображений)
        timestamp: Дата и время публикации
        
    Типы media_type:
        - IMAGE: Фотография
        - VIDEO: Видео (включая Reels)
        - CAROUSEL_ALBUM: Карусель из нескольких фото/видео
        
    Пример JSON:
        {
            "id": "17895695668004550",
            "caption": "Новый жилой комплекс! 🏠",
            "media_type": "IMAGE",
            "media_url": "https://...",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "thumbnail_url": null,
            "timestamp": "2025-01-15T10:30:00+00:00"
        }
    """
    id: str = Field(
        ...,
        description="Уникальный ID публикации в Instagram"
    )
    caption: Optional[str] = Field(
        None,
        description="Подпись к посту (текст)"
    )
    media_type: str = Field(
        ...,
        description="Тип: IMAGE, VIDEO или CAROUSEL_ALBUM"
    )
    media_url: HttpUrl = Field(
        ...,
        description="Прямой URL медиа файла"
    )
    permalink: HttpUrl = Field(
        ...,
        description="Ссылка на пост в Instagram"
    )
    thumbnail_url: Optional[HttpUrl] = Field(
        None,
        description="URL превью (для видео)"
    )
    timestamp: datetime = Field(
        ...,
        description="Дата и время публикации"
    )


class InstagramMediaResponse(BaseModel):
    """
    Ответ со списком медиа контента из Instagram.
    
    Используется эндпоинтом GET /api/instagram/media.
    
    Attributes:
        items: Список публикаций
        
    Пример JSON:
        {
            "items": [
                {"id": "123", "media_type": "IMAGE", ...},
                {"id": "456", "media_type": "VIDEO", ...}
            ]
        }
    """
    items: List[InstagramMediaItem] = Field(
        ...,
        description="Список публикаций"
    )


# =============================================================================
# СЛУЖЕБНЫЕ СХЕМЫ
# =============================================================================

class AuthUrlResponse(BaseModel):
    """
    Ответ с URL для OAuth авторизации.
    
    Используется эндпоинтом GET /api/instagram/auth-url.
    Фронтенд должен перенаправить пользователя на этот URL.
    
    Attributes:
        url: Полный URL для авторизации в Instagram
        
    Пример JSON:
        {
            "url": "https://api.instagram.com/oauth/authorize?client_id=..."
        }
    """
    url: HttpUrl = Field(
        ...,
        description="URL для перенаправления на Instagram OAuth"
    )


class DisconnectResponse(BaseModel):
    """
    Ответ на операцию отключения.
    
    Используется эндпоинтами:
    - DELETE /api/instagram/connection (отключение аккаунта)
    - DELETE /api/instagram/settings (удаление настроек)
    
    Attributes:
        success: True если операция выполнена успешно
        
    Пример JSON:
        {"success": true}
    """
    success: bool = Field(
        ...,
        description="True если операция выполнена успешно"
    )


# =============================================================================
# СХЕМЫ НАСТРОЕК INSTAGRAM API
# =============================================================================

class InstagramSettingsCreate(BaseModel):
    """
    Входные данные для создания/обновления настроек Instagram API.
    
    Используется эндпоинтом POST /api/instagram/settings.
    Админ заполняет эти данные из Meta for Developers.
    
    Attributes:
        app_id: Instagram App ID из настроек приложения Meta
        app_secret: Instagram App Secret (секретный ключ)
        redirect_uri: URL callback для OAuth (должен совпадать с настройками в Meta)
        
    Пример запроса:
        POST /api/instagram/settings
        {
            "app_id": "123456789012345",
            "app_secret": "abc123def456...",
            "redirect_uri": "https://example.com/api/instagram/callback"
        }
        
    Где получить данные:
        1. https://developers.facebook.com/
        2. Мои приложения → Выбрать приложение
        3. Настройки → Основное
    """
    app_id: str = Field(
        ...,
        min_length=1,
        description="Instagram App ID из Meta for Developers"
    )
    app_secret: str = Field(
        ...,
        min_length=1,
        description="Instagram App Secret (секретный ключ)"
    )
    redirect_uri: str = Field(
        ...,
        min_length=1,
        description="OAuth Redirect URI (callback URL)"
    )


class InstagramSettingsResponse(BaseModel):
    """
    Данные настроек Instagram API в ответе.
    
    Используется для отображения текущих настроек в админ панели.
    App Secret маскируется для безопасности.
    
    Attributes:
        id: ID записи в БД
        app_id: Instagram App ID
        app_secret_masked: Маскированный App Secret (видны только первые/последние 4 символа)
        redirect_uri: OAuth Redirect URI
        is_configured: Всегда True (если настройки существуют)
        created_at: Дата создания настроек
        updated_at: Дата последнего обновления
        
    Пример JSON:
        {
            "id": 1,
            "app_id": "123456789012345",
            "app_secret_masked": "abc1********************f456",
            "redirect_uri": "https://example.com/api/instagram/callback",
            "is_configured": true,
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-01-15T10:30:00Z"
        }
    """
    id: int = Field(
        ...,
        description="ID записи в базе данных"
    )
    app_id: str = Field(
        ...,
        description="Instagram App ID"
    )
    app_secret_masked: str = Field(
        ...,
        description="Маскированный App Secret (xxxx****xxxx)"
    )
    redirect_uri: str = Field(
        ...,
        description="OAuth Redirect URI"
    )
    is_configured: bool = Field(
        True,
        description="Флаг настроенности (всегда True)"
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Дата создания настроек"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Дата последнего обновления"
    )

    class Config:
        from_attributes = True  # Для сериализации из SQLAlchemy моделей


class InstagramSettingsStatusResponse(BaseModel):
    """
    Статус настроек Instagram API.
    
    Используется эндпоинтом GET /api/instagram/settings/status
    для проверки, настроен ли Instagram API.
    
    Attributes:
        is_configured: True если настройки существуют в БД
        settings: Данные настроек (None если не настроено)
        
    Пример JSON (настроено):
        {
            "is_configured": true,
            "settings": {
                "id": 1,
                "app_id": "123...",
                ...
            }
        }
        
    Пример JSON (не настроено):
        {
            "is_configured": false,
            "settings": null
        }
    """
    is_configured: bool = Field(
        ...,
        description="True если Instagram API настроен"
    )
    settings: Optional[InstagramSettingsResponse] = Field(
        None,
        description="Данные настроек (если настроено)"
    )
