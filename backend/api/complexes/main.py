import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Body, Query, UploadFile, File, Form
from starlette.responses import FileResponse

from math import isfinite
from backend.core.google_sheets import get_price_data_for_sheet, get_shaxmatka_data, get_price_data_for_sheet_all

router = APIRouter(prefix='/api/complexes')


@router.get('/')
async def get_complexes():
    base_dir = os.path.join('static', 'Жилые_Комплексы')
    complexes = []

    # Сканируем папку "Жилые_Комплексы"
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path):
            render_path = os.path.join(folder_path, 'render')
            renders = []
            if os.path.exists(render_path):
                renders = [
                    f"/static/Жилые_Комплексы/{folder_name}/render/{file}"
                    for file in os.listdir(render_path)
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.svg'))
                ]
            # Добавляем данные о ЖК: первый рендер или заглушка
            complexes.append({
                "name": folder_name,
                "render": renders[0] if renders else "/static/images/default-placeholder.png"
            })

    # Логирование для каждой папки
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        print(f"Processing folder: {folder_name}")
        if os.path.isdir(folder_path):
            render_path = os.path.join(folder_path, 'render')
            print(f"Render path: {render_path}")
            if os.path.exists(render_path):
                print(f"Files in render path: {os.listdir(render_path)}")

    return {"status": "success", "complexes": complexes}


@router.get("/jk/{jk_name}")
async def get_jk_data(jk_name: str):
    shaxmatka_cache = await get_shaxmatka_data(jk_name)  # Получаем кэшированные данные шахматки

    # Проверяем, не вернулась ли ошибка
    if isinstance(shaxmatka_cache, dict) and "error" in shaxmatka_cache:
        print(f"Ошибка при чтении данных ЖК {jk_name}: {shaxmatka_cache['error']}")
        return {"status": "error", "message": f"Ошибка при чтении данных ЖК: {shaxmatka_cache['error']}"}

    shaxmatka_data = shaxmatka_cache
    render_folder = os.path.join('static', 'Жилые_Комплексы', jk_name, 'render')
    render_image = None

    if os.path.exists(render_folder):
        images = [
            f"/static/Жилые_Комплексы/{jk_name}/render/{img}"
            for img in os.listdir(render_folder)
            if img.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if images:
            render_image = images[1] if len(images) > 1 else images[0]

    sanitized_shaxmatka = []
    for row in shaxmatka_data:
        sanitized_row = []
        for item in row:
            if isinstance(item, float) and not isfinite(item):
                sanitized_row.append(None)
            else:
                sanitized_row.append(item)
        sanitized_shaxmatka.append(sanitized_row)
    shaxmatka_data = sanitized_shaxmatka
    return {"status": "success", "shaxmatka": shaxmatka_data, "render": render_image}


def extract_price_value(price_data, key: str) -> float:
    """
    Извлекает числовое значение цены из результата get_local_excel_data.
    Если price_data – список списков, находит строку, где первая колонка равна этажу,
    а затем по суффиксу (последняя часть ключа) выбирает нужный столбец.
    Маппинг: "100" -> 1, "70" -> 2, "50" -> 3, "30" -> 4.
    """
    try:
        components = key.split('_')
        if len(components) < 3:
            raise ValueError("Некорректный формат ключа")
        # Последние две части ключа: этаж и суффикс цены
        floor = float(components[-2])
        suffix = components[-1]
        column_index = {"100": 1, "70": 2, "50": 3, "30": 4}.get(suffix)
        if column_index is None:
            raise ValueError(f"Неизвестный суффикс: {suffix}")

        if isinstance(price_data, list):
            # Каждая строка должна иметь структуру: [этаж, цена_100, цена_70, цена_50, цена_30]
            for row in price_data:
                try:
                    if float(row[0]) == floor:
                        return float(row[column_index])
                except Exception as inner_e:
                    continue
            raise ValueError(f"Этаж {floor} не найден в данных")
        elif isinstance(price_data, dict):
            return float(next(iter(price_data.values())))
        else:
            return float(price_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка извлечения цены для ключа {key}: {e}")


@router.get("/plan-image")
async def get_plan_image(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize")
):
    """
    Возвращает изображение планировки, если оно существует.
    Параметры: jkName, blockName, apartmentSize.
    Если соответствующий графический файл (jpg, jpeg, png, svg) не найден,
    происходит попытка открыть PDF-файл (например, {blockName}.pdf),
    перебираются страницы, и если на странице найден указанный apartmentSize,
    эта страница рендерится и возвращается в виде изображения.
    """
    if not all([jkName, blockName, apartmentSize]):
        raise HTTPException(status_code=400, detail="Отсутствуют обязательные параметры")

    # Путь к директории с планировками
    base_path = os.path.join('static', 'Жилые_Комплексы', jkName, 'Planirovki')
    print(f"Looking for plans in: {base_path}")

    # if not os.path.exists(base_path):
    #     raise HTTPException(status_code=404, detail="Планировки для указанного ЖК не найдены")

    # Сначала пытаемся найти графический файл с именем apartmentSize.xxx
    possible_files = [f"{apartmentSize}.{ext}" for ext in ['jpg', 'jpeg', 'png', 'svg']]
    for file_name in possible_files:
        file_path = os.path.join(base_path, file_name)
        if os.path.exists(file_path):
            return FileResponse(file_path)

    # Если графического файла нет, пытаемся найти PDF-файл
    # Предположим, что PDF-файл называется по имени блока, например: "Блок 1.pdf"
    pdf_file_path = os.path.join(base_path, f"{blockName}.pdf")
    print(pdf_file_path)
    if os.path.exists(pdf_file_path):
        try:
            doc = fitz.open(pdf_file_path)
            for page in doc:
                text = page.get_text()
                # Если на странице содержится искомый apartmentSize, считаем, что это нужная страница
                if apartmentSize in text:
                    pix = page.get_pixmap()
                    # Сохраняем изображение страницы во временный файл
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                        pix.save(tmp_file.name)
                        tmp_file_path = tmp_file.name
                    doc.close()
                    return FileResponse(tmp_file_path, media_type="image/png")
            doc.close()
            raise HTTPException(status_code=404, detail="Файл планировки не найден в PDF")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при обработке PDF: {e}")

    raise HTTPException(status_code=404, detail="Файл планировки не найден")



def _natural_key(path: str) -> List[Any]:
    name = os.path.basename(path)
    return [int(fragment) if fragment.isdigit() else fragment.lower() for fragment in re.split(r'(\d+)', name)]


def _sanitize_token(value: str) -> List[str]:
    """Возвращает набор безопасных вариантов записи для имени файла."""
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
    """Возвращает изображение плана этажа для указанного ЖК."""
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

    candidates = []

    def add_candidates(prefix: str):
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
async def get_blocks(jk_name: str):
    """
    Возвращает список блоков для заданного ЖК.
    """
    try:
        shaxmatka_data = await get_shaxmatka_data(jk_name)
        
        # Извлекаем уникальные блоки из данных шахматки
        blocks = set()
        for row in shaxmatka_data:
            if len(row) > 0 and row[0]:  # Первая колонка содержит название блока
                block_name = str(row[0]).strip()
                if block_name and block_name != 'None':
                    blocks.add(block_name)
        
        blocks_list = sorted(list(blocks))
        return {"status": "success", "blocks": blocks_list}
        
    except Exception as e:
        print(f"Ошибка при получении блоков для {jk_name}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/apartment-info")
async def get_apartment_info(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize"),
        floor: str = Query(..., alias="floor"),
        apartmentNumber: str = Query(..., alias="apartmentNumber")
):
    """
    Возвращает информацию о квартире (статус, цены, площадь, кол-во месяцев до конца периода и т.д.).
    Параметры: jkName, blockName, apartmentSize, floor, apartmentNumber
    """
    print(
        f"Запрос к /api/apartment-info: jk_name={jkName}, block_name={blockName}, "
        f"apartment_size={apartmentSize}, floor={floor}, apartment_number={apartmentNumber}"
    )

    if not all([jkName, blockName, apartmentSize, floor, apartmentNumber]):
        return {"status": "error", "message": "Отсутствуют обязательные параметры"}

    try:
        shaxmatka_data = await get_shaxmatka_data(jkName)
        if not shaxmatka_data:
            print(f"Данные для ЖК {jkName} не найдены в кэше.")
            return {"status": "error", "message": f"Данные для ЖК {jkName} не найдены."}
        
        # Проверяем, не вернулась ли ошибка
        if isinstance(shaxmatka_data, dict) and "error" in shaxmatka_data:
            print(f"Ошибка при чтении данных ЖК {jkName}: {shaxmatka_data['error']}")
            return {"status": "error", "message": f"Ошибка при чтении данных ЖК: {shaxmatka_data['error']}"}

        apartment_status = None
        for row in shaxmatka_data:
            try:
                row_block = row[0].strip().lower() if isinstance(row[0], str) else str(row[0]).lower()
                row_floor = int(row[6]) if row[6] else None
                row_size = float(row[5]) if row[5] else None
                row_apartment_number = str(row[4]) if row[4] else None

                # Добавляем допуск на размер квартиры (0.1 м²)
                size_match = abs(row_size - float(apartmentSize.replace(',', '.'))) < 0.1

                if (
                        row_block == blockName.lower() and
                        row_floor == int(floor) and
                        size_match and
                        row_apartment_number == apartmentNumber
                ):
                    apartment_status = row[2]  # статус квартиры
                    break
            except (ValueError, IndexError) as e:
                print(f"Ошибка обработки строки {row}: {e}")
                continue

        if not apartment_status:
            print("Параметры поиска не совпадают ни с одной строкой.")
            for row in shaxmatka_data:
                print(f"Строка: {row}")
            return {"status": "error", "message": "Квартира не найдена."}

        # Получаем цены из price_cache
        price_keys = {
            "100": f"{jkName}_{floor}_100",
            "70": f"{jkName}_{floor}_70",
            "50": f"{jkName}_{floor}_50",
            "30": f"{jkName}_{floor}_30"
        }

        prices = {}
        for suffix, key in price_keys.items():
            price_data = await get_price_data_for_sheet(key)
            prices[suffix] = extract_price_value(price_data, key)

        if any(price is None for price in prices.values()):
            raise HTTPException(status_code=404,
                                detail="Не найдены цены для некоторых вариантов оплаты. Проверьте кэш.")

        try:
            size = float(apartmentSize.replace(',', '.'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат размера квартиры")

        total_price = size * prices["30"]
        print(f"price_30={prices['30']}, calculated total_price={total_price}")

        # Вычисляем оставшиеся месяцы (например, до 30 июня 2027)
        if jkName == "ЖК_Бахор":
            start_date = datetime(2025, 7, 1)
            end_date = start_date + relativedelta(months=22)

        else:
            start_date = datetime(2025, 8, 1)
            end_date = start_date + relativedelta(months=23)

        # Текущая дата (сегодня)
        today = datetime.today()

        # Считаем разницу в месяцах
        diff_years = end_date.year - today.year
        diff_months = end_date.month - today.month
        total_months_left = diff_years * 12 + diff_months

        # Если день уже прошел текущий месяц, уменьшаем на 1
        if today.day > 1:
            total_months_left -= 1

        # Не допускаем отрицательных значений
        total_months_left = max(total_months_left, 0)
        return {
            "status": "success",
            "data": {
                "pricePerM2_100": round(prices["100"]),
                "pricePerM2_70": round(prices["70"]),
                "pricePerM2_50": round(prices["50"]),
                "pricePerM2_30": round(prices["30"]),
                "total_price": round(total_price),
                "status": apartment_status,
                "floor": floor,
                "size": apartmentSize,
                "apartment_number": apartmentNumber,
                "months_left": total_months_left
            }
        }
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return {"status": "error", "message": str(e)}


STATIC_DIR = "static"
EXCEL_DIR = os.path.join(STATIC_DIR, "Жилые_Комплексы")
METADATA_FILE = os.path.join(EXCEL_DIR, "files.json")

# Создаем необходимые папки, если их нет
os.makedirs(EXCEL_DIR, exist_ok=True)
FILENAME_PREFIX = {
    "prices": "price_shaxamtka",
    "jk": "jk_data",
    "templates": "dogovor_shablon"
}


@router.post('/add-excel-files-api')
async def add_excel_files_api(
        file: UploadFile = File(...),
        category: str = Form(...)
):
    # Проверка поддерживаемых форматов
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат файла. Допустимые: .xlsx, .xls, .csv"
        )

    # Определяем префикс для имени файла по категории
    prefix = FILENAME_PREFIX.get(category.lower())
    if not prefix:
        raise HTTPException(status_code=400, detail="Неверная категория файла")

    file_ext = os.path.splitext(file.filename)[1]
    new_filename = f"{prefix}{file_ext}"
    file_path = os.path.join(EXCEL_DIR, new_filename)

    # Чтение существующих метаданных, если файл существует
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = []
    else:
        metadata = []

    # Проверка: если файл с таким именем уже загружен, возвращаем уведомление
    if any(entry['filename'] == new_filename for entry in metadata):
        raise HTTPException(status_code=400, detail="Файл уже добавлен")

    # Сохранение файла без генерации уникального имени
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")

    # Формирование записи метаданных
    metadata_entry = {
        "filename": new_filename,
        "original_filename": file.filename,
        "category": category.lower(),
        "size": os.path.getsize(file_path),
        "upload_time": datetime.utcnow().isoformat() + "Z"
    }

    # Добавление новой записи
    metadata.append(metadata_entry)

    # Сохранение обновленных метаданных
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении метаданных")

    return {"message": "Файл загружен успешно", "file": metadata_entry}


BASE_DIR = Path(__file__).parent.parent.parent.parent / "static" / "Жилые_Комплексы"
print(BASE_DIR)


@router.post("/add-complex")
async def add_complex(
        name: str = Form(...),
        jk_file: UploadFile = File(...),
        price_file: UploadFile = File(...),
        template_file: UploadFile = File(...)
):
    print(name)
    # 1. Валидация названия
    if not re.match(r"^ЖК_.+", name):
        raise HTTPException(400, detail='Название ЖК должно быть в формате "ЖК_Название"')

    # 2. Создаём папку комплекса
    complex_dir = BASE_DIR / name
    try:
        complex_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        raise HTTPException(500, detail="Не удалось создать папку для ЖК")

    # 3. Словарь «загруженный объект → нужное имя»
    rename_map = {
        jk_file: "jk_data.xlsx",
        price_file: "price_shaxamtka.xlsx",
        template_file: "contract_template.docx"
    }

    saved = []
    for upload, new_name in rename_map.items():
        # Проверка расширений
        ext = Path(upload.filename).suffix.lower()
        if new_name.endswith(".xlsx") and ext not in (".xlsx", ".xls", ".csv"):
            raise HTTPException(400, detail=f"Формат не подходит для {new_name}")
        if new_name.endswith(".docx") and ext not in (".docx", ".doc"):
            raise HTTPException(400, detail=f"Формат не подходит для {new_name}")

        dest = complex_dir / new_name
        try:
            with dest.open("wb") as buf:
                shutil.copyfileobj(upload.file, buf)
        except Exception:
            raise HTTPException(500, detail=f"Не удалось сохранить файл {new_name}")

        saved.append({"filename": new_name, "size": dest.stat().st_size})

    return {
        "message": "ЖК успешно добавлен",
        "complex_name": name,
        "saved_files": saved
    }
