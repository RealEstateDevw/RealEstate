"""
Instagram API Router — Модуль интеграции с Instagram.

Этот модуль предоставляет REST API для:
1. Настройки интеграции с Instagram (App ID, App Secret, Redirect URI)
2. OAuth авторизации через Instagram Basic Display API
3. Получения профиля и медиа контента из Instagram

АРХИТЕКТУРА:
-----------
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend       │────▶│  API Endpoints   │────▶│  Instagram API  │
│  (Admin Panel)  │◀────│  (этот модуль)   │◀────│  (Meta)         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  База данных     │
                        │  (Settings,      │
                        │   Integration)   │
                        └──────────────────┘

ЭНДПОИНТЫ:
----------
Настройки API:
- GET  /api/instagram/settings/status — проверка настроек
- POST /api/instagram/settings — сохранение настроек
- DELETE /api/instagram/settings — удаление настроек

OAuth авторизация:
- GET /api/instagram/auth-url — получить URL для авторизации
- GET /api/instagram/callback — callback после авторизации Instagram

Работа с аккаунтом:
- GET /api/instagram/status — статус подключения
- GET /api/instagram/profile — профиль Instagram
- GET /api/instagram/media — медиа контент (посты)
- DELETE /api/instagram/connection — отключить аккаунт

БЕЗОПАСНОСТЬ:
-------------
- Все эндпоинты доступны только администраторам (роль "Админ")
- OAuth state защищён JWT токеном с временем жизни 10 минут
- App Secret хранится в БД и маскируется при отображении

ИСПОЛЬЗОВАНИЕ:
--------------
1. Админ настраивает App ID/Secret через /settings
2. Админ инициирует OAuth через /auth-url
3. Instagram перенаправляет на /callback с кодом
4. Система обменивает код на access_token
5. Можно получать profile и media

Автор: RealEstate CRM Team
Дата создания: 2025
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from authlib.jose import jwt
from authlib.jose.errors import JoseError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from backend import get_db
from backend.api.instagram.schemas import (
    AuthUrlResponse,
    DisconnectResponse,
    InstagramMediaResponse,
    InstagramProfile,
    InstagramStatusResponse,
    InstagramSettingsCreate,
    InstagramSettingsResponse,
    InstagramSettingsStatusResponse,
)
from backend.api.instagram.service import InstagramService, InstagramServiceError
from backend.core.auth import SECRET_KEY
from backend.core.deps import get_current_user_from_cookie
from backend.database.instagram import InstagramIntegrationCRUD, InstagramSettingsCRUD
from backend.database.models import InstagramIntegration

# =============================================================================
# КОНФИГУРАЦИЯ РОУТЕРА
# =============================================================================

router = APIRouter(prefix="/api/instagram", tags=["instagram"])
"""
FastAPI роутер для Instagram API.
- prefix: /api/instagram — базовый путь для всех эндпоинтов
- tags: ["instagram"] — группировка в Swagger документации
"""

logger = logging.getLogger(__name__)
"""Логгер для отслеживания ошибок и событий Instagram интеграции."""

# Инициализация CRUD классов для работы с БД
integration_crud = InstagramIntegrationCRUD()
"""CRUD для управления подключениями Instagram аккаунтов."""

settings_crud = InstagramSettingsCRUD()
"""CRUD для управления настройками Instagram API (App ID, Secret)."""


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def _get_instagram_service(db: Session) -> InstagramService:
    """
    Создать экземпляр InstagramService с настройками из БД.
    
    Настройки (App ID, App Secret, Redirect URI) хранятся в базе данных
    и добавляются администратором через панель управления.
    
    Args:
        db: Сессия базы данных SQLAlchemy
        
    Returns:
        InstagramService: Сервис для работы с Instagram API
        
    Raises:
        HTTPException (503): Если настройки не найдены в БД
        HTTPException (503): Если настройки некорректны
        
    Пример:
        >>> service = _get_instagram_service(db)
        >>> auth_url = service.build_auth_url(state)
    """
    db_settings = settings_crud.get_active(db)
    if not db_settings:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Instagram не настроен. Перейдите в настройки маркетинга "
                "и добавьте App ID, App Secret и Redirect URI."
            ),
        )
    try:
        return InstagramService(
            db_settings.app_id,
            db_settings.app_secret,
            db_settings.redirect_uri,
        )
    except InstagramServiceError as exc:
        logger.error("Instagram service misconfigured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _ensure_admin(user) -> None:
    """
    Проверить, что пользователь является администратором.
    
    Instagram интеграция доступна только администраторам системы
    для предотвращения несанкционированного доступа к данным.
    
    Args:
        user: Объект текущего пользователя из cookie
        
    Raises:
        HTTPException (403): Если пользователь не админ
    """
    if not user or not getattr(user, "role", None) or user.role.name != "Админ":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к Instagram интеграции разрешён только администраторам.",
        )


def _build_state(user_id: int) -> str:
    """
    Создать OAuth state параметр для защиты от CSRF атак.
    
    State кодируется как JWT токен, содержащий:
    - sub: ID пользователя (для проверки при callback)
    - exp: время истечения (10 минут)
    
    Args:
        user_id: ID пользователя, инициировавшего авторизацию
        
    Returns:
        str: Закодированный JWT токен
        
    Пример:
        >>> state = _build_state(user_id=123)
        >>> # state передаётся в Instagram OAuth URL
        >>> # при callback проверяется через _validate_state
    """
    payload = {
        "sub": str(user_id),
        "exp": (datetime.now(tz=ZoneInfo("UTC")) + timedelta(minutes=10)).timestamp(),
    }
    token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)
    return token.decode("utf-8") if isinstance(token, bytes) else token


def _validate_state(state: str, expected_user_id: int) -> None:
    """
    Проверить OAuth state параметр при callback.
    
    Валидация включает:
    1. Проверку подписи JWT
    2. Проверку времени истечения
    3. Проверку соответствия user_id
    
    Args:
        state: State параметр из callback URL
        expected_user_id: Ожидаемый ID пользователя
        
    Raises:
        HTTPException (400): Если state невалиден или истёк
    """
    try:
        claims = jwt.decode(state, SECRET_KEY)
        claims.validate_exp(now=int(datetime.now(tz=ZoneInfo("UTC")).timestamp()))
        if claims.get("sub") != str(expected_user_id):
            raise JoseError("State user mismatch")
    except JoseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный state Instagram.",
        ) from exc


def _get_active_integration(db: Session, user_id: int) -> InstagramIntegration:
    """
    Получить активное подключение Instagram для пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя-администратора
        
    Returns:
        InstagramIntegration: Объект подключения с access_token
        
    Raises:
        HTTPException (404): Если подключение не найдено
    """
    integration = integration_crud.get_active(db, user_id=user_id)
    if not integration or not integration.access_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instagram не подключен.",
        )
    return integration


def _ensure_token_valid(
    db: Session,
    service: InstagramService,
    integration: InstagramIntegration,
) -> InstagramIntegration:
    """
    Проверить и обновить access_token при необходимости.
    
    Instagram токены действительны ~60 дней. Эта функция проверяет
    срок действия и автоматически обновляет токен за 5 дней до истечения.
    
    Процесс обновления:
    1. Проверка срока действия токена
    2. Если до истечения < 5 дней — вызов refresh_token API
    3. Получение нового профиля для проверки
    4. Сохранение нового токена в БД
    
    Args:
        db: Сессия базы данных
        service: Сервис Instagram API
        integration: Текущее подключение
        
    Returns:
        InstagramIntegration: Обновлённое подключение (или исходное, если обновление не требуется)
    """
    now = datetime.now(tz=ZoneInfo("UTC"))
    expires_at = integration.token_expires_at or now
    
    # Если до истечения более 5 дней — обновление не требуется
    if expires_at - now > timedelta(days=5):
        return integration

    # Обновляем токен через Instagram API
    refreshed = service.refresh_token(integration.access_token)
    profile = service.fetch_profile(refreshed.access_token)
    new_expiration = service.compute_expiration(refreshed.expires_in)
    
    # Сохраняем обновлённые данные в БД
    return integration_crud.upsert_connection(
        db,
        user_id=integration.user_id,
        instagram_user_id=str(profile.get("id") or integration.instagram_user_id),
        username=profile.get("username") or integration.username,
        account_type=profile.get("account_type"),
        media_count=profile.get("media_count"),
        access_token=refreshed.access_token,
        token_expires_at=new_expiration,
    )


# =============================================================================
# ЭНДПОИНТЫ: НАСТРОЙКИ INSTAGRAM API
# =============================================================================

@router.get("/settings/status", response_model=InstagramSettingsStatusResponse)
def get_settings_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Проверить статус настроек Instagram API.
    
    Возвращает информацию о том, настроен ли Instagram:
    - is_configured: True/False
    - settings: данные настроек (App ID, маскированный Secret, Redirect URI)
    
    Используется фронтендом для определения, нужно ли показывать
    форму настроек или можно переходить к подключению аккаунта.
    
    Returns:
        InstagramSettingsStatusResponse: Статус и данные настроек
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    db_settings = settings_crud.get_active(db)
    if not db_settings:
        return InstagramSettingsStatusResponse(is_configured=False, settings=None)
    
    return InstagramSettingsStatusResponse(
        is_configured=True,
        settings=InstagramSettingsResponse(
            id=db_settings.id,
            app_id=db_settings.app_id,
            # Маскируем App Secret для безопасности (показываем только первые и последние 4 символа)
            app_secret_masked=db_settings.app_secret[:4] + "*" * 20 + db_settings.app_secret[-4:],
            redirect_uri=db_settings.redirect_uri,
            created_at=db_settings.created_at,
            updated_at=db_settings.updated_at,
        ),
    )


@router.post("/settings", response_model=InstagramSettingsResponse)
def save_settings(
    data: InstagramSettingsCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Сохранить настройки Instagram API.
    
    Принимает данные приложения Meta for Developers:
    - app_id: ID приложения Instagram
    - app_secret: Секретный ключ приложения
    - redirect_uri: URL для OAuth callback
    
    При сохранении:
    1. Деактивируются все предыдущие настройки
    2. Создаётся новая запись с is_active=True
    3. Сохраняется ID админа, создавшего настройки
    
    Returns:
        InstagramSettingsResponse: Сохранённые настройки (с маскированным Secret)
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    db_settings = settings_crud.create_or_update(
        db,
        app_id=data.app_id,
        app_secret=data.app_secret,
        redirect_uri=data.redirect_uri,
        created_by=current_user.id,
    )
    return InstagramSettingsResponse(
        id=db_settings.id,
        app_id=db_settings.app_id,
        app_secret_masked=db_settings.app_secret[:4] + "*" * 20 + db_settings.app_secret[-4:],
        redirect_uri=db_settings.redirect_uri,
        created_at=db_settings.created_at,
        updated_at=db_settings.updated_at,
    )


@router.delete("/settings", response_model=DisconnectResponse)
def delete_settings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Удалить настройки Instagram API.
    
    ВНИМАНИЕ: После удаления настроек все подключённые аккаунты
    перестанут работать до повторной настройки.
    
    Returns:
        DisconnectResponse: success=True если удалено успешно
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    result = settings_crud.delete_active(db)
    return DisconnectResponse(success=result)


# =============================================================================
# ЭНДПОИНТЫ: OAUTH АВТОРИЗАЦИЯ
# =============================================================================

@router.get("/auth-url", response_model=AuthUrlResponse)
def get_auth_url(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Получить URL для OAuth авторизации Instagram.
    
    Генерирует URL вида:
    https://api.instagram.com/oauth/authorize?
        client_id={app_id}&
        redirect_uri={redirect_uri}&
        scope=user_profile,user_media&
        response_type=code&
        state={jwt_state}
    
    Фронтенд должен перенаправить пользователя на этот URL.
    После авторизации Instagram перенаправит на /callback.
    
    Returns:
        AuthUrlResponse: URL для перенаправления
        
    Raises:
        HTTPException (503): Если Instagram не настроен
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    service = _get_instagram_service(db)
    state = _build_state(current_user.id)
    return AuthUrlResponse(url=service.build_auth_url(state))


@router.get("/callback")
def instagram_callback(
    code: str = Query(..., description="Authorization code из Instagram"),
    state: Optional[str] = Query(None),
    current_user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    """
    Callback эндпоинт для OAuth авторизации Instagram.
    
    Instagram перенаправляет сюда после авторизации с параметрами:
    - code: Временный код для обмена на access_token
    - state: JWT токен для защиты от CSRF
    
    Процесс:
    1. Валидация state (проверка подписи, времени, user_id)
    2. Обмен code на short-lived token
    3. Обмен short-lived на long-lived token (~60 дней)
    4. Получение профиля Instagram
    5. Сохранение данных в БД
    6. Редирект на страницу маркетинга
    
    При ошибке редиректит на страницу подключения с параметром error.
    
    Returns:
        RedirectResponse: Перенаправление на /dashboard/admin/marketing
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    redirect_on_error = "/dashboard/admin/marketing/instagram/connect"
    try:
        service = _get_instagram_service(db)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Отсутствует state",
            )
        _validate_state(state, current_user.id)
        
        # Обмен кода на токены
        token_payload = service.exchange_code_for_token(code)
        profile = service.fetch_profile(token_payload.access_token)
        expires_at = service.compute_expiration(token_payload.expires_in)

        # Сохранение подключения в БД
        integration_crud.upsert_connection(
            db,
            user_id=current_user.id,
            instagram_user_id=str(profile.get("id") or token_payload.user_id),
            username=profile.get("username") or "",
            account_type=profile.get("account_type"),
            media_count=profile.get("media_count"),
            access_token=token_payload.access_token,
            token_expires_at=expires_at,
        )
        return RedirectResponse(
            url="/dashboard/admin/marketing",
            status_code=status.HTTP_302_FOUND,
        )
    except InstagramServiceError as exc:
        logger.error("Instagram callback failed: %s", exc)
        return RedirectResponse(
            url=f"{redirect_on_error}?error={quote_plus(str(exc))}",
            status_code=status.HTTP_302_FOUND,
        )
    except HTTPException as exc:
        logger.error("Instagram callback validation failed: %s", exc.detail)
        return RedirectResponse(
            url=f"{redirect_on_error}?error={quote_plus(str(exc.detail))}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected Instagram callback error: %s", exc)
        return RedirectResponse(
            url=f"{redirect_on_error}?error={quote_plus('Не удалось завершить авторизацию.')}",
            status_code=status.HTTP_302_FOUND,
        )


# =============================================================================
# ЭНДПОИНТЫ: РАБОТА С АККАУНТОМ
# =============================================================================

@router.get("/status", response_model=InstagramStatusResponse)
def instagram_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Получить статус подключения Instagram аккаунта.
    
    Проверяет:
    1. Настроен ли Instagram API (есть ли App ID/Secret)
    2. Подключён ли аккаунт Instagram
    3. Валиден ли access_token
    
    При необходимости автоматически обновляет токен.
    При ошибке API автоматически отключает интеграцию.
    
    Returns:
        InstagramStatusResponse:
            - connected: True если аккаунт подключён и работает
            - profile: Данные профиля (username, account_type, и т.д.)
            
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    
    # Проверяем, настроен ли Instagram
    db_settings = settings_crud.get_active(db)
    if not db_settings:
        return InstagramStatusResponse(connected=False, profile=None)
    
    service = _get_instagram_service(db)
    integration = integration_crud.get_active(db, user_id=current_user.id)
    if not integration or not integration.access_token:
        return InstagramStatusResponse(connected=False, profile=None)

    try:
        # Проверяем и обновляем токен при необходимости
        integration = _ensure_token_valid(db, service, integration)
        profile_data = service.fetch_profile(integration.access_token)
        
        # Обновляем кэшированные данные профиля в БД
        integration_crud.update_profile_snapshot(
            db,
            integration.id,
            user_id=current_user.id,
            account_type=profile_data.get("account_type"),
            media_count=profile_data.get("media_count"),
        )

        return InstagramStatusResponse(
            connected=True,
            profile=InstagramProfile(
                id=str(profile_data.get("id") or integration.instagram_user_id),
                username=profile_data.get("username") or integration.username,
                account_type=profile_data.get("account_type"),
                media_count=profile_data.get("media_count"),
                token_expires_at=integration.token_expires_at,
                connected_at=integration.connected_at,
            ),
        )
    except InstagramServiceError as exc:
        # При ошибке API отключаем интеграцию
        logger.error("Instagram status error, disconnecting: %s", exc)
        integration_crud.disconnect_active(db)
        return InstagramStatusResponse(connected=False, profile=None)


@router.get("/profile", response_model=InstagramProfile)
def instagram_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Получить профиль подключённого Instagram аккаунта.
    
    Возвращает актуальные данные профиля из Instagram API:
    - id: Instagram User ID
    - username: Имя пользователя
    - account_type: Тип аккаунта (BUSINESS, CREATOR, PERSONAL)
    - media_count: Количество публикаций
    - token_expires_at: Дата истечения токена
    - connected_at: Дата подключения
    
    Returns:
        InstagramProfile: Данные профиля
        
    Raises:
        HTTPException (404): Если аккаунт не подключён
        HTTPException (400): Если ошибка API Instagram
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    service = _get_instagram_service(db)
    integration = _get_active_integration(db, user_id=current_user.id)
    try:
        integration = _ensure_token_valid(db, service, integration)
        profile_data = service.fetch_profile(integration.access_token)
        integration_crud.update_profile_snapshot(
            db,
            integration.id,
            user_id=current_user.id,
            account_type=profile_data.get("account_type"),
            media_count=profile_data.get("media_count"),
        )
        return InstagramProfile(
            id=str(profile_data.get("id") or integration.instagram_user_id),
            username=profile_data.get("username") or integration.username,
            account_type=profile_data.get("account_type"),
            media_count=profile_data.get("media_count"),
            token_expires_at=integration.token_expires_at,
            connected_at=integration.connected_at,
        )
    except InstagramServiceError as exc:
        logger.error("Instagram profile fetch failed: %s", exc)
        integration_crud.disconnect_active(db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/media", response_model=InstagramMediaResponse)
def instagram_media(
    limit: int = Query(12, ge=1, le=25, description="Количество постов (1-25)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Получить медиа контент (посты) из Instagram.
    
    Возвращает список последних публикаций с данными:
    - id: ID публикации
    - caption: Подпись к посту
    - media_type: Тип (IMAGE, VIDEO, CAROUSEL_ALBUM)
    - media_url: URL медиа файла
    - permalink: Ссылка на пост в Instagram
    - thumbnail_url: URL превью (для видео)
    - timestamp: Дата публикации
    
    Args:
        limit: Количество постов (по умолчанию 12, максимум 25)
        
    Returns:
        InstagramMediaResponse: Список медиа объектов
        
    Raises:
        HTTPException (404): Если аккаунт не подключён
        HTTPException (400): Если ошибка API Instagram
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    service = _get_instagram_service(db)
    integration = _get_active_integration(db, user_id=current_user.id)
    try:
        integration = _ensure_token_valid(db, service, integration)
        media = service.fetch_media(integration.access_token, limit=limit)
        
        # Обновляем счётчик медиа в профиле
        integration_crud.update_profile_snapshot(
            db,
            integration.id,
            user_id=current_user.id,
            account_type=integration.account_type,
            media_count=len(media) if media else integration.media_count,
        )
        return InstagramMediaResponse(items=media)
    except InstagramServiceError as exc:
        logger.error("Instagram media fetch failed: %s", exc)
        integration_crud.disconnect_active(db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/connection", response_model=DisconnectResponse)
def disconnect_instagram(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_cookie),
):
    """
    Отключить Instagram аккаунт.
    
    Деактивирует текущее подключение:
    - Устанавливает is_active=False
    - Очищает access_token
    - Сохраняет время отключения
    
    После отключения можно подключить другой аккаунт
    или переподключить тот же.
    
    Returns:
        DisconnectResponse: success=True
        
    Доступ: Только администраторы
    """
    _ensure_admin(current_user)
    integration_crud.disconnect_active(db, user_id=current_user.id)
    return DisconnectResponse(success=True)
