"""
Instagram Service — Сервис для работы с Instagram Basic Display API.

Этот модуль предоставляет низкоуровневый интерфейс для взаимодействия
с Instagram API от Meta (Facebook).

ИСПОЛЬЗУЕМЫЕ API:
-----------------
1. Instagram Basic Display API — для получения профиля и медиа
   Документация: https://developers.facebook.com/docs/instagram-basic-display-api

2. OAuth 2.0 — для авторизации пользователей
   Документация: https://developers.facebook.com/docs/instagram-basic-display-api/overview#authorization-window

ПОТОК АВТОРИЗАЦИИ (OAuth 2.0):
------------------------------
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Админ   │────▶│  Auth URL    │────▶│  Instagram   │
│          │     │  (authorize) │     │  Login Page  │
└──────────┘     └──────────────┘     └──────────────┘
                                             │
                                             ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  БД      │◀────│  Callback    │◀────│  Code        │
│ (token)  │     │  (exchange)  │     │  redirect    │
└──────────┘     └──────────────┘     └──────────────┘

ТИПЫ ТОКЕНОВ:
-------------
1. Short-lived token — действует 1 час
   - Получается при обмене authorization code
   
2. Long-lived token — действует ~60 дней
   - Получается при обмене short-lived токена
   - Можно обновить за 24 часа до истечения

КЛАССЫ:
-------
- InstagramServiceError: Исключение для ошибок API
- TokenPayload: Dataclass с данными токена
- InstagramService: Основной сервис для работы с API

ИСПОЛЬЗОВАНИЕ:
--------------
>>> service = InstagramService(app_id, app_secret, redirect_uri)
>>> auth_url = service.build_auth_url(state)
>>> # После redirect с code:
>>> token = service.exchange_code_for_token(code)
>>> profile = service.fetch_profile(token.access_token)
>>> media = service.fetch_media(token.access_token, limit=12)

Автор: RealEstate CRM Team
Дата создания: 2025
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from requests import Response

logger = logging.getLogger(__name__)


# =============================================================================
# ИСКЛЮЧЕНИЯ И ТИПЫ ДАННЫХ
# =============================================================================

class InstagramServiceError(Exception):
    """
    Исключение для ошибок интеграции с Instagram.
    
    Выбрасывается при:
    - Отсутствии или некорректности настроек (App ID, Secret)
    - Ошибках API Instagram (network errors, rate limits, invalid tokens)
    - Некорректных ответах от API
    
    Пример:
        >>> try:
        ...     service.fetch_profile(invalid_token)
        ... except InstagramServiceError as e:
        ...     logger.error(f"Instagram error: {e}")
    """
    pass


@dataclass
class TokenPayload:
    """
    Данные токена доступа Instagram.
    
    Attributes:
        access_token: Токен для доступа к API
        user_id: Instagram User ID (может быть пустым при refresh)
        expires_in: Время жизни токена в секундах
        
    Пример:
        >>> token = TokenPayload(
        ...     access_token="IGQVJ...",
        ...     user_id="17841400000000000",
        ...     expires_in=5183944  # ~60 дней
        ... )
    """
    access_token: str
    user_id: str
    expires_in: int


# =============================================================================
# ОСНОВНОЙ СЕРВИС
# =============================================================================

class InstagramService:
    """
    Сервис для работы с Instagram Basic Display API.
    
    Предоставляет методы для:
    - OAuth авторизации (построение URL, обмен кодов)
    - Получения профиля пользователя
    - Получения медиа контента (постов)
    - Обновления токенов
    
    Attributes:
        AUTH_URL: URL для OAuth авторизации
        TOKEN_URL: URL для обмена кода на токен
        GRAPH_URL: Базовый URL Instagram Graph API
        SCOPE: Запрашиваемые разрешения (user_profile, user_media)
        
    Пример использования:
        >>> service = InstagramService(
        ...     app_id="123456789",
        ...     app_secret="abc123...",
        ...     redirect_uri="https://example.com/api/instagram/callback"
        ... )
        >>> url = service.build_auth_url(state="jwt_token")
    """
    
    # Базовые URL Instagram API
    AUTH_URL = "https://api.instagram.com/oauth/authorize"
    """URL для начала OAuth авторизации."""
    
    TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    """URL для обмена authorization code на access token."""
    
    GRAPH_URL = "https://graph.instagram.com"
    """Базовый URL для Instagram Graph API (профиль, медиа)."""
    
    SCOPE = "user_profile,user_media"
    """
    Запрашиваемые разрешения OAuth:
    - user_profile: доступ к id, username, account_type
    - user_media: доступ к постам пользователя
    """

    def __init__(self, app_id: str, app_secret: str, redirect_uri: str) -> None:
        """
        Инициализация сервиса Instagram.
        
        Args:
            app_id: Instagram App ID из Meta for Developers
            app_secret: Instagram App Secret из Meta for Developers
            redirect_uri: URL для OAuth callback (должен совпадать с настройками в Meta)
            
        Raises:
            InstagramServiceError: Если какой-либо параметр пустой
            
        Пример:
            >>> service = InstagramService(
            ...     app_id="123456789012345",
            ...     app_secret="abc123def456...",
            ...     redirect_uri="https://example.com/api/instagram/callback"
            ... )
        """
        if not app_id or not app_secret or not redirect_uri:
            raise InstagramServiceError("Instagram credentials are not configured.")
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri

    def build_auth_url(self, state: str) -> str:
        """
        Построить URL для OAuth авторизации Instagram.
        
        Генерирует URL вида:
        https://api.instagram.com/oauth/authorize?
            client_id={app_id}&
            redirect_uri={redirect_uri}&
            scope=user_profile,user_media&
            response_type=code&
            state={state}
        
        Args:
            state: CSRF токен (рекомендуется JWT с user_id и exp)
            
        Returns:
            str: Полный URL для перенаправления пользователя
            
        Пример:
            >>> url = service.build_auth_url(state="eyJ...")
            >>> # Перенаправить пользователя на url
        """
        return (
            f"{self.AUTH_URL}"
            f"?client_id={quote(self.app_id)}"
            f"&redirect_uri={quote(self.redirect_uri)}"
            f"&scope={self.SCOPE}"
            f"&response_type=code"
            f"&state={quote(state)}"
        )

    def exchange_code_for_token(self, code: str) -> TokenPayload:
        """
        Обменять authorization code на access token.
        
        Двухэтапный процесс:
        1. Обмен code на short-lived token (1 час)
        2. Обмен short-lived на long-lived token (~60 дней)
        
        Args:
            code: Authorization code из callback URL
            
        Returns:
            TokenPayload: Данные long-lived токена
            
        Raises:
            InstagramServiceError: При ошибке обмена токенов
            
        Пример:
            >>> # После редиректа с Instagram:
            >>> # https://example.com/callback?code=AQC...
            >>> token = service.exchange_code_for_token(code="AQC...")
            >>> print(token.access_token)  # IGQVJ...
            >>> print(token.expires_in)    # 5183944 (~60 дней)
        """
        # Шаг 1: Получаем short-lived token (1 час)
        short_lived = self._post(
            self.TOKEN_URL,
            data={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
        )
        short_token = short_lived.get("access_token")
        user_id = short_lived.get("user_id")
        if not short_token or not user_id:
            logger.error("Invalid response from Instagram token exchange: %s", short_lived)
            raise InstagramServiceError("Не удалось получить токен Instagram.")

        # Шаг 2: Обмениваем на long-lived token (~60 дней)
        long_lived = self._get(
            f"{self.GRAPH_URL}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": self.app_secret,
                "access_token": short_token,
            },
        )
        access_token = long_lived.get("access_token")
        expires_in = long_lived.get("expires_in", 60 * 60 * 24 * 60)  # default ~60 дней
        if not access_token:
            logger.error("Invalid response from Instagram long-lived token exchange: %s", long_lived)
            raise InstagramServiceError("Не удалось получить long-lived токен Instagram.")

        return TokenPayload(
            access_token=access_token,
            user_id=str(user_id),
            expires_in=int(expires_in),
        )

    def refresh_token(self, access_token: str) -> TokenPayload:
        """
        Обновить long-lived access token.
        
        Токен можно обновить в течение 24 часов до истечения.
        Новый токен будет действовать ещё ~60 дней.
        
        ВАЖНО: Токен нельзя обновить, если он:
        - Уже истёк
        - Был отозван пользователем
        - Является short-lived токеном
        
        Args:
            access_token: Текущий long-lived access token
            
        Returns:
            TokenPayload: Новый токен (user_id будет пустым)
            
        Raises:
            InstagramServiceError: При ошибке обновления
            
        Пример:
            >>> # Рекомендуется обновлять за 5 дней до истечения
            >>> new_token = service.refresh_token(old_token)
            >>> # Сохранить new_token.access_token в БД
        """
        refreshed = self._get(
            f"{self.GRAPH_URL}/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            },
        )
        new_token = refreshed.get("access_token")
        expires_in = refreshed.get("expires_in")
        if not new_token or not expires_in:
            logger.error("Invalid response from Instagram refresh: %s", refreshed)
            raise InstagramServiceError("Не удалось обновить токен Instagram.")
        return TokenPayload(access_token=new_token, user_id="", expires_in=int(expires_in))

    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Получить профиль Instagram пользователя.
        
        Возвращает данные:
        - id: Instagram User ID (числовой идентификатор)
        - username: Имя пользователя (@username)
        - account_type: Тип аккаунта (BUSINESS, MEDIA_CREATOR, PERSONAL)
        - media_count: Количество публикаций
        
        Args:
            access_token: Валидный access token
            
        Returns:
            Dict: Данные профиля из Instagram API
            
        Raises:
            InstagramServiceError: При ошибке API
            
        Пример:
            >>> profile = service.fetch_profile(token)
            >>> print(profile)
            {
                "id": "17841400000000000",
                "username": "company_account",
                "account_type": "BUSINESS",
                "media_count": 42
            }
        """
        return self._get(
            f"{self.GRAPH_URL}/me",
            params={
                "fields": "id,username,account_type,media_count",
                "access_token": access_token,
            },
        )

    def fetch_media(self, access_token: str, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Получить медиа контент (посты) пользователя.
        
        Возвращает список последних публикаций с полями:
        - id: ID публикации
        - caption: Подпись к посту (может быть None)
        - media_type: Тип (IMAGE, VIDEO, CAROUSEL_ALBUM)
        - media_url: Прямой URL медиа файла
        - permalink: Ссылка на пост в Instagram
        - thumbnail_url: Превью для видео (None для изображений)
        - timestamp: Дата публикации в ISO формате
        
        Args:
            access_token: Валидный access token
            limit: Количество постов (по умолчанию 12, максимум 25)
            
        Returns:
            List[Dict]: Список медиа объектов
            
        Raises:
            InstagramServiceError: При ошибке API
            
        Пример:
            >>> media = service.fetch_media(token, limit=10)
            >>> for post in media:
            ...     print(f"{post['media_type']}: {post['permalink']}")
        """
        payload = self._get(
            f"{self.GRAPH_URL}/me/media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp",
                "limit": limit,
                "access_token": access_token,
            },
        )
        data = payload.get("data", [])
        if not isinstance(data, list):
            logger.error("Unexpected media payload: %s", payload)
            raise InstagramServiceError("Не удалось получить медиа из Instagram.")
        return data

    @staticmethod
    def compute_expiration(expires_in: int) -> datetime:
        """
        Вычислить дату истечения токена.
        
        Args:
            expires_in: Время жизни токена в секундах
            
        Returns:
            datetime: Дата и время истечения (UTC timezone-aware)
            
        Пример:
            >>> expires_at = InstagramService.compute_expiration(5183944)
            >>> print(expires_at)  # 2025-02-01 12:00:00+00:00
        """
        return datetime.now(tz=ZoneInfo("UTC")) + timedelta(seconds=expires_in)

    # =========================================================================
    # ПРИВАТНЫЕ МЕТОДЫ ДЛЯ HTTP ЗАПРОСОВ
    # =========================================================================

    @staticmethod
    def _handle_response(response: Response) -> Dict[str, Any]:
        """
        Обработать ответ от Instagram API.
        
        Проверяет статус код, парсит JSON и обрабатывает ошибки.
        
        Args:
            response: Объект Response от requests
            
        Returns:
            Dict: Распарсенный JSON ответ
            
        Raises:
            InstagramServiceError: При HTTP ошибке или невалидном JSON
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            content = response.text
            logger.error("Instagram API error: %s, content=%s", exc, content)
            raise InstagramServiceError("Ошибка при обращении к API Instagram.") from exc
        except ValueError as exc:
            logger.error("Invalid JSON from Instagram API: %s", exc)
            raise InstagramServiceError("Instagram вернул некорректный ответ.") from exc

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнить GET запрос к Instagram API.
        
        Args:
            url: URL эндпоинта
            params: Query параметры
            
        Returns:
            Dict: JSON ответ API
        """
        response = requests.get(url, params=params or {}, timeout=15)
        return self._handle_response(response)

    def _post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнить POST запрос к Instagram API.
        
        Args:
            url: URL эндпоинта
            data: Данные формы (form-urlencoded)
            
        Returns:
            Dict: JSON ответ API
        """
        response = requests.post(url, data=data or {}, timeout=15)
        return self._handle_response(response)
