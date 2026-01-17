"""Pydantic-схемы для маркетинговых кампаний.

Содержит схемы для:
- Создания и обновления кампаний
- Метрик и статистики
- Дашборда маркетинга
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class CampaignPlatform(str, Enum):
    """Платформы для рекламных кампаний."""
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TELEGRAM = "TELEGRAM"
    GOOGLE = "GOOGLE"
    TIKTOK = "TIKTOK"


class CampaignStatus(str, Enum):
    """Статусы рекламных кампаний."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class CampaignBase(BaseModel):
    """Базовая схема кампании."""
    name: str = Field(..., title="Название кампании", max_length=200)
    platform: CampaignPlatform = Field(..., title="Платформа")
    account: Optional[str] = Field(None, title="Аккаунт (например @Bahor.LC)", max_length=100)

    launch_date: date = Field(..., title="Дата запуска")
    end_date: Optional[date] = Field(None, title="Дата окончания")

    planned_budget: float = Field(0, ge=0, title="Планируемый бюджет, $")
    spent_budget: float = Field(0, ge=0, title="Потрачено, $")

    views: int = Field(0, ge=0, title="Просмотры")
    clicks: int = Field(0, ge=0, title="Переходы")

    status: CampaignStatus = Field(
        default=CampaignStatus.ACTIVE,
        title="Статус кампании"
    )

    # UTM-параметры
    utm_source: Optional[str] = Field(None, title="UTM Source (уникальный код)")
    utm_medium: Optional[str] = Field(None, title="UTM Medium (тип трафика)")
    utm_campaign: Optional[str] = Field(None, title="UTM Campaign (название)")
    target_url: Optional[str] = Field(None, title="Целевой URL")

    class Config:
        use_enum_values = True
        from_attributes = True


class CampaignCreate(BaseModel):
    """Схема для создания кампании."""
    name: str = Field(..., title="Название кампании", max_length=200)
    platform: CampaignPlatform = Field(..., title="Платформа")
    account: Optional[str] = Field(None, title="Аккаунт", max_length=100)

    launch_date: date = Field(..., title="Дата запуска")
    end_date: Optional[date] = Field(None, title="Дата окончания")

    planned_budget: float = Field(0, ge=0, title="Планируемый бюджет, $")
    spent_budget: float = Field(0, ge=0, title="Потрачено, $")

    views: int = Field(0, ge=0, title="Просмотры")
    clicks: int = Field(0, ge=0, title="Переходы")

    status: CampaignStatus = Field(
        default=CampaignStatus.ACTIVE,
        title="Статус кампании"
    )

    target_url: Optional[str] = Field(
        "https://t.me/bahor_lc_bot/app",
        title="Целевой URL"
    )

    class Config:
        use_enum_values = True


class CampaignUpdate(BaseModel):
    """Схема для частичного обновления кампании."""
    name: Optional[str] = Field(None, title="Название кампании", max_length=200)
    platform: Optional[CampaignPlatform] = Field(None, title="Платформа")
    account: Optional[str] = Field(None, title="Аккаунт", max_length=100)

    launch_date: Optional[date] = Field(None, title="Дата запуска")
    end_date: Optional[date] = Field(None, title="Дата окончания")

    planned_budget: Optional[float] = Field(None, ge=0, title="Планируемый бюджет, $")
    spent_budget: Optional[float] = Field(None, ge=0, title="Потрачено, $")

    views: Optional[int] = Field(None, ge=0, title="Просмотры")
    clicks: Optional[int] = Field(None, ge=0, title="Переходы")

    status: Optional[CampaignStatus] = Field(None, title="Статус кампании")
    target_url: Optional[str] = Field(None, title="Целевой URL")

    class Config:
        use_enum_values = True


class CampaignRead(CampaignBase):
    """Схема для чтения кампании (включает ID и таймстемпы)."""
    id: int = Field(..., title="ID кампании")
    utm_link: Optional[str] = Field(None, title="Сгенерированная UTM-ссылка")
    created_at: datetime = Field(..., title="Дата создания")
    updated_at: datetime = Field(..., title="Дата обновления")


class CampaignMetrics(BaseModel):
    """Полные метрики кампании."""
    campaign_id: int
    name: str
    platform: str
    status: str

    # Базовые метрики
    clicks: int = Field(0, title="Переходы")
    leads_count: int = Field(0, title="Количество лидов")
    deals_count: int = Field(0, title="Количество сделок")

    # Бюджет
    spent_budget: float = Field(0, title="Потрачено")
    planned_budget: float = Field(0, title="Планируемый бюджет")

    # Конверсии (%)
    cr_lead: float = Field(0, title="CR Lead (Лиды/Переходы)")
    cr_sale: float = Field(0, title="CR Sale (Сделки/Лиды)")
    cr_total: float = Field(0, title="CR Total (Сделки/Переходы)")

    # Стоимости
    cpa: float = Field(0, title="CPA (Стоимость лида)")
    cps: float = Field(0, title="CPS (Стоимость сделки)")
    cost_per_click: float = Field(0, title="Стоимость клика")

    # Статус здоровья
    health_status: str = Field("neutral", title="Статус здоровья кампании")

    # UTM
    utm_source: Optional[str] = None
    utm_link: Optional[str] = None


class DashboardStats(BaseModel):
    """Общая статистика маркетингового дашборда."""
    total_clicks: int = Field(0, title="Общее число переходов")
    total_leads: int = Field(0, title="Общее число лидов")
    total_deals: int = Field(0, title="Общее число сделок")
    total_spent: float = Field(0, title="Общий расход")
    active_campaigns: int = Field(0, title="Активных кампаний")
    campaigns: List[CampaignMetrics] = Field([], title="Список кампаний с метриками")


class TrackClickRequest(BaseModel):
    """Запрос на трекинг клика."""
    utm_source: str = Field(..., title="UTM Source код")


class TrackClickResponse(BaseModel):
    """Ответ на трекинг клика."""
    success: bool
    campaign_id: Optional[int] = None
    clicks: Optional[int] = None


class GenerateLinkResponse(BaseModel):
    """Ответ с сгенерированной UTM-ссылкой."""
    utm_source: str
    utm_link: str
    target_url: str