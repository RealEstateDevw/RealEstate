from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api.campaigns import crud, schemas
from backend.api.dependencies import get_db

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
)

campaign_crud = crud.CampaignCRUD()


@router.get(
    "/",
    response_model=List[schemas.CampaignRead],
    summary="Список кампаний",
)
def list_campaigns(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=1000, description="Макс. число записей"),
    platform: schemas.CampaignPlatform = Query(None, description="Фильтр по платформе"),
    status: schemas.CampaignStatus   = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db),
):
    return campaign_crud.get_campaigns(db, skip=skip, limit=limit, platform=platform, status=status)


@router.get(
    "/{campaign_id}",
    response_model=schemas.CampaignRead,
    summary="Получить кампанию по ID",
)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    campaign = campaign_crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Кампания с ID={campaign_id} не найдена")
    return campaign


@router.post(
    "/",
    response_model=schemas.CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую кампанию",
)
def create_campaign(
    payload: schemas.CampaignCreate,
    db: Session = Depends(get_db),
):
    try:
        return campaign_crud.create_campaign(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{campaign_id}",
    response_model=schemas.CampaignRead,
    summary="Обновить кампанию",
)
def update_campaign(
    campaign_id: int,
    payload: schemas.CampaignUpdate,
    db: Session = Depends(get_db),
):
    campaign = campaign_crud.update_campaign(db, campaign_id, payload)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Кампания с ID={campaign_id} не найдена")
    return campaign


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить кампанию",
)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    success = campaign_crud.delete_campaign(db, campaign_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Кампания с ID={campaign_id} не найдена")
    return None


@router.get(
    "/{campaign_id}/stats",
    response_model=schemas.CampaignStats,
    summary="Статистика по кампании",
)
def get_campaign_stats(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    try:
        stats = campaign_crud.get_statistics(db, campaign_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return stats


@router.get(
    "/search",
    response_model=List[schemas.CampaignRead],
    summary="Поиск кампаний по названию или аккаунту",
)
def search_campaigns(
    query: str = Query(..., min_length=1, description="Строка для поиска"),
    skip:  int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db),
):
    return campaign_crud.search_campaigns(db, query, skip=skip, limit=limit)