from typing import Optional, List

from pydantic import BaseModel

from backend.database.models import Lead, User


class SearchResultBase(BaseModel):
    id: int
    type: str  # 'lead' или 'user'
    name: str
    phone: Optional[str]
    email: Optional[str] = None
    region: Optional[str] = None

    class Config:
        orm_mode = True

class SearchResponse(BaseModel):
    results: List[SearchResultBase]
    total_count: int


def convert_lead_to_search_result(lead: Lead) -> SearchResultBase:
    return SearchResultBase(
        id=lead.id,
        type='lead',
        name=lead.full_name,
        phone=lead.phone,
        region=lead.region,
    )

def convert_user_to_search_result(user: User) -> SearchResultBase:
    return SearchResultBase(
        id=user.id,
        type='user',
        name=f"{user.first_name} {user.last_name}".strip(),
        phone=user.phone,
        email=user.email
    )

