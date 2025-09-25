"""
Lead Service - CRM и управление лидами
"""
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import logging
from contextlib import asynccontextmanager
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums
class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class LeadSource(str, Enum):
    WEBSITE = "website"
    PHONE = "phone"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"

# Модели данных
class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    source: LeadSource
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    complex_interest: Optional[str] = None
    budget: Optional[float] = None

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[LeadStatus] = None
    source: Optional[LeadSource] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    complex_interest: Optional[str] = None
    budget: Optional[float] = None

class Lead(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    status: LeadStatus
    source: LeadSource
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    complex_interest: Optional[str] = None
    budget: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    last_contact: Optional[datetime] = None

class LeadList(BaseModel):
    leads: List[Lead]
    total: int
    page: int
    size: int

class LeadActivity(BaseModel):
    id: str
    lead_id: str
    type: str  # call, email, meeting, note
    description: str
    created_at: datetime
    created_by: int
    created_by_name: str

# In-memory хранилище (в production - база данных)
LEADS_DB = {}
LEAD_ACTIVITIES_DB = {}

# Моковые пользователи для assigned_to
USERS_MOCK = {
    1: "Admin User",
    2: "Seller User",
    3: "Manager User"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Lead Service...")
    yield
    logger.info("Shutting down Lead Service...")

app = FastAPI(
    title="Lead Service",
    description="Сервис управления лидами и CRM",
    version="1.0.0",
    lifespan=lifespan
)

# API Endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "lead-service"}

@app.get("/leads", response_model=LeadList)
async def get_leads(
    page: int = 1,
    size: int = 10,
    status: Optional[LeadStatus] = None,
    assigned_to: Optional[int] = None,
    source: Optional[LeadSource] = None,
    search: Optional[str] = None
):
    """Получение списка лидов с фильтрацией"""
    leads = list(LEADS_DB.values())
    
    # Фильтрация
    if status:
        leads = [lead for lead in leads if lead["status"] == status]
    
    if assigned_to:
        leads = [lead for lead in leads if lead["assigned_to"] == assigned_to]
    
    if source:
        leads = [lead for lead in leads if lead["source"] == source]
    
    # Поиск
    if search:
        search_lower = search.lower()
        leads = [
            lead for lead in leads
            if (search_lower in lead["first_name"].lower() or
                search_lower in lead["last_name"].lower() or
                search_lower in lead["phone"].lower() or
                (lead["email"] and search_lower in lead["email"].lower()))
        ]
    
    # Сортировка по дате создания (новые сначала)
    leads.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Пагинация
    total = len(leads)
    start = (page - 1) * size
    end = start + size
    paginated_leads = leads[start:end]
    
    # Формируем результат
    result_leads = []
    for lead in paginated_leads:
        assigned_to_name = USERS_MOCK.get(lead["assigned_to"]) if lead["assigned_to"] else None
        result_leads.append(Lead(
            id=lead["id"],
            first_name=lead["first_name"],
            last_name=lead["last_name"],
            phone=lead["phone"],
            email=lead["email"],
            status=lead["status"],
            source=lead["source"],
            notes=lead["notes"],
            assigned_to=lead["assigned_to"],
            assigned_to_name=assigned_to_name,
            complex_interest=lead["complex_interest"],
            budget=lead["budget"],
            created_at=lead["created_at"],
            updated_at=lead["updated_at"],
            last_contact=lead["last_contact"]
        ))
    
    return LeadList(
        leads=result_leads,
        total=total,
        page=page,
        size=size
    )

@app.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str):
    """Получение лида по ID"""
    lead = LEADS_DB.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    assigned_to_name = USERS_MOCK.get(lead["assigned_to"]) if lead["assigned_to"] else None
    return Lead(
        id=lead["id"],
        first_name=lead["first_name"],
        last_name=lead["last_name"],
        phone=lead["phone"],
        email=lead["email"],
        status=lead["status"],
        source=lead["source"],
        notes=lead["notes"],
        assigned_to=lead["assigned_to"],
        assigned_to_name=assigned_to_name,
        complex_interest=lead["complex_interest"],
        budget=lead["budget"],
        created_at=lead["created_at"],
        updated_at=lead["updated_at"],
        last_contact=lead["last_contact"]
    )

@app.post("/leads", response_model=Lead)
async def create_lead(lead_data: LeadCreate):
    """Создание нового лида"""
    lead_id = str(uuid.uuid4())
    now = datetime.now()
    
    new_lead = {
        "id": lead_id,
        "first_name": lead_data.first_name,
        "last_name": lead_data.last_name,
        "phone": lead_data.phone,
        "email": lead_data.email,
        "status": LeadStatus.NEW,
        "source": lead_data.source,
        "notes": lead_data.notes,
        "assigned_to": lead_data.assigned_to,
        "complex_interest": lead_data.complex_interest,
        "budget": lead_data.budget,
        "created_at": now,
        "updated_at": now,
        "last_contact": None
    }
    
    LEADS_DB[lead_id] = new_lead
    
    # Создаем активность
    activity_id = str(uuid.uuid4())
    activity = {
        "id": activity_id,
        "lead_id": lead_id,
        "type": "note",
        "description": "Lead created",
        "created_at": now,
        "created_by": lead_data.assigned_to or 1,
        "created_by_name": USERS_MOCK.get(lead_data.assigned_to or 1, "System")
    }
    LEAD_ACTIVITIES_DB[activity_id] = activity
    
    assigned_to_name = USERS_MOCK.get(lead_data.assigned_to) if lead_data.assigned_to else None
    return Lead(
        id=new_lead["id"],
        first_name=new_lead["first_name"],
        last_name=new_lead["last_name"],
        phone=new_lead["phone"],
        email=new_lead["email"],
        status=new_lead["status"],
        source=new_lead["source"],
        notes=new_lead["notes"],
        assigned_to=new_lead["assigned_to"],
        assigned_to_name=assigned_to_name,
        complex_interest=new_lead["complex_interest"],
        budget=new_lead["budget"],
        created_at=new_lead["created_at"],
        updated_at=new_lead["updated_at"],
        last_contact=new_lead["last_contact"]
    )

@app.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: LeadUpdate, updated_by: int = 1):
    """Обновление лида"""
    lead = LEADS_DB.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Обновляем поля
    changes = []
    if lead_data.first_name is not None and lead_data.first_name != lead["first_name"]:
        lead["first_name"] = lead_data.first_name
        changes.append(f"First name changed to {lead_data.first_name}")
    
    if lead_data.last_name is not None and lead_data.last_name != lead["last_name"]:
        lead["last_name"] = lead_data.last_name
        changes.append(f"Last name changed to {lead_data.last_name}")
    
    if lead_data.phone is not None and lead_data.phone != lead["phone"]:
        lead["phone"] = lead_data.phone
        changes.append(f"Phone changed to {lead_data.phone}")
    
    if lead_data.email is not None and lead_data.email != lead["email"]:
        lead["email"] = lead_data.email
        changes.append(f"Email changed to {lead_data.email}")
    
    if lead_data.status is not None and lead_data.status != lead["status"]:
        lead["status"] = lead_data.status
        changes.append(f"Status changed to {lead_data.status}")
    
    if lead_data.notes is not None and lead_data.notes != lead["notes"]:
        lead["notes"] = lead_data.notes
        changes.append("Notes updated")
    
    if lead_data.assigned_to is not None and lead_data.assigned_to != lead["assigned_to"]:
        lead["assigned_to"] = lead_data.assigned_to
        changes.append(f"Assigned to user {lead_data.assigned_to}")
    
    if lead_data.complex_interest is not None and lead_data.complex_interest != lead["complex_interest"]:
        lead["complex_interest"] = lead_data.complex_interest
        changes.append(f"Complex interest changed to {lead_data.complex_interest}")
    
    if lead_data.budget is not None and lead_data.budget != lead["budget"]:
        lead["budget"] = lead_data.budget
        changes.append(f"Budget changed to {lead_data.budget}")
    
    lead["updated_at"] = datetime.now()
    
    # Создаем активность для изменений
    if changes:
        activity_id = str(uuid.uuid4())
        activity = {
            "id": activity_id,
            "lead_id": lead_id,
            "type": "note",
            "description": f"Lead updated: {', '.join(changes)}",
            "created_at": datetime.now(),
            "created_by": updated_by,
            "created_by_name": USERS_MOCK.get(updated_by, "System")
        }
        LEAD_ACTIVITIES_DB[activity_id] = activity
    
    assigned_to_name = USERS_MOCK.get(lead["assigned_to"]) if lead["assigned_to"] else None
    return Lead(
        id=lead["id"],
        first_name=lead["first_name"],
        last_name=lead["last_name"],
        phone=lead["phone"],
        email=lead["email"],
        status=lead["status"],
        source=lead["source"],
        notes=lead["notes"],
        assigned_to=lead["assigned_to"],
        assigned_to_name=assigned_to_name,
        complex_interest=lead["complex_interest"],
        budget=lead["budget"],
        created_at=lead["created_at"],
        updated_at=lead["updated_at"],
        last_contact=lead["last_contact"]
    )

@app.get("/leads/{lead_id}/activities", response_model=List[LeadActivity])
async def get_lead_activities(lead_id: str):
    """Получение активностей лида"""
    activities = [
        activity for activity in LEAD_ACTIVITIES_DB.values()
        if activity["lead_id"] == lead_id
    ]
    
    # Сортировка по дате (новые сначала)
    activities.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [LeadActivity(**activity) for activity in activities]

@app.post("/leads/{lead_id}/activities")
async def add_lead_activity(
    lead_id: str,
    activity_type: str,
    description: str,
    created_by: int = 1
):
    """Добавление активности к лиду"""
    if lead_id not in LEADS_DB:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    activity_id = str(uuid.uuid4())
    activity = {
        "id": activity_id,
        "lead_id": lead_id,
        "type": activity_type,
        "description": description,
        "created_at": datetime.now(),
        "created_by": created_by,
        "created_by_name": USERS_MOCK.get(created_by, "System")
    }
    
    LEAD_ACTIVITIES_DB[activity_id] = activity
    
    # Обновляем last_contact у лида
    LEADS_DB[lead_id]["last_contact"] = datetime.now()
    LEADS_DB[lead_id]["updated_at"] = datetime.now()
    
    return LeadActivity(**activity)

@app.get("/leads/stats/summary")
async def get_leads_summary():
    """Получение статистики по лидам"""
    leads = list(LEADS_DB.values())
    
    total_leads = len(leads)
    new_leads = len([l for l in leads if l["status"] == LeadStatus.NEW])
    contacted_leads = len([l for l in leads if l["status"] == LeadStatus.CONTACTED])
    qualified_leads = len([l for l in leads if l["status"] == LeadStatus.QUALIFIED])
    closed_won = len([l for l in leads if l["status"] == LeadStatus.CLOSED_WON])
    closed_lost = len([l for l in leads if l["status"] == LeadStatus.CLOSED_LOST])
    
    # Статистика по источникам
    sources = {}
    for lead in leads:
        source = lead["source"]
        sources[source] = sources.get(source, 0) + 1
    
    return {
        "total_leads": total_leads,
        "status_breakdown": {
            "new": new_leads,
            "contacted": contacted_leads,
            "qualified": qualified_leads,
            "closed_won": closed_won,
            "closed_lost": closed_lost
        },
        "sources_breakdown": sources,
        "conversion_rate": (closed_won / total_leads * 100) if total_leads > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
