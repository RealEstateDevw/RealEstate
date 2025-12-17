from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Body, Query, UploadFile, File, Form, Depends
from starlette.responses import FileResponse

from math import isfinite
from sqlalchemy.orm import Session, joinedload
from fastapi_cache.decorator import cache

from backend.core.google_sheets import (
    get_price_data_for_sheet,
    get_shaxmatka_data,
    get_price_data_for_sheet_all,
)
from backend.core.excel_importer import (
    import_chess_from_excel,
    import_price_from_excel,
    import_contract_registry_from_excel,
)
from backend.database import get_db
from backend.database.models import ResidentialComplex, ContractRegistryEntry
from backend.core.cache_utils import invalidate_complex_cache
from backend.core.plan_cache import ensure_plan_image_cached

router = APIRouter(prefix='/api/complexes')

BASE_COMPLEX_STATIC = Path('static') / 'Жилые_Комплексы'
CACHE_TTL_SECONDS = 300  # 5 минут для админских endpoints
CACHE_TTL_LANDING_SECONDS = 3600  # 1 час для публичных landing pages


def _collect_render_paths(complex_name: str) -> List[str]:
    render_dir = BASE_COMPLEX_STATIC / complex_name / 'render'
    if not render_dir.exists() or not render_dir.is_dir():
        return []
    return [
        f"/static/Жилые_Комплексы/{complex_name}/render/{file.name}"
        for file in sorted(render_dir.iterdir())
        if file.is_file() and file.suffix.lower() in {'.png', '.jpg', '.jpeg', '.svg'}
    ]


def _sanitize_shaxmatka_rows(rows: Any) -> Tuple[List[List[Any]], List[str], List[int]]:
    sanitized: List[List[Any]] = []
    blocks: set[str] = set()
    floors: set[int] = set()

    if not isinstance(rows, list):
        return sanitized, [], []

    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        cleaned_row: List[Any] = []
        for item in row:
            if isinstance(item, float) and not isfinite(item):
                cleaned_row.append(None)
            else:
                cleaned_row.append(item)
        sanitized.append(cleaned_row)

        if len(cleaned_row) >= 1 and cleaned_row[0]:
            blocks.add(str(cleaned_row[0]).strip())
        if len(cleaned_row) >= 7 and cleaned_row[6] not in (None, ""):
            try:
                floors.add(int(float(str(cleaned_row[6]).replace(',', '.'))))
            except (ValueError, TypeError):
                continue

    return sanitized, sorted(blocks), sorted(floors)


_CYR_TO_LAT = {
    "А": "A", "а": "a",
    "В": "V", "в": "v",
    "С": "S", "с": "s",
    "Е": "E", "е": "e",
    "К": "K", "к": "k",
    "М": "M", "м": "m",
    "Н": "N", "н": "n",
    "О": "O", "о": "o",
    "Р": "R", "р": "r",
    "Т": "T", "т": "t",
    "Х": "H", "х": "h",
    "У": "U", "у": "u",
}


def _normalize_block_name(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)
    text = text.lower()
    return re.sub(r"[\s_–—\-]+", "-", text)


def _normalize_unit_number(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    cleaned = str(value).strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return None


def _build_registry_contracts(db: Session, complex_id: int) -> List[Dict[str, Any]]:
    entries = (
        db.query(ContractRegistryEntry)
        .filter(ContractRegistryEntry.complex_id == complex_id)
        .options(joinedload(ContractRegistryEntry.apartment))
        .all()
    )

    latest: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for entry in entries:
        extra = entry.extra_data or {}

        block_value = entry.block_name or extra.get("Блок")
        if not block_value and entry.apartment:
            block_value = entry.apartment.block_name

        floor_value = entry.floor
        if floor_value is None:
            floor_value = _coerce_int(extra.get("Этаж"))
        if floor_value is None and entry.apartment:
            floor_value = entry.apartment.floor

        apt_number = entry.apartment_number or extra.get("№ КВ")
        if not apt_number and entry.apartment:
            apt_number = entry.apartment.unit_number

        normalized_block = _normalize_block_name(block_value)
        normalized_number = _normalize_unit_number(apt_number)
        if not normalized_block or floor_value is None or not normalized_number:
            continue

        key = (normalized_block, str(floor_value), normalized_number)
        sort_key = (
            entry.contract_date or datetime.min.date(),
            entry.id or 0,
        )

        current = latest.get(key)
        if current and current["__sort"] >= sort_key:
            continue

        latest[key] = {
            "block": block_value,
            "blockNormalized": normalized_block,
            "floor": str(floor_value),
            "apartmentNumber": normalized_number,
            "contractNumber": entry.contract_number,
            "contractDate": entry.contract_date.isoformat() if entry.contract_date else None,
            "__sort": sort_key,
        }

    result: List[Dict[str, Any]] = []
    for payload in latest.values():
        payload.pop("__sort", None)
        result.append(payload)

    result.sort(key=lambda item: (item["blockNormalized"], item["floor"], item["apartmentNumber"]))
    return result


@router.get('/')
@cache(expire=CACHE_TTL_SECONDS, namespace="complexes:list")
async def get_complexes(db: Session = Depends(get_db)):
    complexes = (
        db.query(ResidentialComplex)
        .order_by(ResidentialComplex.name.asc())
        .all()
    )

    response: List[Dict[str, Any]] = []

    if not complexes and BASE_COMPLEX_STATIC.exists():
        for folder in sorted(p for p in BASE_COMPLEX_STATIC.iterdir() if p.is_dir()):
            renders = _collect_render_paths(folder.name)
            response.append({
                "name": folder.name,
                "slug": None,
                "render": renders[0] if renders else "/static/images/default-placeholder.png",
            })
        return {"status": "success", "complexes": response}

    for complex_obj in complexes:
        renders = _collect_render_paths(complex_obj.name)
        response.append({
            "id": complex_obj.id,
            "name": complex_obj.name,
            "slug": complex_obj.slug,
            "render": renders[0] if renders else "/static/images/default-placeholder.png",
        })

    return {"status": "success", "complexes": response}


@router.get("/jk/{jk_name}")
@cache(expire=CACHE_TTL_LANDING_SECONDS, namespace="complexes:jk")
async def get_jk_data(jk_name: str, db: Session = Depends(get_db)):
    try:
        shaxmatka_rows = await get_shaxmatka_data(jk_name)
    except HTTPException as exc:
        return {"status": "error", "message": exc.detail}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    if isinstance(shaxmatka_rows, dict) and "error" in shaxmatka_rows:
        return {"status": "error", "message": shaxmatka_rows["error"]}

    renders = _collect_render_paths(jk_name)
    sanitized, blocks, floors = _sanitize_shaxmatka_rows(shaxmatka_rows)
    registry_contracts: List[Dict[str, Any]] = []
    complex_record = (
        db.query(ResidentialComplex)
        .filter(ResidentialComplex.name == jk_name)
        .first()
    )
    if complex_record:
        registry_contracts = _build_registry_contracts(db, complex_record.id)
    return {
        "status": "success",
        "shaxmatka": sanitized,
        "blocks": blocks,
        "floors": floors,
        "render": renders[1] if len(renders) > 1 else (renders[0] if renders else None),
        "registryContracts": registry_contracts,
    }


@router.get("/aggregate", summary="Получить агрегированные данные по ЖК")
@cache(expire=CACHE_TTL_SECONDS, namespace="complexes:aggregate")
async def get_complexes_aggregate(db: Session = Depends(get_db)):
    complexes = (
        db.query(ResidentialComplex)
        .order_by(ResidentialComplex.name.asc())
        .all()
    )

    response: List[Dict[str, Any]] = []

    names: List[str]
    id_map: Dict[str, Optional[int]]

    if complexes:
        names = [c.name for c in complexes]
        id_map = {c.name: c.id for c in complexes}
    elif BASE_COMPLEX_STATIC.exists():
        names = [folder.name for folder in BASE_COMPLEX_STATIC.iterdir() if folder.is_dir()]
        id_map = {name: None for name in names}
    else:
        names = []
        id_map = {}

    for jk_name in sorted(names):
        try:
            shaxmatka_rows = await get_shaxmatka_data(jk_name)
        except Exception as exc:
            print(f"[aggregate] failed to load shaxmatka for {jk_name}: {exc}")
            shaxmatka_rows = []

        sanitized, blocks, floors = _sanitize_shaxmatka_rows(shaxmatka_rows)
        renders = _collect_render_paths(jk_name)

        response.append({
            "id": id_map.get(jk_name),
            "name": jk_name,
            "slug": None,
            "render": renders[0] if renders else "/static/images/default-placeholder.png",
            "renders": renders,
            "blocks": blocks,
            "floors": floors,
            "shaxmatka": sanitized,
        })

    return {
        "status": "success",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "complexes": response,
    }


def extract_price_value(price_data: Any, key: str) -> Optional[float]:
    try:
        components = key.split('_')
        if len(components) < 3:
            return None
        floor = float(components[-2])
        suffix = components[-1]
        column_index = {"100": 1, "0.7": 2, "0.5": 3, "0.3": 4, "70": 2, "50": 3, "30": 4}.get(suffix)
        if column_index is None:
            return None

        if isinstance(price_data, list):
            for row in price_data:
                try:
                    if float(row[0]) == floor:
                        return float(row[column_index])
                except Exception:
                    continue
            return None
        elif isinstance(price_data, dict):
            try:
                return float(next(iter(price_data.values())))
            except Exception:
                return None
        else:
            return float(price_data)
    except Exception as exc:
        print(f"Ошибка извлечения цены для ключа {key}: {exc}")
        return None


@router.get("/plan-image")
async def get_plan_image(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize")
):
    if not all([jkName, blockName, apartmentSize]):
        raise HTTPException(status_code=400, detail="Отсутствуют обязательные параметры")

    try:
        cached_path = ensure_plan_image_cached(jkName, blockName, apartmentSize)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл планировки не найден")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось подготовить план: {exc}") from exc

    return FileResponse(cached_path)


# (floor-plan endpoint, add-complex, etc., would continue below with DB/caching logic)

def _natural_key(path: str) -> List[Any]:
    name = os.path.basename(path)
    return [int(fragment) if fragment.isdigit() else fragment.lower() for fragment in re.split(r'(\d+)', name)]


def _sanitize_token(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    token = str(value).strip()
    if not token:
        return []
    variants = {
        token,
        token.lower(),
        token.upper(),
        token.replace(' ', '_'),
        token.replace(' ', ''),
        token.replace('-', '_'),
        token.replace('-', ''),
        token.replace(',', '.'),
        token.replace(',', '_'),
        token.replace('.', '_'),
        token.replace('.', ''),
    }
    try:
        numeric = int(float(token.replace(',', '.')))
        variants.update({str(numeric), f"{numeric:02d}"})
    except ValueError:
        pass
    return list(variants)


@router.get("/floor-plan")
async def get_floor_plan(
        jkName: str = Query(..., alias="jkName"),
        floor: str = Query(..., alias="floor"),
        blockName: Optional[str] = Query(None, alias="blockName")
):
    if not jkName or not floor:
        raise HTTPException(status_code=400, detail="Параметры jkName и floor обязательны")

    base_dir = os.path.join('static', 'Жилые_Комплексы', jkName)
    if not os.path.isdir(base_dir):
        raise HTTPException(status_code=404, detail=f"ЖК {jkName} не найден")

    pdf_candidates = [
        os.path.join(base_dir, name)
        for name in ("plan_roof.pdf", "Plan pradaja.pdf")
        if os.path.exists(os.path.join(base_dir, name))
    ]
    PDF_PAGE_OVERRIDES: Dict[str, int] = {
        "ЖК_Рассвет": 1,
    }

    pdf_plan_path = pdf_candidates[0] if pdf_candidates else None

    try:
        floor_number = int(float(str(floor).replace(',', '.')))
    except ValueError:
        floor_number = None

    unique_floors: List[int] = []
    try:
        shaxmatka_data = await get_shaxmatka_data(jkName)
    except Exception as exc:
        print(f"[floor-plan] failed to load shaxmatka for {jkName}: {exc}")
        shaxmatka_data = None

    if shaxmatka_data:
        seen = set()
        for row in shaxmatka_data:
            if len(row) < 7:
                continue
            val = row[6]
            if val in (None, ''):
                continue
            try:
                num = int(float(str(val).replace(',', '.')))
            except (ValueError, TypeError):
                continue
            if num not in seen:
                unique_floors.append(num)
                seen.add(num)

    def fallback_index(page_count: int) -> int:
        if page_count <= 0:
            return 0
        if floor_number is None:
            return 0
        override = PDF_PAGE_OVERRIDES.get(jkName)
        if override is not None:
            adjusted = override + max(0, floor_number - 1)
            return max(0, min(adjusted, page_count - 1))
        if unique_floors:
            floors_sorted = sorted(unique_floors)
            min_floor = floors_sorted[0]
            max_floor = floors_sorted[-1]

            ordered_sequences: List[List[int]] = []
            if (max_floor - floor_number) <= (floor_number - min_floor):
                ordered_sequences.append(sorted(unique_floors, reverse=True))
                ordered_sequences.append(sorted(unique_floors))
            else:
                ordered_sequences.append(sorted(unique_floors))
                ordered_sequences.append(sorted(unique_floors, reverse=True))
            ordered_sequences.append(unique_floors)

            seen_sequences = set()
            for seq in ordered_sequences:
                key = tuple(seq)
                if not seq or key in seen_sequences:
                    continue
                seen_sequences.add(key)
                try:
                    idx = seq.index(floor_number)
                    return max(0, min(idx, page_count - 1))
                except ValueError:
                    continue
        return max(0, min(floor_number - 1, page_count - 1))

    def find_pdf_page_index(doc: fitz.Document) -> Optional[int]:
        if floor_number is None:
            return None
        override = PDF_PAGE_OVERRIDES.get(jkName)
        if override is not None:
            return max(0, min(override + max(0, floor_number - 1), doc.page_count - 1))
        tokens = {
            str(floor_number),
            f"{floor_number:02d}",
            str(floor_number).replace('.', ','),
            str(floor_number).replace('.', ' ')
        }
        for idx, page in enumerate(doc):
            text = page.get_text() or ''
            normalized = re.sub(r'\s+', '', text.lower())
            for token in tokens:
                if f"этаж{token}" in normalized or f"floor{token}" in normalized:
                    return idx
        return None

    precomputed_dir = os.path.join('static', 'floorplans', jkName)
    if os.path.isdir(precomputed_dir):
        png_files = sorted(
            [
                os.path.join(precomputed_dir, name)
                for name in os.listdir(precomputed_dir)
                if name.lower().endswith('.png')
            ],
            key=_natural_key
        )

        if png_files:
            page_index = None
            doc = None
            if pdf_plan_path:
                try:
                    doc = fitz.open(pdf_plan_path)
                    page_index = find_pdf_page_index(doc)
                except Exception as exc:
                    print(f"[floor-plan] failed to analyse PDF {pdf_plan_path}: {exc}")
                finally:
                    if doc:
                        doc.close()
            if page_index is None:
                page_index = fallback_index(len(png_files))
            page_index = max(0, min(page_index, len(png_files) - 1))
            return FileResponse(png_files[page_index])

    floor_tokens = _sanitize_token(floor)
    block_tokens = _sanitize_token(blockName) if blockName else []

    candidates: List[str] = []

    def add_candidates(prefix: str) -> None:
        for ext in ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.pdf'):
            candidates.append(os.path.join(base_dir, prefix + ext))

    if block_tokens:
        for block_token in block_tokens:
            for floor_token in floor_tokens:
                add_candidates(f"plan_{block_token}_{floor_token}")
                add_candidates(f"plan_{floor_token}_{block_token}")

    for floor_token in floor_tokens:
        add_candidates(f"plan_{floor_token}")
        add_candidates(f"floor_{floor_token}")

    add_candidates('plan')
    add_candidates('floorplan')
    add_candidates('plan_roof')

    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if not os.path.exists(path):
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext == '.pdf':
            try:
                doc = fitz.open(path)
                page_index = find_pdf_page_index(doc)
                if page_index is None:
                    page_index = fallback_index(doc.page_count)
                page_index = max(0, min(page_index, doc.page_count - 1))
                page = doc.load_page(page_index)
                pix = page.get_pixmap()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                    pix.save(tmp_file.name)
                    tmp_path = tmp_file.name
                doc.close()
                return FileResponse(tmp_path, media_type="image/png")
            except Exception as exc:
                print(f"[floor-plan] Ошибка обработки PDF {path}: {exc}")
                continue
        else:
            return FileResponse(path)

    raise HTTPException(status_code=404, detail="План этажа не найден")


@router.get("/blocks/{jk_name}")
@cache(expire=CACHE_TTL_SECONDS, namespace="complexes:blocks")
async def get_blocks(jk_name: str):
    try:
        shaxmatka_rows = await get_shaxmatka_data(jk_name)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    sanitized, blocks, _ = _sanitize_shaxmatka_rows(shaxmatka_rows)
    return {"status": "success", "blocks": blocks}


@router.get("/apartment-info")
@cache(expire=CACHE_TTL_LANDING_SECONDS, namespace="complexes:apartment-info")
async def get_apartment_info(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize"),
        floor: str = Query(..., alias="floor"),
        apartmentNumber: str = Query(..., alias="apartmentNumber"),
        db: Session = Depends(get_db)
):
    print(
        f"Запрос к /api/apartment-info: jk_name={jkName}, block_name={blockName}, "
        f"apartment_size={apartmentSize}, floor={floor}, apartment_number={apartmentNumber}"
    )

    if not all([jkName, blockName, apartmentSize, floor, apartmentNumber]):
        return {"status": "error", "message": "Отсутствуют обязательные параметры"}

    try:
        shaxmatka_rows = await get_shaxmatka_data(jkName)
        if isinstance(shaxmatka_rows, dict) and "error" in shaxmatka_rows:
            return {"status": "error", "message": shaxmatka_rows["error"]}
        sanitized_rows, _, _ = _sanitize_shaxmatka_rows(shaxmatka_rows)
    except HTTPException as e:
        return {"status": "error", "message": e.detail}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    target_status = None
    target_rooms = None
    target_unit_type = None
    normalized_block = blockName.strip().lower()
    target_floor = int(float(str(floor).replace(',', '.')))
    target_size = float(str(apartmentSize).replace(',', '.'))
    target_number = str(apartmentNumber).strip()

    for row in sanitized_rows:
        if len(row) < 7:
            continue
        row_block = str(row[0]).strip().lower()
        try:
            row_floor = int(float(str(row[6]).replace(',', '.')))
            row_size = float(str(row[5]).replace(',', '.'))
        except (ValueError, TypeError):
            continue
        row_number = str(row[4]).strip() if row[4] is not None else ""

        if (
            row_block == normalized_block and
            row_floor == target_floor and
            abs(row_size - target_size) <= 0.15 and
            row_number == target_number
        ):
            target_status = row[2]
            # Извлекаем тип помещения из row[1]
            # По структуре данных: row[0]=block, row[1]=unit_type, row[2]=status, row[3]=rooms, row[4]=number, row[5]=size, row[6]=floor
            if len(row) > 1:
                target_unit_type = row[1] if row[1] is not None else None
            # Извлекаем количество комнат из row[3]
            if len(row) > 3:
                rooms_value = row[3]
                if rooms_value is not None:
                    try:
                        # Пытаемся преобразовать в int, если это число
                        target_rooms = int(float(str(rooms_value).replace(',', '.')))
                    except (ValueError, TypeError):
                        # Если не число, оставляем как есть
                        target_rooms = rooms_value
                else:
                    target_rooms = None
            else:
                target_rooms = None
            print(f"[apartment-info] Найдена квартира: rooms={target_rooms}, unit_type={target_unit_type}, row={row}")
            break

    if target_status is None:
        return {"status": "error", "message": "Квартира не найдена"}

    try:
        # Получаем настройки рассрочки из базы данных
        complex_record = (
            db.query(ResidentialComplex)
            .filter(ResidentialComplex.name == jkName)
            .first()
        )

        if complex_record and complex_record.installment_start_date:
            from datetime import datetime as dt
            start_date = dt.combine(complex_record.installment_start_date, dt.min.time())
            installment_months = complex_record.installment_months
        else:
            # Значения по умолчанию, если не найдено в БД
            start_date = datetime(2025, 12, 1)
            installment_months = 36

        end_date = start_date + relativedelta(months=installment_months)

        today = datetime.today()
        diff_years = end_date.year - today.year
        diff_months = end_date.month - today.month
        months_left = diff_years * 12 + diff_months
        if today.day > 1:
            months_left -= 1
        months_left = max(months_left, 0)
    except Exception as e:
        print(f"Ошибка при расчете месяцев до сдачи: {e}")
        months_left = 0

    price_keys = {
        "100": f"{jkName}_{floor}_100",
        "70": f"{jkName}_{floor}_0.7",
        "50": f"{jkName}_{floor}_0.5",
        "30": f"{jkName}_{floor}_0.3",
    }
    prices: Dict[str, Optional[float]] = {}
    for key, price_key in price_keys.items():
        try:
            price_data = await get_price_data_for_sheet(price_key)
            prices[key] = extract_price_value(price_data, price_key)
        except Exception as e:
            print(f"Ошибка при извлечении цены для ключа {price_key}: {e}")
            prices[key] = None

    total_price = None
    if prices.get("100"):
        total_price = prices["100"] * target_size

    response_data = {
        "pricePerM2_100": round(prices.get("100") or 0),
        "pricePerM2_70": round(prices.get("70") or 0),
        "pricePerM2_50": round(prices.get("50") or 0),
        "pricePerM2_30": round(prices.get("30") or 0),
        "total_price": round(total_price) if total_price else None,
        "status": target_status,
        "floor": floor,
        "size": apartmentSize,
        "apartment_number": apartmentNumber,
        "months_left": months_left,
        "roomsCount": target_rooms,  # Всегда включаем roomsCount в ответ
        "unitType": target_unit_type,  # Тип помещения (жилой/нежилой)
        "hybrid_installment_enabled": complex_record.hybrid_installment_enabled if complex_record else False,
        "installment_months": complex_record.installment_months if complex_record else 36,
    }
    
    return {
        "status": "success",
        "data": response_data
    }



def _slugify(name: str) -> Optional[str]:
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in name)
    slug = '-'.join(filter(None, slug.split('-')))
    return slug or None


@router.post("/add-complex")
async def add_complex(
        name: str = Form(...),
        jk_file: UploadFile = File(...),
        price_file: UploadFile = File(...),
        template_file: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    if not re.match(r"^ЖК_.+", name):
        raise HTTPException(status_code=400, detail='Название ЖК должно быть в формате "ЖК_Название"')

    existing = (
        db.query(ResidentialComplex)
        .filter(ResidentialComplex.name == name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="ЖК с таким названием уже существует")

    complex_record = ResidentialComplex(name=name, slug=_slugify(name))
    db.add(complex_record)
    db.flush()

    complex_dir = BASE_COMPLEX_STATIC / name
    try:
        complex_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать папку для ЖК") from exc

    rename_map = {
        jk_file: "jk_data.xlsx",
        price_file: "price_shaxamtka.xlsx",
        template_file: "contract_template.docx",
    }

    saved: List[Dict[str, Any]] = []
    for upload, new_name in rename_map.items():
        ext = Path(upload.filename).suffix.lower()
        if new_name.endswith(".xlsx") and ext not in (".xlsx", ".xls", ".csv"):
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Формат не подходит для {new_name}")
        if new_name.endswith(".docx") and ext not in (".docx", ".doc"):
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Формат не подходит для {new_name}")

        dest = complex_dir / new_name
        try:
            with dest.open("wb") as buf:
                shutil.copyfileobj(upload.file, buf)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл {new_name}") from exc

        saved.append({"filename": new_name, "size": dest.stat().st_size})

    try:
        apartments = import_chess_from_excel(db, complex_record, str(complex_dir / "jk_data.xlsx"))
        prices = import_price_from_excel(db, complex_record, str(complex_dir / "price_shaxamtka.xlsx"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта Excel данных: {exc}") from exc

    await invalidate_complex_cache()

    return {
        "message": "ЖК успешно добавлен",
        "complex_name": name,
        "saved_files": saved,
        "imported": {
            "apartments": apartments,
            "prices": prices,
        }
    }


@router.post("/clear-cache")
async def clear_cache():
    """Очистить кеш комплексов (для разработки)."""
    await invalidate_complex_cache()
    return {"status": "success", "message": "Кеш успешно очищен"}


@router.get("/installment-settings/{jk_name}")
async def get_installment_settings(jk_name: str, db: Session = Depends(get_db)):
    """Получить настройки рассрочки для жилого комплекса."""
    complex_record = (
        db.query(ResidentialComplex)
        .filter(ResidentialComplex.name == jk_name)
        .first()
    )

    if not complex_record:
        raise HTTPException(status_code=404, detail=f"Жилой комплекс {jk_name} не найден")

    return {
        "status": "success",
        "data": {
            "installment_months": complex_record.installment_months,
            "installment_start_date": complex_record.installment_start_date.isoformat() if complex_record.installment_start_date else None,
            "hybrid_installment_enabled": complex_record.hybrid_installment_enabled,
        }
    }


@router.put("/installment-settings/{jk_name}")
async def update_installment_settings(
    jk_name: str,
    installment_months: int = Body(...),
    installment_start_date: str = Body(...),
    hybrid_installment_enabled: bool = Body(...),
    db: Session = Depends(get_db),
):
    """Обновить настройки рассрочки для жилого комплекса."""
    complex_record = (
        db.query(ResidentialComplex)
        .filter(ResidentialComplex.name == jk_name)
        .first()
    )

    if not complex_record:
        raise HTTPException(status_code=404, detail=f"Жилой комплекс {jk_name} не найден")

    # Обновляем настройки
    complex_record.installment_months = installment_months

    # Парсим дату
    from datetime import datetime as dt
    try:
        parsed_date = dt.strptime(installment_start_date, "%Y-%m-%d").date()
        complex_record.installment_start_date = parsed_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")

    complex_record.hybrid_installment_enabled = hybrid_installment_enabled

    try:
        db.commit()
        db.refresh(complex_record)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")

    await invalidate_complex_cache()

    return {
        "status": "success",
        "message": "Настройки рассрочки успешно обновлены",
        "data": {
            "installment_months": complex_record.installment_months,
            "installment_start_date": complex_record.installment_start_date.isoformat(),
            "hybrid_installment_enabled": complex_record.hybrid_installment_enabled,
        }
    }
