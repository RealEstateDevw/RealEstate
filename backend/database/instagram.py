"""
Instagram CRUD — Слой работы с базой данных для Instagram интеграции.

Этот модуль предоставляет CRUD операции для двух сущностей:
1. InstagramSettings — настройки API (App ID, Secret)
2. InstagramIntegration — подключённые аккаунты Instagram

СТРУКТУРА МОДУЛЯ:
-----------------
┌─────────────────────────────────────────────────────────────────┐
│                    InstagramSettingsCRUD                        │
├─────────────────────────────────────────────────────────────────┤
│  get_active()        │ Получить активные настройки API         │
│  create_or_update()  │ Сохранить новые настройки               │
│  delete_active()     │ Деактивировать настройки                │
├─────────────────────────────────────────────────────────────────┤
│                   InstagramIntegrationCRUD                      │
├─────────────────────────────────────────────────────────────────┤
│  get_active()          │ Получить активное подключение         │
│  upsert_connection()   │ Создать/обновить подключение          │
│  update_profile_snapshot() │ Обновить кэш профиля              │
│  disconnect_active()   │ Отключить аккаунт                     │
└─────────────────────────────────────────────────────────────────┘

ПАТТЕРНЫ:
---------
1. Soft Delete: Записи не удаляются физически, а помечаются is_active=False
2. Upsert: При повторном подключении обновляется существующая запись
3. Single Active: Только одна запись может быть активной для пользователя

ИСПОЛЬЗОВАНИЕ:
--------------
>>> from backend.database.instagram import InstagramSettingsCRUD, InstagramIntegrationCRUD
>>> 
>>> settings_crud = InstagramSettingsCRUD()
>>> integration_crud = InstagramIntegrationCRUD()
>>> 
>>> # Сохранить настройки
>>> settings = settings_crud.create_or_update(
...     db,
...     app_id="123...",
...     app_secret="abc...",
...     redirect_uri="https://..."
... )
>>> 
>>> # Подключить аккаунт
>>> integration = integration_crud.upsert_connection(
...     db,
...     user_id=1,
...     instagram_user_id="17841...",
...     username="company",
...     ...
... )

Автор: RealEstate CRM Team
Дата создания: 2025
"""

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database.models import InstagramIntegration, InstagramSettings

logger = logging.getLogger(__name__)


# =============================================================================
# CRUD ДЛЯ НАСТРОЕК INSTAGRAM API
# =============================================================================

class InstagramSettingsCRUD:
    """
    CRUD класс для управления настройками Instagram API.
    
    Настройки хранят данные приложения Meta for Developers:
    - app_id: ID приложения
    - app_secret: Секретный ключ
    - redirect_uri: URL для OAuth callback
    
    ВАЖНО: В системе может быть только одна активная запись настроек.
    При сохранении новых настроек предыдущие деактивируются.
    
    Пример:
        >>> crud = InstagramSettingsCRUD()
        >>> settings = crud.get_active(db)
        >>> if settings:
        ...     print(f"App ID: {settings.app_id}")
    """

    def get_active(self, db: Session) -> Optional[InstagramSettings]:
        """
        Получить активные настройки Instagram API.
        
        Возвращает последнюю активную запись настроек.
        Если настройки не найдены, возвращает None.
        
        Args:
            db: Сессия SQLAlchemy
            
        Returns:
            InstagramSettings или None
            
        Пример:
            >>> settings = crud.get_active(db)
            >>> if not settings:
            ...     raise HTTPException(503, "Instagram не настроен")
        """
        return (
            db.query(InstagramSettings)
            .filter(InstagramSettings.is_active.is_(True))
            .order_by(InstagramSettings.updated_at.desc())
            .first()
        )

    def create_or_update(
        self,
        db: Session,
        *,
        app_id: str,
        app_secret: str,
        redirect_uri: str,
        created_by: Optional[int] = None,
    ) -> InstagramSettings:
        """
        Создать или обновить настройки Instagram API.
        
        При сохранении:
        1. Все предыдущие активные настройки деактивируются
        2. Создаётся новая запись с is_active=True
        3. Сохраняется ID администратора, создавшего настройки
        
        Args:
            db: Сессия SQLAlchemy
            app_id: Instagram App ID
            app_secret: Instagram App Secret
            redirect_uri: OAuth Redirect URI
            created_by: ID пользователя-администратора (опционально)
            
        Returns:
            InstagramSettings: Созданная запись настроек
            
        Raises:
            SQLAlchemyError: При ошибке БД (автоматический rollback)
            
        Пример:
            >>> settings = crud.create_or_update(
            ...     db,
            ...     app_id="123456789",
            ...     app_secret="abc123...",
            ...     redirect_uri="https://example.com/callback",
            ...     created_by=admin_user.id
            ... )
        """
        try:
            # Шаг 1: Деактивируем все предыдущие настройки
            # Это гарантирует, что в системе только одна активная запись
            db.query(InstagramSettings).filter(
                InstagramSettings.is_active.is_(True)
            ).update({InstagramSettings.is_active: False})

            # Шаг 2: Создаём новые настройки
            settings = InstagramSettings(
                app_id=app_id,
                app_secret=app_secret,
                redirect_uri=redirect_uri,
                is_active=True,
                created_by=created_by,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
            return settings
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to save Instagram settings: %s", exc)
            raise

    def delete_active(self, db: Session) -> bool:
        """
        Удалить (деактивировать) настройки Instagram API.
        
        Не удаляет запись физически, а устанавливает is_active=False.
        После этого Instagram интеграция перестанет работать до
        повторной настройки.
        
        Args:
            db: Сессия SQLAlchemy
            
        Returns:
            bool: True если настройки были деактивированы, False если не найдены
            
        Raises:
            SQLAlchemyError: При ошибке БД (автоматический rollback)
            
        Пример:
            >>> success = crud.delete_active(db)
            >>> if success:
            ...     print("Настройки удалены")
        """
        try:
            result = (
                db.query(InstagramSettings)
                .filter(InstagramSettings.is_active.is_(True))
                .update({InstagramSettings.is_active: False})
            )
            db.commit()
            return result > 0  # True если хотя бы одна запись обновлена
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to delete Instagram settings: %s", exc)
            raise


# =============================================================================
# CRUD ДЛЯ ПОДКЛЮЧЕНИЙ INSTAGRAM АККАУНТОВ
# =============================================================================

class InstagramIntegrationCRUD:
    """
    CRUD класс для управления подключениями Instagram аккаунтов.
    
    Каждое подключение привязано к администратору (user_id) и содержит:
    - Данные Instagram аккаунта (user_id, username)
    - Access token и срок его действия
    - Кэшированные данные профиля (account_type, media_count)
    
    ВАЖНО: У каждого администратора может быть только одно активное подключение.
    При подключении нового аккаунта предыдущий деактивируется.
    
    Пример:
        >>> crud = InstagramIntegrationCRUD()
        >>> integration = crud.get_active(db, user_id=admin.id)
        >>> if integration:
        ...     print(f"Подключён: @{integration.username}")
    """

    def get_active(self, db: Session, user_id: int) -> Optional[InstagramIntegration]:
        """
        Получить активное подключение Instagram для пользователя.
        
        Args:
            db: Сессия SQLAlchemy
            user_id: ID пользователя-администратора
            
        Returns:
            InstagramIntegration или None
            
        Пример:
            >>> integration = crud.get_active(db, user_id=1)
            >>> if integration and integration.access_token:
            ...     # Можно использовать токен
            ...     pass
        """
        return (
            db.query(InstagramIntegration)
            .filter(
                InstagramIntegration.is_active.is_(True),
                InstagramIntegration.user_id == user_id,
            )
            .order_by(InstagramIntegration.connected_at.desc())
            .first()
        )

    def upsert_connection(
        self,
        db: Session,
        *,
        user_id: int,
        instagram_user_id: str,
        username: str,
        account_type: Optional[str],
        media_count: Optional[int],
        access_token: str,
        token_expires_at: datetime,
    ) -> InstagramIntegration:
        """
        Создать или обновить подключение Instagram (Upsert).
        
        Логика работы:
        1. Ищет существующее подключение по instagram_user_id и user_id
        2. Если найдено — обновляет данные
        3. Если не найдено — создаёт новую запись
        4. Деактивирует все другие подключения этого пользователя
        
        Args:
            db: Сессия SQLAlchemy
            user_id: ID администратора
            instagram_user_id: Instagram User ID
            username: @username в Instagram
            account_type: Тип аккаунта (BUSINESS, PERSONAL, и т.д.)
            media_count: Количество публикаций
            access_token: OAuth access token
            token_expires_at: Дата истечения токена
            
        Returns:
            InstagramIntegration: Созданная или обновлённая запись
            
        Raises:
            SQLAlchemyError: При ошибке БД (автоматический rollback)
            
        Пример:
            >>> integration = crud.upsert_connection(
            ...     db,
            ...     user_id=admin.id,
            ...     instagram_user_id="17841400000000000",
            ...     username="company_account",
            ...     account_type="BUSINESS",
            ...     media_count=42,
            ...     access_token="IGQVJ...",
            ...     token_expires_at=datetime(2025, 3, 1)
            ... )
        """
        try:
            # Шаг 1: Ищем существующее подключение
            integration = (
                db.query(InstagramIntegration)
                .filter(
                    InstagramIntegration.instagram_user_id == instagram_user_id,
                    InstagramIntegration.user_id == user_id,
                )
                .first()
            )
            now_utc = datetime.now(tz=ZoneInfo("UTC"))
            
            if integration:
                # Шаг 2a: Обновляем существующее подключение
                integration.username = username
                integration.account_type = account_type
                integration.media_count = media_count
                integration.access_token = access_token
                integration.token_expires_at = token_expires_at
                integration.connected_at = now_utc
                integration.is_active = True
            else:
                # Шаг 2b: Создаём новое подключение
                integration = InstagramIntegration(
                    user_id=user_id,
                    instagram_user_id=instagram_user_id,
                    username=username,
                    account_type=account_type,
                    media_count=media_count,
                    access_token=access_token,
                    token_expires_at=token_expires_at,
                    connected_at=now_utc,
                    is_active=True,
                )
                db.add(integration)

            # Шаг 3: Деактивируем другие подключения этого пользователя
            # (у пользователя может быть только одно активное подключение)
            (
                db.query(InstagramIntegration)
                .filter(
                    InstagramIntegration.id != integration.id,
                    InstagramIntegration.is_active.is_(True),
                    InstagramIntegration.user_id == user_id,
                )
                .update({InstagramIntegration.is_active: False})
            )

            db.commit()
            db.refresh(integration)
            return integration
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to upsert Instagram integration: %s", exc)
            raise

    def update_profile_snapshot(
        self,
        db: Session,
        integration_id: int,
        *,
        user_id: int,
        account_type: Optional[str],
        media_count: Optional[int],
    ) -> Optional[InstagramIntegration]:
        """
        Обновить кэшированные данные профиля Instagram.
        
        Вызывается после успешного запроса к Instagram API для
        синхронизации локальных данных (account_type, media_count).
        
        Args:
            db: Сессия SQLAlchemy
            integration_id: ID записи подключения
            user_id: ID пользователя (для дополнительной проверки)
            account_type: Тип аккаунта
            media_count: Количество публикаций
            
        Returns:
            InstagramIntegration или None если не найдено
            
        Raises:
            SQLAlchemyError: При ошибке БД (автоматический rollback)
            
        Пример:
            >>> # После получения профиля из Instagram API
            >>> crud.update_profile_snapshot(
            ...     db,
            ...     integration_id=integration.id,
            ...     user_id=admin.id,
            ...     account_type=profile["account_type"],
            ...     media_count=profile["media_count"]
            ... )
        """
        try:
            integration = (
                db.query(InstagramIntegration)
                .filter(
                    InstagramIntegration.id == integration_id,
                    InstagramIntegration.user_id == user_id,
                )
                .first()
            )
            if not integration:
                return None
                
            # Обновляем кэшированные данные
            integration.account_type = account_type
            integration.media_count = media_count
            integration.updated_at = datetime.now(tz=ZoneInfo("UTC"))
            
            db.commit()
            db.refresh(integration)
            return integration
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to update Instagram profile snapshot: %s", exc)
            raise

    def disconnect_active(self, db: Session, user_id: int) -> Optional[InstagramIntegration]:
        """
        Отключить активный Instagram аккаунт.
        
        Действия при отключении:
        1. Устанавливает is_active=False
        2. Очищает access_token (для безопасности)
        3. Обновляет updated_at
        
        Запись НЕ удаляется из БД — это позволяет сохранить историю
        и упростить переподключение того же аккаунта.
        
        Args:
            db: Сессия SQLAlchemy
            user_id: ID пользователя-администратора
            
        Returns:
            InstagramIntegration: Отключённая запись или None если не найдено
            
        Raises:
            SQLAlchemyError: При ошибке БД (автоматический rollback)
            
        Пример:
            >>> integration = crud.disconnect_active(db, user_id=admin.id)
            >>> if integration:
            ...     print(f"Отключён: @{integration.username}")
        """
        try:
            integration = self.get_active(db, user_id=user_id)
            if not integration:
                return None
                
            # Деактивируем и очищаем токен
            integration.is_active = False
            integration.access_token = ""  # Очищаем для безопасности
            integration.updated_at = datetime.now(tz=ZoneInfo("UTC"))
            
            db.commit()
            db.refresh(integration)
            return integration
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to disconnect Instagram integration: %s", exc)
            raise
