from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.database.models import ResidentialComplex, ApartmentUnit, ChessboardPriceEntry


def _get_complex(session: Session, jk_name: str) -> ResidentialComplex:
    complex_obj = (
        session.query(ResidentialComplex)
        .filter(ResidentialComplex.name == jk_name)
        .first()
    )
    if not complex_obj:
        raise HTTPException(status_code=404, detail=f"ЖК '{jk_name}' не найден")
    return complex_obj


def _collect_apartment_rows(apartments: List[ApartmentUnit]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for unit in apartments:
        payload = unit.raw_payload or {}
        rows.append([
            unit.block_name,
            unit.unit_type,
            unit.status,
            unit.rooms,
            payload.get("номер помещение ") or payload.get("номер помещение" ) or unit.unit_number,
            unit.area_sqm,
            unit.floor,
        ])
    return rows


def _ordered_price_categories(entries: List[ChessboardPriceEntry]) -> List[str]:
    seen: Dict[str, int] = {}
    for entry in entries:
        if entry.category_key not in seen:
            seen[entry.category_key] = entry.order_index
    return [key for key, _ in sorted(seen.items(), key=lambda item: (item[1], item[0]))]


def _build_price_matrix(entries: List[ChessboardPriceEntry]) -> List[List[Any]]:
    if not entries:
        return []

    categories = _ordered_price_categories(entries)
    floors: Dict[int, Dict[str, float]] = {}
    for entry in entries:
        floors.setdefault(int(entry.floor), {})[entry.category_key] = entry.price_per_sqm

    matrix: List[List[Any]] = []
    for floor in sorted(floors.keys(), reverse=True):
        row = [floor]
        for category in categories:
            row.append(floors[floor].get(category))
        matrix.append(row)
    return matrix


async def get_shaxmatka_data(jk_name: str) -> List[List[Any]]:
    session = SessionLocal()
    try:
        complex_obj = _get_complex(session, jk_name)
        apartments = (
            session.query(ApartmentUnit)
            .filter(ApartmentUnit.complex_id == complex_obj.id)
            .order_by(ApartmentUnit.block_name.asc(), ApartmentUnit.floor.asc(), ApartmentUnit.unit_number.asc())
            .all()
        )
        return _collect_apartment_rows(apartments)
    finally:
        session.close()


async def get_price_data_for_sheet(jk_floor_key: str) -> List[List[Any]]:
    components = jk_floor_key.split('_')
    if len(components) < 3:
        raise HTTPException(status_code=400, detail="Некорректный формат ключа")
    jk_name = '_'.join(components[:-2])

    session = SessionLocal()
    try:
        complex_obj = _get_complex(session, jk_name)
        entries = (
            session.query(ChessboardPriceEntry)
            .filter(ChessboardPriceEntry.complex_id == complex_obj.id)
            .all()
        )
        return _build_price_matrix(entries)
    finally:
        session.close()


async def get_price_data_for_sheet_all(sheet_name: str) -> List[List[Any]]:
    session = SessionLocal()
    try:
        complex_obj = _get_complex(session, sheet_name)
        entries = (
            session.query(ChessboardPriceEntry)
            .filter(ChessboardPriceEntry.complex_id == complex_obj.id)
            .all()
        )
        return _build_price_matrix(entries)
    finally:
        session.close()

