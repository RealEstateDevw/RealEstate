"""
Complex Service - Управление жилыми комплексами и квартирами
"""
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from contextlib import asynccontextmanager
import json
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Модели данных
class Apartment(BaseModel):
    id: str
    complex_name: str
    block: str
    floor: int
    rooms: int
    area: float
    price: float
    status: str
    plan_image: Optional[str] = None

class Complex(BaseModel):
    id: str
    name: str
    description: str
    location: str
    image: str
    apartments: List[Apartment] = []

class ComplexList(BaseModel):
    complexes: List[Complex]

class ApartmentFilter(BaseModel):
    complex_name: Optional[str] = None
    block: Optional[str] = None
    rooms: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    status: Optional[str] = None

# In-memory хранилище (в production - база данных)
COMPLEXES_DB = {
    "rassvet": {
        "id": "rassvet",
        "name": "ЖК Рассвет",
        "description": "Современный жилой комплекс в центре города",
        "location": "Ташкент, Мирзо-Улугбекский район",
        "image": "/static/images/rassvet.jpg",
        "apartments": [
            {
                "id": "r_1_1",
                "complex_name": "ЖК Рассвет",
                "block": "Д",
                "floor": 1,
                "rooms": 1,
                "area": 45.5,
                "price": 45000,
                "status": "available",
                "plan_image": "/static/floorplans/1room.jpg"
            },
            {
                "id": "r_1_2",
                "complex_name": "ЖК Рассвет",
                "block": "Д",
                "floor": 1,
                "rooms": 2,
                "area": 65.2,
                "price": 65000,
                "status": "available",
                "plan_image": "/static/floorplans/2room.jpg"
            },
            {
                "id": "r_2_1",
                "complex_name": "ЖК Рассвет",
                "block": "Д",
                "floor": 2,
                "rooms": 3,
                "area": 85.7,
                "price": 85000,
                "status": "sold",
                "plan_image": "/static/floorplans/3room.jpg"
            }
        ]
    },
    "bahor": {
        "id": "bahor",
        "name": "ЖК Бахор",
        "description": "Элитный жилой комплекс с развитой инфраструктурой",
        "location": "Ташкент, Чиланзарский район",
        "image": "/static/images/bahor.jpg",
        "apartments": [
            {
                "id": "b_1_1",
                "complex_name": "ЖК Бахор",
                "block": "Блок 1,2",
                "floor": 1,
                "rooms": 1,
                "area": 50.0,
                "price": 50000,
                "status": "available",
                "plan_image": "/static/floorplans/1room.jpg"
            },
            {
                "id": "b_1_2",
                "complex_name": "ЖК Бахор",
                "block": "Блок 1,2",
                "floor": 1,
                "rooms": 2,
                "area": 70.0,
                "price": 70000,
                "status": "available",
                "plan_image": "/static/floorplans/2room.jpg"
            },
            {
                "id": "b_2_1",
                "complex_name": "ЖК Бахор",
                "block": "Блок 1,2",
                "floor": 2,
                "rooms": 4,
                "area": 120.0,
                "price": 120000,
                "status": "reserved",
                "plan_image": "/static/floorplans/4room.jpg"
            }
        ]
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Complex Service...")
    yield
    logger.info("Shutting down Complex Service...")

app = FastAPI(
    title="Complex Service",
    description="Сервис управления жилыми комплексами и квартирами",
    version="1.0.0",
    lifespan=lifespan
)

# API Endpoints
@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "complex-service"}

@app.get("/complexes", response_model=ComplexList)
async def get_complexes():
    """Получение списка всех жилых комплексов"""
    complexes = [Complex(**complex_data) for complex_data in COMPLEXES_DB.values()]
    return ComplexList(complexes=complexes)

@app.get("/complexes/{complex_id}", response_model=Complex)
async def get_complex(complex_id: str):
    """Получение информации о конкретном жилом комплексе"""
    complex_data = COMPLEXES_DB.get(complex_id)
    if not complex_data:
        raise HTTPException(status_code=404, detail="Complex not found")
    
    return Complex(**complex_data)

@app.get("/complexes/{complex_id}/apartments", response_model=List[Apartment])
async def get_complex_apartments(
    complex_id: str,
    block: Optional[str] = Query(None),
    rooms: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    status: Optional[str] = Query(None)
):
    """Получение квартир жилого комплекса с фильтрацией"""
    complex_data = COMPLEXES_DB.get(complex_id)
    if not complex_data:
        raise HTTPException(status_code=404, detail="Complex not found")
    
    apartments = [Apartment(**apt) for apt in complex_data["apartments"]]
    
    # Применяем фильтры
    filtered_apartments = apartments
    
    if block:
        filtered_apartments = [apt for apt in filtered_apartments if apt.block == block]
    
    if rooms:
        filtered_apartments = [apt for apt in filtered_apartments if apt.rooms == rooms]
    
    if min_price is not None:
        filtered_apartments = [apt for apt in filtered_apartments if apt.price >= min_price]
    
    if max_price is not None:
        filtered_apartments = [apt for apt in filtered_apartments if apt.price <= max_price]
    
    if status:
        filtered_apartments = [apt for apt in filtered_apartments if apt.status == status]
    
    return filtered_apartments

@app.get("/apartments/{apartment_id}", response_model=Apartment)
async def get_apartment(apartment_id: str):
    """Получение информации о конкретной квартире"""
    for complex_data in COMPLEXES_DB.values():
        for apt_data in complex_data["apartments"]:
            if apt_data["id"] == apartment_id:
                return Apartment(**apt_data)
    
    raise HTTPException(status_code=404, detail="Apartment not found")

@app.get("/complexes/{complex_id}/blocks")
async def get_complex_blocks(complex_id: str):
    """Получение списка блоков жилого комплекса"""
    complex_data = COMPLEXES_DB.get(complex_id)
    if not complex_data:
        raise HTTPException(status_code=404, detail="Complex not found")
    
    blocks = list(set(apt["block"] for apt in complex_data["apartments"]))
    return {"blocks": blocks}

@app.get("/complexes/{complex_id}/rooms")
async def get_available_rooms(complex_id: str):
    """Получение доступных типов квартир (по количеству комнат)"""
    complex_data = COMPLEXES_DB.get(complex_id)
    if not complex_data:
        raise HTTPException(status_code=404, detail="Complex not found")
    
    rooms = list(set(apt["rooms"] for apt in complex_data["apartments"]))
    rooms.sort()
    return {"rooms": rooms}

@app.put("/apartments/{apartment_id}/status")
async def update_apartment_status(
    apartment_id: str,
    status: str,
    user_id: Optional[int] = None
):
    """Обновление статуса квартиры"""
    for complex_id, complex_data in COMPLEXES_DB.items():
        for apt_data in complex_data["apartments"]:
            if apt_data["id"] == apartment_id:
                apt_data["status"] = status
                logger.info(f"Apartment {apartment_id} status updated to {status} by user {user_id}")
                return {"message": "Status updated successfully"}
    
    raise HTTPException(status_code=404, detail="Apartment not found")

@app.get("/search")
async def search_apartments(
    query: str = Query(..., description="Search query"),
    complex_id: Optional[str] = Query(None),
    rooms: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None)
):
    """Поиск квартир по различным критериям"""
    results = []
    
    for complex_id_key, complex_data in COMPLEXES_DB.items():
        if complex_id and complex_id_key != complex_id:
            continue
            
        for apt_data in complex_data["apartments"]:
            # Простой поиск по названию комплекса и блоку
            if (query.lower() in complex_data["name"].lower() or 
                query.lower() in apt_data["block"].lower()):
                
                apartment = Apartment(**apt_data)
                
                # Применяем дополнительные фильтры
                if rooms and apartment.rooms != rooms:
                    continue
                if min_price and apartment.price < min_price:
                    continue
                if max_price and apartment.price > max_price:
                    continue
                
                results.append(apartment)
    
    return {"results": results, "total": len(results)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
