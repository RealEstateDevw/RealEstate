# backend/api/campaigns/schemas.py

from datetime import date, datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, conint, confloat


class CampaignPlatform(str, Enum):
    instagram = "instagram"
    facebook = "facebook"
    telegram = "telegram"


class CampaignStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class CampaignBase(BaseModel):
    name: str = Field(..., title="Название кампании", max_length=200)
    platform: CampaignPlatform = Field(..., title="Платформа")
    account: str = Field(..., title="Аккаунт (например @Bahor.LC)", max_length=100)

    launch_date: date = Field(..., title="Дата запуска")
    end_date: date = Field(..., title="Дата окончания")

    planned_budget: confloat(ge=0) = Field(..., title="Планируемый бюджет, $")
    spent_budget: confloat(ge=0) = Field(..., title="Потрачено, $")

    views: conint(ge=0) = Field(..., title="Просмотры")
    clicks: conint(ge=0) = Field(..., title="Переходы")

    leads_total: conint(ge=0) = Field(..., title="Получено лидов")
    leads_active: conint(ge=0) = Field(..., title="Активных лидов")

    status: CampaignStatus = Field(
        default=CampaignStatus.active,
        title="Статус кампании"
    )

    class Config:
        use_enum_values = True
        orm_mode = True


class CampaignCreate(CampaignBase):
    """
    Все поля обязательны при создании.
    """
    pass


class CampaignUpdate(BaseModel):
    """
    При обновлении можно передавать любые поля необязательно.
    """
    name: Optional[str] = Field(None, title="Название кампании", max_length=200)
    platform: Optional[CampaignPlatform] = Field(None, title="Платформа")
    account: Optional[str] = Field(None, title="Аккаунт", max_length=100)

    launch_date: Optional[date] = Field(None, title="Дата запуска")
    end_date: Optional[date] = Field(None, title="Дата окончания")

    planned_budget: Optional[confloat(ge=0)] = Field(None, title="Планируемый бюджет, $")
    spent_budget: Optional[confloat(ge=0)] = Field(None, title="Потрачено, $")

    views: Optional[conint(ge=0)] = Field(None, title="Просмотры")
    clicks: Optional[conint(ge=0)] = Field(None, title="Переходы")

    leads_total: Optional[conint(ge=0)] = Field(None, title="Получено лидов")
    leads_active: Optional[conint(ge=0)] = Field(None, title="Активных лидов")

    status: Optional[CampaignStatus] = Field(None, title="Статус кампании")

    class Config:
        use_enum_values = True
        orm_mode = True


class CampaignRead(CampaignBase):
    """
    Схема, возвращаемая из CRUD (включает ID и таймстемпы).
    """
    id: int = Field(..., title="ID кампании")
    created_at: datetime = Field(..., title="Дата создания")
    updated_at: datetime = Field(..., title="Дата обновления")


class CampaignStats(BaseModel):
    budget_spent: float
    cost_per_deal: Union[float, None]
    success_rate: Union[float, None]
    date: date