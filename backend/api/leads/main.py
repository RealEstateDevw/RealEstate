from fastapi import APIRouter, Query
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/api/leads")


# Модель ответа
class Lead(BaseModel):
    name: str
    role: str


# Пример данных (в реальном случае будет доступ к базе данных)
mock_leads = [
    {"name": "Мухаммедов Мухаммадамин", "role": "Лид"},
    {"name": "Абдурахмонов Джамшед", "role": "Лид"},
    {"name": "Олимов Олим", "role": "Лид"},
    {"name": "Зухриддинов Зухриддин", "role": "Лид"},
    {"name": "Камилов Камил", "role": "Лид"}
]


@router.get("/search", response_model=List[Lead])
async def search_leads(query: str = Query(...)):
    # Фильтруем лидов, проверяя наличие запроса в имени
    results = [lead for lead in mock_leads if query.lower() in lead["name"].lower()]
    return results
