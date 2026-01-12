"""Pydantic schemas for Mini App API."""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class InterestEventType(str, Enum):
    """Types of interest events."""
    PAYMENT_VIEW = "payment_view"
    MAP_VIEW = "map_view"


class LeadRequestType(str, Enum):
    """Types of lead requests from Mini App."""
    LEAVE_REQUEST = "leave_request"
    BOOK = "book"
    QUESTION = "question"


class LeadRequestStatus(str, Enum):
    """Status of lead request."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CONVERTED = "converted"


# =============================================================================
# USER SCHEMAS
# =============================================================================

class MiniAppUserInit(BaseModel):
    """Request to initialize Mini App user."""
    init_data: str = Field(..., description="Telegram initData string")
    start_param: Optional[str] = Field(None, description="PAYLOAD from deep link")


class MiniAppUserResponse(BaseModel):
    """Response with user data."""
    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    source_payload: str
    favorites_count: int = 0
    top_interest_apartment: Optional[dict] = None

    class Config:
        from_attributes = True


# =============================================================================
# VIEW SESSION SCHEMAS
# =============================================================================

class ViewSessionStart(BaseModel):
    """Start a new viewing session."""
    telegram_id: int
    complex_name: str
    block_name: str
    floor: int
    unit_number: str
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None


class ViewSessionStartResponse(BaseModel):
    """Response after starting a view session."""
    session_id: int
    score_id: int
    view_count: int


class ViewSessionHeartbeat(BaseModel):
    """Heartbeat during viewing session."""
    session_id: int
    telegram_id: int
    seconds_elapsed: int = Field(..., ge=0, le=30, description="Time since last heartbeat (max 30)")
    is_visible: bool = Field(..., description="Whether tab is visible")


class ViewSessionHeartbeatResponse(BaseModel):
    """Response to heartbeat."""
    session_id: int
    total_active_seconds: int
    time_score: int
    should_end: bool = Field(False, description="True if session should be ended (cap reached)")


class ViewSessionEnd(BaseModel):
    """End a viewing session."""
    session_id: int
    telegram_id: int


class ViewSessionEndResponse(BaseModel):
    """Response after ending session."""
    session_id: int
    total_score: int
    time_score: int
    total_time_seconds: int


# =============================================================================
# INTEREST EVENT SCHEMAS
# =============================================================================

class InterestEventRequest(BaseModel):
    """Record an interest event."""
    telegram_id: int
    complex_name: str
    block_name: str
    floor: int
    unit_number: str
    event_type: InterestEventType


class InterestEventResponse(BaseModel):
    """Response after recording interest event."""
    score_id: int
    event_type: str
    bonus_added: int
    total_score: int


# =============================================================================
# INTEREST SCORE SCHEMAS
# =============================================================================

class InterestScoreResponse(BaseModel):
    """Interest score for an apartment."""
    complex_name: str
    block_name: str
    floor: int
    unit_number: str
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    total_score: int
    view_count: int
    time_score: int
    favorites_bonus: int
    payment_view_bonus: int
    map_view_bonus: int
    last_viewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TopInterestsResponse(BaseModel):
    """List of top interest scores."""
    interests: List[InterestScoreResponse]
    total_count: int


# =============================================================================
# FAVORITES SCHEMAS
# =============================================================================

class FavoriteRequest(BaseModel):
    """Add apartment to favorites."""
    telegram_id: int
    complex_name: str
    block_name: str
    floor: int
    unit_number: str
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    price_snapshot: Optional[float] = None


class FavoriteResponse(BaseModel):
    """Response after adding/removing favorite."""
    success: bool
    is_favorite: bool
    total_score: int


# =============================================================================
# LEAD REQUEST SCHEMAS
# =============================================================================

class LeadRequestCreate(BaseModel):
    """Create a lead request from Mini App."""
    telegram_id: int
    request_type: LeadRequestType
    complex_name: Optional[str] = None
    block_name: Optional[str] = None
    floor: Optional[int] = None
    unit_number: Optional[str] = None
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    price_snapshot: Optional[float] = None
    payment_type_interest: Optional[str] = None


class LeadRequestResponse(BaseModel):
    """Response with lead request data."""
    id: int
    request_type: str
    status: str
    complex_name: Optional[str] = None
    block_name: Optional[str] = None
    floor: Optional[int] = None
    unit_number: Optional[str] = None
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    price_snapshot: Optional[float] = None
    interest_score: Optional[int] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadRequestConfirm(BaseModel):
    """Confirm or decline a lead request."""
    request_id: int
    confirmed: bool
