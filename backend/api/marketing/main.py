"""API эндпоинты для маркетинговых кампаний.

Предоставляет:
- CRUD операции для кампаний
- Дашборд с общей статистикой
- Генерация UTM-ссылок
- Трекинг переходов
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api.marketing import schemas
from backend.database import get_db
from backend.database.marketing.crud import CampaignCRUD

router = APIRouter(
    prefix="/api/marketing",
    tags=["marketing"],
)

campaign_crud = CampaignCRUD()


# =============================================================================
# ДАШБОРД
# =============================================================================

@router.get(
    "/dashboard",
    response_model=schemas.DashboardStats,
    summary="Общая статистика маркетинга",
)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Возвращает общую статистику маркетинга:
    - Общее число переходов, лидов, сделок
    - Список кампаний с метриками
    """
    return campaign_crud.get_dashboard_stats(db)


# =============================================================================
# CRUD КАМПАНИЙ
# =============================================================================

@router.get(
    "/campaigns",
    response_model=List[schemas.CampaignRead],
    summary="Список кампаний",
)
def list_campaigns(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=1000, description="Макс. число записей"),
    platform: Optional[schemas.CampaignPlatform] = Query(None, description="Фильтр по платформе"),
    campaign_status: Optional[schemas.CampaignStatus] = Query(None, alias="status", description="Фильтр по статусу"),
    db: Session = Depends(get_db),
):
    """Получить список всех кампаний с фильтрацией."""
    return campaign_crud.get_campaigns(
        db,
        skip=skip,
        limit=limit,
        platform=platform,
        status=campaign_status
    )


@router.get(
    "/campaigns/search",
    response_model=List[schemas.CampaignRead],
    summary="Поиск кампаний",
)
def search_campaigns(
    query: str = Query(..., min_length=1, description="Строка для поиска"),
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db),
):
    """Поиск кампаний по названию или аккаунту."""
    return campaign_crud.search_campaigns(db, query, skip=skip, limit=limit)


@router.get(
    "/campaigns/{campaign_id}",
    response_model=schemas.CampaignRead,
    summary="Получить кампанию по ID",
)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Получить детали кампании по ID."""
    campaign = campaign_crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Кампания с ID={campaign_id} не найдена"
        )
    return campaign


@router.post(
    "/campaigns",
    response_model=schemas.CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать кампанию",
)
def create_campaign(
    payload: schemas.CampaignCreate,
    db: Session = Depends(get_db),
):
    """Создать новую рекламную кампанию."""
    try:
        campaign = campaign_crud.create_campaign(db, payload)
        # Автоматически генерируем UTM-ссылку
        campaign_crud.generate_utm_link(db, campaign.id)
        db.refresh(campaign)
        return campaign
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/campaigns/{campaign_id}",
    response_model=schemas.CampaignRead,
    summary="Обновить кампанию",
)
def update_campaign(
    campaign_id: int,
    payload: schemas.CampaignUpdate,
    db: Session = Depends(get_db),
):
    """Обновить данные кампании."""
    campaign = campaign_crud.update_campaign(db, campaign_id, payload)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Кампания с ID={campaign_id} не найдена"
        )
    return campaign


@router.delete(
    "/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить кампанию",
)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Удалить кампанию."""
    success = campaign_crud.delete_campaign(db, campaign_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Кампания с ID={campaign_id} не найдена"
        )
    return None


# =============================================================================
# МЕТРИКИ И СТАТИСТИКА
# =============================================================================

@router.get(
    "/campaigns/{campaign_id}/metrics",
    response_model=schemas.CampaignMetrics,
    summary="Метрики кампании",
)
def get_campaign_metrics(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить полные метрики кампании:
    - CR_lead, CR_sale, CR_total
    - CPA, CPS
    - Health status
    """
    try:
        return campaign_crud.get_campaign_metrics(db, campaign_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# UTM-ССЫЛКИ
# =============================================================================

@router.post(
    "/campaigns/{campaign_id}/generate-link",
    response_model=schemas.GenerateLinkResponse,
    summary="Сгенерировать UTM-ссылку",
)
def generate_utm_link(
    campaign_id: int,
    base_url: Optional[str] = Query(None, description="Базовый URL (опционально)"),
    db: Session = Depends(get_db),
):
    """
    Сгенерировать уникальную UTM-ссылку для кампании.

    Если base_url не указан, используется target_url кампании
    или дефолтный URL Telegram Mini App.
    """
    try:
        campaign = campaign_crud.generate_utm_link(db, campaign_id, base_url)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Кампания с ID={campaign_id} не найдена"
            )
        return schemas.GenerateLinkResponse(
            utm_source=campaign.utm_source,
            utm_link=campaign.utm_link,
            target_url=campaign.target_url
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# ТРЕКИНГ ПЕРЕХОДОВ
# =============================================================================

@router.post(
    "/track-click",
    response_model=schemas.TrackClickResponse,
    summary="Трекинг перехода",
)
def track_click(
    payload: schemas.TrackClickRequest,
    db: Session = Depends(get_db),
):
    """
    Зарегистрировать переход по UTM-ссылке.

    Вызывается из Mini App при открытии с параметром startapp.
    """
    campaign = campaign_crud.track_click_by_utm(db, payload.utm_source)
    if not campaign:
        return schemas.TrackClickResponse(success=False)

    return schemas.TrackClickResponse(
        success=True,
        campaign_id=campaign.id,
        clicks=campaign.clicks
    )


@router.get(
    "/track/{utm_source}",
    response_model=schemas.TrackClickResponse,
    summary="Трекинг перехода (GET)",
)
def track_click_get(
    utm_source: str,
    db: Session = Depends(get_db),
):
    """
    Альтернативный GET-эндпоинт для трекинга.
    Удобен для использования в пикселях и редиректах.
    """
    campaign = campaign_crud.track_click_by_utm(db, utm_source)
    if not campaign:
        return schemas.TrackClickResponse(success=False)

    return schemas.TrackClickResponse(
        success=True,
        campaign_id=campaign.id,
        clicks=campaign.clicks
    )