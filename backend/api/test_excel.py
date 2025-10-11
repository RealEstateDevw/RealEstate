from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Union, Dict, List, Any, Optional
from dateutil.relativedelta import relativedelta
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from fastapi import APIRouter, HTTPException, Body, Query, Path, Depends
from fastapi import Form, UploadFile, File
import shutil
from num2words import num2words
from openpyxl.workbook import Workbook
from pydantic import BaseModel, Field
import openpyxl
import os
import traceback  # Для логирования ошибок

from starlette.responses import StreamingResponse, FileResponse
from urllib.parse import quote

from pdf2image import convert_from_path
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database.models import (
    ResidentialComplex,
    ApartmentUnit,
    ChessboardPriceEntry,
    ContractRegistryEntry,
    Lead,
)
from backend.api.leads.schemas import LeadState
from backend.core.cache_utils import invalidate_complex_cache
from backend.core.excel_importer import (
    import_chess_from_excel,
    import_price_from_excel,
    import_contract_registry_from_excel,
)

# --- Вспомогательные функции ---
def col_letter_to_index(letter: str) -> int:
    """
    Преобразует буквенное обозначение столбца в индекс, используемый openpyxl (1-индексация).
    Например: 'A' -> 1, 'G' -> 7.
    """
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index  # openpyxl использует 1-based index


# --- Конфигурация ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# === НОВАЯ КОНФИГУРАЦИЯ СТОЛБЦОВ ===
COLUMN_MAPPING = {
    "blockName": 'A',  # Столбец 'A' для Блока
    "status": 'C',  # Столбец 'C' для Статуса (для обновления)
    "apartmentNumber": 'E',  # Столбец 'E' для Номера квартиры
    "floor": 'G'  # Столбец 'G' для Этажа
}
DATA_START_ROW = 2  # Строка, с которой начинаются данные (1-based)


# === КОНЕЦ НОВОЙ КОНФИГУРАЦИИ ===

# --- Модель запроса (остается без изменений) ---
class ApartmentStatusUpdate(BaseModel):
    jkName: str
    blockName: str
    floor: int
    apartmentNumber: Union[int, str]  # Номер квартиры может быть числом в JSON
    newStatus: str = Field(default="бронь")


class ContractData(BaseModel):
    jkName: str
    contractNumber: Union[str, None] = None
    contractDate: str
    leadId: Optional[int] = None
    fullName: str
    passportSeries: str
    issuedBy: str
    registrationAddress: str
    phone: str
    pinfl: str
    block: str
    floor: int
    apartmentNumber: int
    rooms: int
    size: float
    totalPrice: str
    pricePerM2: str
    paymentChoice: str
    initialPayment: str
    monthlyPayment: Optional[str] = None
    finalPayment: Optional[str] = None
    salesDepartment: Union[str, None] = None
    unitType: Optional[str] = Field(default="residential",
                                    description="Тип помещения: 'residential' (жилой) или 'nonresidential' (нежилой)")


# Функция преобразования числа в слова (на русском языке)
def _number_to_words(number: str) -> str:
    # Убираем все нечисловые символы и преобразуем в int
    clean_number = ''.join(filter(str.isdigit, number))
    return num2words(int(clean_number), lang='ru') + " сум"


router = APIRouter(prefix="/excel", tags=["Excel Operations"])  # Пример префикса


def _get_db_complex(db: Session, jk_name: str) -> ResidentialComplex:
    complex_obj = (
        db.query(ResidentialComplex)
        .filter(ResidentialComplex.name == jk_name)
        .first()
    )
    if not complex_obj:
        raise HTTPException(status_code=404, detail=f"ЖК '{jk_name}' не найден")
    return complex_obj


def _clean_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = (
        str(value)
        .replace(" ", "")
        .replace("\xa0", "")
        .replace(",", ".")
        .strip()
    )
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


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
        except (ValueError, TypeError):
            return None
    cleaned = str(value).strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None

def _find_apartment_unit(
        db: Session,
        complex_id: int,
        block_name: Any,
        floor: Any,
        apartment_number: Any,
) -> Optional[ApartmentUnit]:
    normalized_number = _normalize_unit_number(apartment_number)
    floor_int = _coerce_int(floor)
    if not normalized_number or floor_int is None:
        return None

    candidates = (
        db.query(ApartmentUnit)
        .filter(
            ApartmentUnit.complex_id == complex_id,
            ApartmentUnit.floor == floor_int,
            ApartmentUnit.unit_number == normalized_number,
        )
        .all()
    )
    block_norm = _normalize_block_name(block_name)
    return next(
        (
            unit for unit in candidates
            if _normalize_block_name(unit.block_name) == block_norm
        ),
        None,
    )


def _render_numeric_like(value: Any) -> Any:
    if value is None:
        return None
    try:
        num = float(value)
        if num.is_integer():
            return int(num)
        return num
    except (ValueError, TypeError):
        return value


def _render_contract_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _extract_contract_sequence(value: Any) -> Optional[int]:
    if value is None:
        return None
    digits = re.findall(r"\d+", str(value))
    if not digits:
        return None
    try:
        return int(digits[-1])
    except ValueError:
        return None


# --- Обновленная логика работы со статусами квартир ---
def _update_apartment_status_db(db: Session, update_data: ApartmentStatusUpdate) -> bool:
    complex_obj = _get_db_complex(db, update_data.jkName)
    apartment = _find_apartment_unit(
        db,
        complex_obj.id,
        update_data.blockName,
        update_data.floor,
        update_data.apartmentNumber,
    )
    if not apartment:
        return False

    apartment.status = update_data.newStatus
    payload = dict(apartment.raw_payload or {})
    for key in list(payload.keys()):
        if isinstance(key, str) and "статус" in key.lower():
            payload[key] = update_data.newStatus
    apartment.raw_payload = payload or None
    return True


@router.post("/update-status")
async def update_excel_status_endpoint(
        update_data: ApartmentStatusUpdate = Body(...),
        db: Session = Depends(get_db),
):
    print(f"Запрос: {update_data.dict()}")
    updated = _update_apartment_status_db(db, update_data)
    if not updated:
        return {"status": "warning", "message": f"Квартира не найдена для '{update_data.jkName}'"}

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Не удалось обновить статус: {exc}") from exc

    await invalidate_complex_cache()
    return {"status": "success", "message": "Apartment status updated successfully"}


BASE_STATIC_PATH = "static/Жилые_Комплексы"


def parse_date(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.now()
    # Список поддерживаемых форматов
    date_formats = ["%d.%m.%Y", "%Y-%m-%d"]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # Если ни один формат не подошел, логируем ошибку и возвращаем текущую дату
    print(
        f"Ошибка: дата '{date_str}' не соответствует ни одному из форматов {date_formats}. Используется текущая дата.")
    return datetime.now()


@router.get("/last-contract-number")
async def get_last_contract_number(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    contract_numbers = (
        db.query(ContractRegistryEntry.contract_number)
        .filter(ContractRegistryEntry.complex_id == complex_obj.id)
        .all()
    )

    last_number = 0
    for (contract_number,) in contract_numbers:
        seq = _extract_contract_sequence(contract_number)
        if seq is not None and seq > last_number:
            last_number = seq

    return {"lastContractNumber": last_number + 1}


# --- Начало определения роутера и модели (пример) ---


# Примерная модель Pydantic, адаптируйте под вашу структуру


# Пример функции-хелпера
# def number_to_words(num_str: str) -> str:
#     # Замените на вашу реальную реализацию конвертации числа в текст
#     num_str_clean = num_str.replace(" ", "").replace(",", ".")
#     try:
#         num = float(num_str_clean)
#         return f"{num:.2f} (прописью)"  # Заглушка
#     except ValueError:
#         return "Некорректное число"


def clean_number(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned_value = value.replace(" ", "").replace("\xa0", "")
    try:
        return float(cleaned_value)
    except ValueError as e:
        print(f"Ошибка преобразования строки '{value}' в float: {e}")
        return 0.0


FLOORPLAN_IMAGES_DIR = os.path.join(BASE_DIR, "static", "floorplans")
FLOORPLAN_PDF_PATHS = {
    "ЖК_Бахор": os.path.join(BASE_STATIC_PATH, "ЖК_Бахор", "plan_roof.pdf"),
    "ЖК_Рассвет": os.path.join(BASE_STATIC_PATH, "ЖК_Рассвет", "plan_roof.pdf"),
}
FLOORPLAN_CROP_BOX = (529, 530, 960, 982)  # (left, upper, right, lower)


def convert_floorplan_pdf_to_images(jk_name: str, pdf_path: str, root_output_dir: str) -> List[str]:
    """Конвертирует PDF плана этажа в PNG и возвращает пути к обрезанным изображениям."""
    if not os.path.exists(pdf_path):
        print(f"[floorplan] PDF для {jk_name} не найден: {pdf_path}")
        return []

    output_dir = os.path.join(root_output_dir, jk_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Конвертируем PDF {pdf_path} для {jk_name} в директории {output_dir}")

    try:
        pil_images = convert_from_path(pdf_path, dpi=150)
    except Exception as exc:
        print(f"[floorplan] Ошибка конвертации PDF {pdf_path}: {exc}")
        return []

    saved_paths: List[str] = []
    for idx, image in enumerate(pil_images, start=1):
        cropped_img = image.crop(FLOORPLAN_CROP_BOX)
        cropped_fname = os.path.join(output_dir, f"floorplan_page_{idx}.png")
        cropped_img.save(cropped_fname, "PNG")
        print(f"Сохранён скропанный план этажа: {cropped_fname}")
        saved_paths.append(cropped_fname)

    return saved_paths


FLOORPLAN_IMAGES: Dict[str, List[str]] = {
    jk: convert_floorplan_pdf_to_images(jk, path, FLOORPLAN_IMAGES_DIR)
    for jk, path in FLOORPLAN_PDF_PATHS.items()
}


@router.post("/generate-contract")
async def generate_contract(
        data: ContractData,
        db: Session = Depends(get_db),
):
    """Генерация договора в формате DOCX (автоматический выбор шаблона: жилой/нежилой) и обновление реестра в XLSX (docxtpl)."""

    jk_dir = os.path.join(BASE_STATIC_PATH, data.jkName)
    TEMPLATE_PATH = os.path.join(jk_dir, "contract_template.docx")
    # Выбор шаблона: жилой/нежилой
    alt_template_path = os.path.join(jk_dir, "contract_template_empty.docx")
    unit_type_val = (data.unitType or "residential").strip().lower()
    # Поддерживаем русские и английские значения
    nonres_aliases = {"nonresidential", "non-residential", "commercial", "нежилой", "не жилой", "помещение", "нежилое"}
    if unit_type_val in nonres_aliases:
        TEMPLATE_PATH = alt_template_path

    os.makedirs(jk_dir, exist_ok=True)

    lead_obj = None
    if data.leadId is not None:
        lead_obj = db.query(Lead).filter(Lead.id == data.leadId).first()
        if not lead_obj:
            raise HTTPException(status_code=404, detail=f"Лид с ID {data.leadId} не найден")

    complex_obj = _get_db_complex(db, data.jkName)
    contract_number = data.contractNumber or _generate_contract_number(db, complex_obj)
    data.contractNumber = contract_number  # Сохраняем сгенерированный номер обратно в данные

    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail=f"Шаблон договора не найден: {TEMPLATE_PATH}")

    try:
        # Загрузка шаблона с помощью DocxTemplate
        doc = DocxTemplate(TEMPLATE_PATH)  # Используем DocxTemplate

        # Подготовка контекста (словаря) для Jinja2
        # Имена ключей должны ТОЧНО соответствовать плейсхолдерам БЕЗ {{ }}
        context = _prepare_context_for_tpl(data)
        floorplan_images = FLOORPLAN_IMAGES.get(data.jkName, [])
        img_index = data.floor - 1
        if 0 <= img_index < len(floorplan_images):
            img_path = floorplan_images[img_index]
            # Задаём желаемую ширину картинки (например, 140 мм). Высота подгонится автоматически:
            context["FloorPlan"] = InlineImage(doc, img_path, width=Mm(140))
        else:
            # Если нет подходящего плана, можно вставить пустую строку или сообщение:
            context["FloorPlan"] = "План этажа недоступен"
        # Рендеринг шаблона (заполнение)
        doc.render(context)

        # Сохранение в буфер (немного отличается синтаксис)
        contract_buffer = BytesIO()
        doc.save(contract_buffer)
        contract_buffer.seek(0)

        entry, apartment = _create_contract_registry_entry(db, complex_obj, data, contract_number)
        if apartment:
            apartment.status = SOLD_STATUS_IN_CHESS
            payload = dict(apartment.raw_payload or {})
            for key in list(payload.keys()):
                if isinstance(key, str) and "статус" in key.lower():
                    payload[key] = SOLD_STATUS_IN_CHESS
            apartment.raw_payload = payload or None

        if lead_obj:
            total_amount = clean_number(data.totalPrice)
            price_per_sqm = clean_number(data.pricePerM2)
            initial_payment = clean_number(data.initialPayment)
            monthly_payment = clean_number(data.monthlyPayment) if data.monthlyPayment else None
            final_payment = clean_number(data.finalPayment) if data.finalPayment else None

            lead_obj.state = LeadState.CLOSED
            if total_amount:
                lead_obj.total_price = total_amount
            if price_per_sqm:
                lead_obj.square_meters_price = price_per_sqm
            if initial_payment:
                lead_obj.down_payment = initial_payment
            if data.paymentChoice:
                lead_obj.down_payment_percent = data.paymentChoice
            if monthly_payment is not None:
                lead_obj.monthly_payment = monthly_payment
            if final_payment is not None:
                lead_obj.hybrid_final_payment = final_payment
            lead_obj.updated_at = datetime.utcnow()

        db.commit()

        contract_filename = f"contract_{contract_number}.docx"
    except Exception as e:
        db.rollback()
        # Добавим вывод traceback для лучшей диагностики
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка обработки договора: {str(e)}")

    await invalidate_complex_cache()

    return StreamingResponse(
        contract_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"{contract_filename}\"",
            "Content-Length": str(contract_buffer.getbuffer().nbytes)
        }
    )

# --- Вспомогательные функции ---

def _generate_contract_number(db: Session, complex_obj: ResidentialComplex) -> str:
    existing_numbers = (
        db.query(ContractRegistryEntry.contract_number)
        .filter(ContractRegistryEntry.complex_id == complex_obj.id)
        .all()
    )
    max_seq = 0
    for (number,) in existing_numbers:
        seq = _extract_contract_sequence(number)
        if seq and seq > max_seq:
            max_seq = seq
    next_seq = max_seq + 1
    return f"Д-{str(next_seq).zfill(4)}"


def _prepare_context_for_tpl(data: ContractData) -> Dict[str, any]:
    """Подготовка словаря (контекста) для docxtpl."""
    total_amount = clean_number(data.totalPrice)
    initial_payment = clean_number(data.initialPayment)
    monthly_payment_override = None
    if getattr(data, "monthlyPayment", None) is not None:
        monthly_payment_override = clean_number(data.monthlyPayment)

    # Не допускаем отрицательных значений
    # Осторожно с делением на 0, если total_amount может быть 0
    contract_date = parse_date(data.contractDate)  # Предполагаем, что parse_date возвращает datetime объект
    print(data.contractDate)
    if data.jkName == "ЖК_Бахор":
        start_date = datetime(2025, 10, 1)
        end_date = start_date + relativedelta(months=24)

    else:
        start_date = datetime(2025, 10, 1)
        end_date = start_date + relativedelta(months=21)

    # Текущая дата (сегодня)
    today = datetime.today()

    # Считаем разницу в месяцах
    diff_years = end_date.year - today.year
    diff_months = end_date.month - today.month
    total_months_left = diff_years * 12 + diff_months

    # Если день уже прошел текущий месяц, уменьшаем на 1
    if today.day > 1:
        total_months_left -= 1
    total_months_left = max(total_months_left, 0)
    if monthly_payment_override is not None:
        monthly_payment = monthly_payment_override
    else:
        monthly_payment = (
            total_amount - initial_payment
        ) / total_months_left if total_amount and initial_payment is not None and total_months_left else 0

    # Не допускаем отрицательных значений
    # Ключи БЕЗ {{ }}
    context = {
        "Номер_Договора": data.contractNumber or "N/A",
        "Дата": contract_date or "N/A",  # Оставить как строку или форматировать?
        "Ф_И_О": data.fullName or "N/A",
        "Серия_Паспорта": data.passportSeries or "N/A",
        "Кем_Выдан": data.issuedBy or "N/A",
        "Прописка": data.registrationAddress or "N/A",
        "Номер_Тел": data.phone or "N/A",
        "ПИНФЛ": data.pinfl or "N/A",
        "Блок": str(data.block or "N/A"),
        "Этаж": str(data.floor) if data.floor is not None else "N/A",
        "Номер_КВ": str(data.apartmentNumber) if data.apartmentNumber is not None else "N/A",
        "Кол_во_Ком": str(data.rooms) if data.rooms is not None else "N/A",
        "Квадратура_Квартиры": str(data.size) if data.size is not None else "N/A",
        "Квадратура_Не_жилое": str(data.size) if data.size is not None else "N/A",
        "Общ_Стоимость": f"{(monthly_payment * total_months_left):,.0f}".replace(",",
                                                                                 " ") if total_amount is not None else "N/A",
        "Общ_Стоимость_1": f"{total_amount :,.0f}".replace(",", " ") if total_amount is not None else "N/A",
        "Общ_Стоимость_Про": _number_to_words(f"{total_amount :,.0f}"),
        "Стоимость_1_м2": (data.pricePerM2 or "N/A").replace(" ", "").replace("\xa0", ""),
        "Стоимость_1_м2_Про": _number_to_words(data.pricePerM2),
        "Процент_1_Взноса": (data.paymentChoice or "N/A").replace("%", ""),
        "Сумма_1_Взноса": f"{initial_payment:,.0f}".replace(",", " ") if initial_payment is not None else "N/A",
        "Сумма_1_Взноса_Про": _number_to_words(data.initialPayment),
        # --- График платежей ---
        # Можно передать список словарей для цикла {% for item in payment_schedule %} в шаблоне
        # Или генерировать ключи динамически, как у вас было
    }

    # Добавление графика платежей (динамические ключи)
    if contract_date:  # Проверяем, что дата есть
        payment_schedule = []
        current_payment_date = contract_date + relativedelta(months=1)  # Первый платеж через месяц? Уточнить логику
        # Уточнить, первый взнос уже покрыт? Расчет monthly_payment должен это учитывать.
        # Пример расчета остатка: remaining_amount = total_amount - initial_payment
        # monthly_payment = remaining_amount / 24 # Если рассрочка на 24 месяца *после* первого взноса

        for i in range(1, 24):
            # payment_date = contract_date + relativedelta(months=i) # Платеж в след. месяце
            payment_date = current_payment_date + relativedelta(months=i - 1)  # Платеж начиная с current_payment_date
            context[f"Дата_Платежа_{i}"] = payment_date.strftime("%d.%m.%Y")
            context[f"Сумма_Платежа_{i}"] = f"{monthly_payment:,.0f}".replace(",",
                                                                              " ") if monthly_payment is not None else "N/A"
            context[f"Оплачено_{i}"] = ""  # Обычно поле "Оплачено" оставляют пустым при генерации

            # Альтернатива: создать список для цикла в шаблоне
            # payment_schedule.append({
            #     "date": payment_date.strftime("%d.%m.%Y"),
            #     "amount": f"{monthly_payment:,.0f}".replace(",", " ") if monthly_payment is not None else "N/A",
            #     "paid": ""
            # })

        # Если использовать список:
        # context["payment_schedule"] = payment_schedule
        # В шаблоне .docx: {% for p in payment_schedule %} {{p.date}} {{p.amount}} {% endfor %}

    return context


def _create_contract_registry_entry(
        db: Session,
        complex_obj: ResidentialComplex,
        data: ContractData,
        contract_number: str,
) -> tuple[ContractRegistryEntry, Optional[ApartmentUnit]]:
    contract_date = parse_date(data.contractDate).date()
    total_amount = clean_number(data.totalPrice)
    price_m2 = clean_number(data.pricePerM2)
    initial_payment = clean_number(data.initialPayment)
    payment_choice_clean = clean_number((data.paymentChoice or "").replace("%", "")) if data.paymentChoice else None

    apartment = _find_apartment_unit(
        db,
        complex_obj.id,
        data.block,
        data.floor,
        data.apartmentNumber,
    )

    entry = ContractRegistryEntry(
        complex_id=complex_obj.id,
        apartment_id=apartment.id if apartment else None,
        contract_number=contract_number,
        contract_date=contract_date,
        block_name=data.block,
        floor=_coerce_int(data.floor),
        apartment_number=_normalize_unit_number(data.apartmentNumber),
        rooms=data.rooms,
        area_sqm=clean_number(str(data.size)),
        total_price=total_amount,
        price_per_sqm=price_m2,
        down_payment_percent=payment_choice_clean,
        down_payment_amount=initial_payment,
        buyer_full_name=data.fullName,
        buyer_passport_series=data.passportSeries,
        buyer_pinfl=data.pinfl,
        issued_by=data.issuedBy,
        registration_address=data.registrationAddress,
        phone_number=data.phone,
        sales_department=data.salesDepartment,
        extra_data=None,
    )

    db.add(entry)
    db.flush()
    return entry, apartment


@router.get("/download-contract-registry")
async def download_contract_registry(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    entries = (
        db.query(ContractRegistryEntry)
        .filter(ContractRegistryEntry.complex_id == complex_obj.id)
        .order_by(ContractRegistryEntry.contract_date.desc(), ContractRegistryEntry.id.desc())
        .all()
    )

    headers = [
        "№ Договора", "Дата Договора", "Блок", "Этаж", "№ КВ", "Кол-во ком",
        "Квадратура Квартиры", "Общ Стоимость Договора", "Стоимость 1 кв.м",
        "Процент 1 Взноса", "Сумма 1 Взноса", "Ф/И/О", "Серия Паспорта",
        "ПИНФЛ", "Кем выдан", "Адрес прописки", "Номер тел", "Отдел Продаж"
    ]

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)

    for entry in entries:
        sheet.append([
            entry.contract_number,
            entry.contract_date,
            entry.block_name,
            entry.floor,
            entry.apartment_number,
            entry.rooms,
            entry.area_sqm,
            entry.total_price,
            entry.price_per_sqm,
            entry.down_payment_percent,
            entry.down_payment_amount,
            entry.buyer_full_name,
            entry.buyer_passport_series,
            entry.buyer_pinfl,
            entry.issued_by,
            entry.registration_address,
            entry.phone_number,
            entry.sales_department,
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"contract_registry_{jkName}.xlsx"
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition}
    )


@router.get("/get-contract-registry")
async def get_contract_registry(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    entries = (
        db.query(ContractRegistryEntry)
        .filter(ContractRegistryEntry.complex_id == complex_obj.id)
        .order_by(ContractRegistryEntry.contract_date.desc(), ContractRegistryEntry.id.desc())
        .all()
    )

    registry_rows: List[Dict[str, Any]] = []
    for entry in entries:
        row: Dict[str, Any] = {
            "№ Договора": entry.contract_number,
            "Дата Договора": _render_contract_value(entry.contract_date),
            "Блок": entry.block_name,
            "Этаж": entry.floor,
            "№ КВ": entry.apartment_number,
            "Кол-во ком": entry.rooms,
            "Квадратура Квартиры": entry.area_sqm,
            "Общ Стоимость Договора": entry.total_price,
            "Стоимость 1 кв.м": entry.price_per_sqm,
            "Процент 1 Взноса": entry.down_payment_percent,
            "Сумма 1 Взноса": entry.down_payment_amount,
            "Ф/И/О": entry.buyer_full_name,
            "Серия Паспорта": entry.buyer_passport_series,
            "ПИНФЛ": entry.buyer_pinfl,
            "Кем выдан": entry.issued_by,
            "Адрес прописки": entry.registration_address,
            "Номер тел": entry.phone_number,
            "Отдел Продаж": entry.sales_department,
        }
        if entry.extra_data:
            extra = dict(entry.extra_data)
            for skip_key in ("unitType", "rawPaymentChoice"):
                extra.pop(skip_key, None)
            for key, value in extra.items():
                row.setdefault(key, value)
        registry_rows.append(row)

    return {"registry": registry_rows}


NEW_STATUS_ON_DELETE = "свободна"  # Статус, который нужно установить в шахматке
REGISTRY_COLUMN_HEADERS = {
    "contractNumber": "№ Договора",  # Пример
    "block": "Блок",  # Пример
    "floor": "Этаж",  # Пример
    "apartmentNumber": "№ КВ"  # Пример
}

# --- Новый функционал: Синхронизация статусов шахматки с реестром ---
SOLD_STATUS_IN_CHESS = "продана"

# --- Helpers for robust matching (blocks/floor/apt) ---
def _to_int_first(value) -> Optional[int]:
    """Берёт первые найденные цифры из значения и возвращает int, иначе None."""
    if value is None:
        return None
    s = str(value)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None

# Карта замены «похожих» кириллических букв на латиницу
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
    """
    Нормализует название блока:
      - trim + lower
      - конверт «похожие» кириллические буквы в латиницу
      - все пробелы/подчёркивания/дефисы -> одиночный '-'
    """
    if value is None:
        return ""
    s = str(value).strip()
    s = "".join(_CYR_TO_LAT.get(ch, ch) for ch in s)  # unify Cyrillic lookalikes
    s = s.lower()
    s = re.sub(r"[\\s_–—\\-]+", "-", s)
    return s


def sync_chess_with_registry(db: Session, jkName: str) -> dict:
    complex_obj = _get_db_complex(db, jkName)

    registry_entries = (
        db.query(ContractRegistryEntry)
        .filter(ContractRegistryEntry.complex_id == complex_obj.id)
        .all()
    )

    sold_keys: set[tuple[str, int, str]] = set()
    for entry in registry_entries:
        block_norm = _normalize_block_name(entry.block_name)
        floor_val = entry.floor
        if floor_val is None and entry.extra_data:
            floor_val = _coerce_int(entry.extra_data.get("Этаж"))
        apt_number = entry.apartment_number or (entry.extra_data.get("№ КВ") if entry.extra_data else None)
        apt_norm = _normalize_unit_number(apt_number)

        if block_norm and floor_val is not None and apt_norm:
            sold_keys.add((block_norm, floor_val, apt_norm))

    apartments = (
        db.query(ApartmentUnit)
        .filter(ApartmentUnit.complex_id == complex_obj.id)
        .all()
    )

    updated = 0
    for apartment in apartments:
        key = (
            _normalize_block_name(apartment.block_name),
            apartment.floor,
            _normalize_unit_number(apartment.unit_number),
        )
        if key in sold_keys and (apartment.status or "").strip().lower() != SOLD_STATUS_IN_CHESS:
            apartment.status = SOLD_STATUS_IN_CHESS
            payload = dict(apartment.raw_payload or {})
            for column_key in list(payload.keys()):
                if isinstance(column_key, str) and "статус" in column_key.lower():
                    payload[column_key] = SOLD_STATUS_IN_CHESS
            apartment.raw_payload = payload or None
            updated += 1

    if updated:
        db.commit()

    return {
        "status": "success",
        "updated": updated,
        "totalContracts": len(registry_entries),
    }



@router.delete("/delete-contract-from-registry")
async def delete_contract_from_registry_and_update_shaxmatка(
        jkName: str = Query(..., description="Название жилого комплекса"),
        contractNumber: str = Query(..., description="Номер договора для удаления (например, Д-0001)"),
        db: Session = Depends(get_db),
):
    """
    Удаляет договор из базы и возвращает квартиру в статус 'свободна'.
    """
    contract_number_clean = contractNumber.strip()
    complex_obj = _get_db_complex(db, jkName)

    entry = (
        db.query(ContractRegistryEntry)
        .filter(
            ContractRegistryEntry.complex_id == complex_obj.id,
            ContractRegistryEntry.contract_number == contract_number_clean,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail=f"Договор '{contractNumber}' не найден")

    block_name = entry.block_name or (entry.extra_data or {}).get("Блок")
    floor_value = entry.floor
    if floor_value is None and entry.extra_data:
        floor_value = _coerce_int(entry.extra_data.get("Этаж"))
    apartment_number = entry.apartment_number or ((entry.extra_data or {}).get("№ КВ"))

    apartment: Optional[ApartmentUnit] = None
    if entry.apartment_id:
        apartment = db.query(ApartmentUnit).filter(ApartmentUnit.id == entry.apartment_id).first()

    if apartment is None and floor_value is not None and apartment_number:
        apartment = _find_apartment_unit(
            db,
            complex_obj.id,
            block_name,
            floor_value,
            apartment_number,
        )

    db.delete(entry)

    apartment_updated = False
    if apartment:
        apartment.status = NEW_STATUS_ON_DELETE
        payload = dict(apartment.raw_payload or {})
        for key in list(payload.keys()):
            if isinstance(key, str) and "статус" in key.lower():
                payload[key] = NEW_STATUS_ON_DELETE
        apartment.raw_payload = payload or None
        apartment_updated = True

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Не удалось удалить договор: {exc}") from exc

    await invalidate_complex_cache()

    message = f"Договор '{contractNumber}' удален из реестра."
    if apartment_updated:
        message += f" Статус квартиры обновлен на '{NEW_STATUS_ON_DELETE}'."
    else:
        message += " Не удалось определить квартиру для обновления статуса."

    return {
        "status": "success" if apartment_updated else "warning",
        "message": message,
    }


# --- Новый эндпоинт: Синхронизация шахматки с реестром ---
@router.post("/sync-chess-with-registry", summary="Sync chess statuses with contract registry")
async def api_sync_chess_with_registry(
        jkName: str = Query(..., description="Название ЖК для синхронизации"),
        db: Session = Depends(get_db),
):
    result = sync_chess_with_registry(db, jkName)
    await invalidate_complex_cache()
    return result


import os


# Получить список всех ЖК (папок в BASE_STATIC_PATH)
@router.get("/complexes", summary="List all residential complexes")
async def list_complexes(db: Session = Depends(get_db)):
    complexes = (
        db.query(ResidentialComplex)
        .order_by(ResidentialComplex.name.asc())
        .all()
    )
    if complexes:
        return {"complexes": [c.name for c in complexes]}

    if not os.path.exists(BASE_STATIC_PATH):
        return {"complexes": []}

    items = [
        name for name in os.listdir(BASE_STATIC_PATH)
        if os.path.isdir(os.path.join(BASE_STATIC_PATH, name))
    ]
    return {"complexes": items}


# Получить список файлов внутри папки конкретного ЖК
@router.get("/complexes/{jkName}/files", summary="List files for a given residential complex")
async def list_complex_files(jkName: str):
    """
    Возвращает список файлов внутри папки конкретного ЖК.
    """
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    if not os.path.isdir(jk_dir):
        raise HTTPException(status_code=404, detail=f"ЖК '{jkName}' не найден")
    try:
        files = [
            fname for fname in os.listdir(jk_dir)
            if os.path.isfile(os.path.join(jk_dir, fname))
        ]
        print(files)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении файлов ЖК: {e}")


# --- Новый эндпоинт: Получить price_shaxamtka.xlsx как JSON ---
@router.get("/complexes/{jkName}/price", summary="Get price data for a given residential complex")
async def get_price(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    price_entries = (
        db.query(ChessboardPriceEntry)
        .filter(ChessboardPriceEntry.complex_id == complex_obj.id)
        .order_by(ChessboardPriceEntry.order_index.asc(), ChessboardPriceEntry.category_key.asc())
        .all()
    )

    if not price_entries:
        return {"headers": [], "rows": []}

    ordered_categories: List[Tuple[int, str]] = []
    seen: set[str] = set()
    for entry in price_entries:
        if entry.category_key in seen:
            continue
        ordered_categories.append((entry.order_index, entry.category_key))
        seen.add(entry.category_key)
    ordered_categories.sort(key=lambda item: (item[0], item[1]))

    floor_map: Dict[int, Dict[str, float]] = {}
    for entry in price_entries:
        floor_map.setdefault(int(entry.floor), {})[entry.category_key] = entry.price_per_sqm

    headers = ["Этаж"] + [cat for _, cat in ordered_categories]
    rows: List[Dict[str, Any]] = []
    for floor in sorted(floor_map.keys(), reverse=True):
        row_payload: Dict[str, Any] = {"Этаж": floor}
        for _, original_key in ordered_categories:
            row_payload[original_key] = floor_map[floor].get(original_key)
        rows.append(row_payload)

    return {"headers": headers, "rows": rows}


@router.put("/complexes/{jkName}/price", summary="Update price data for a given residential complex")
async def update_price(
        jkName: str,
        data: Dict[str, Any] = Body(...,
                                    description="JSON с ключами 'headers' (list) и 'rows' (list of dict)"),
        db: Session = Depends(get_db),
):
    headers = data.get("headers")
    rows = data.get("rows")

    if not isinstance(headers, list) or not headers:
        raise HTTPException(status_code=400, detail="Headers must be a non-empty list")
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="Rows must be a list of dictionaries")
    if len(headers) < 2:
        raise HTTPException(status_code=400, detail="Не указаны колонки с ценами")

    floor_header = headers[0]
    category_headers = headers[1:]

    complex_obj = _get_db_complex(db, jkName)

    db.query(ChessboardPriceEntry).filter(ChessboardPriceEntry.complex_id == complex_obj.id).delete(
        synchronize_session=False
    )

    new_entries: List[ChessboardPriceEntry] = []

    for row_data in rows:
        if not isinstance(row_data, dict):
            continue
        floor_value = row_data.get(floor_header)
        floor_int = _coerce_int(floor_value)
        if floor_int is None:
            continue

        for order_index, category_header in enumerate(category_headers):
            raw_price = row_data.get(category_header)
            price_float = _clean_float(raw_price)
            if price_float is None:
                continue

            new_entries.append(
                ChessboardPriceEntry(
                    complex_id=complex_obj.id,
                    floor=floor_int,
                    category_key=str(category_header),
                    price_per_sqm=price_float,
                    order_index=order_index,
                )
            )

    if new_entries:
        db.bulk_save_objects(new_entries)
    db.commit()

    await invalidate_complex_cache([
        "complexes:price-by-key",
        "complexes:price-all",
        "complexes:aggregate",
        "complexes:apartment-info",
    ])

    return {
        "status": "success",
        "message": f"Price grid updated for '{jkName}'",
        "records": len(new_entries),
    }


class ChessUpdate(BaseModel):
    apt: str
    status: str


class ChessUpdates(BaseModel):
    updates: List[ApartmentStatusUpdate]


@router.get("/complexes/{jkName}/chess", summary="Get full chess grid")
async def get_chess(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    apartments = (
        db.query(ApartmentUnit)
        .filter(ApartmentUnit.complex_id == complex_obj.id)
        .order_by(
            ApartmentUnit.block_name.asc(),
            ApartmentUnit.floor.asc(),
            ApartmentUnit.unit_number.asc(),
        )
        .all()
    )

    grid: List[Dict[str, Any]] = []
    for unit in apartments:
        row: Dict[str, Any] = {
            "block": unit.block_name,
            "unit_type": unit.unit_type,
            "status": unit.status,
            "rooms": unit.rooms,
            "number": unit.unit_number,
            "area": unit.area_sqm,
            "floor": unit.floor,
        }
        if unit.raw_payload:
            row.update(unit.raw_payload)
        grid.append(row)

    return {"grid": grid}


@router.put("/complexes/chess", summary="Update chess grid statuses")
async def update_chess(data: ChessUpdates, db: Session = Depends(get_db)):
    """
    Принимает JSON:
    {
      "updates": [
        {
          "jkName":"ЖК Бахор",
          "blockName":"Блок-1",
          "floor":5,
          "apartmentNumber":101,
          "newStatus":"Бронь"
        },
        ...
      ]
    }
    """
    not_found: List[str] = []
    updated = 0

    for upd in data.updates:
        try:
            complex_obj = _get_db_complex(db, upd.jkName)
        except HTTPException:
            not_found.append(f"{upd.jkName}: комплекс не найден")
            continue

        normalized_number = _normalize_unit_number(upd.apartmentNumber)
        candidates = (
            db.query(ApartmentUnit)
            .filter(
                ApartmentUnit.complex_id == complex_obj.id,
                ApartmentUnit.floor == upd.floor,
                ApartmentUnit.unit_number == normalized_number,
            )
            .all()
        )

        target_unit = next(
            (
                unit for unit in candidates
                if _normalize_block_name(unit.block_name) == _normalize_block_name(upd.blockName)
            ),
            None,
        )

        if not target_unit:
            not_found.append(
                f"{upd.jkName} — Блок={upd.blockName}, этаж={upd.floor}, кв={upd.apartmentNumber}"
            )
            continue

        target_unit.status = upd.newStatus
        payload = dict(target_unit.raw_payload or {})
        for key in list(payload.keys()):
            if isinstance(key, str) and "статус" in key.lower():
                payload[key] = upd.newStatus
        target_unit.raw_payload = payload or None
        updated += 1

    if updated:
        db.commit()
        await invalidate_complex_cache()
    else:
        db.rollback()

    if not_found:
        raise HTTPException(status_code=404, detail={"not_updated": not_found})

    return {"detail": "Все статусы успешно сохранены", "updated": updated}


# --- Новый эндпоинт для замены файла в папке ЖК ---
@router.post("/replace-file", summary="Replace a file in a given residential complex")
async def replace_file(
        name: str = Form(..., description="Название жилого комплекса (jkName)"),
        category: str = Form(..., description="Категория файла: 'jk_data', 'price', 'template', 'registry', 'tamplate_empty'"),
        file: UploadFile = File(..., description="Загружаемый файл"),
        db: Session = Depends(get_db),
):
    """
    Загружает новый файл и заменяет существующий в папке ЖК.
    """
    # Определяем директорию комплекса
    complex_dir = os.path.join(BASE_STATIC_PATH, name)
    if not os.path.isdir(complex_dir):
        raise HTTPException(status_code=404, detail=f"ЖК '{name}' не найден")

    complex_obj = _get_db_complex(db, name)

    # Определяем имя файла на сервере по категории
    filename_map = {
        "jk_data": "jk_data.xlsx",
        "price": "price_shaxamtka.xlsx",
        "template": "contract_template.docx",
        "registry": "contract_registry.xlsx",
        "template_empty": "contract_template_empty.docx"
    }
    target_filename = filename_map.get(category)
    if not target_filename:
        raise HTTPException(status_code=400, detail=f"Неизвестная категория файла: {category}")

    target_path = os.path.join(complex_dir, target_filename)
    try:
        with open(target_path, "wb") as out_file:
            shutil.copyfileobj(file.file, out_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {e}")

    imports_summary: Dict[str, Any] = {}

    try:
        if category == "jk_data":
            apartments = import_chess_from_excel(db, complex_obj, target_path)
            imports_summary["apartments"] = apartments
        elif category == "price":
            prices = import_price_from_excel(db, complex_obj, target_path)
            imports_summary["prices"] = prices
        elif category == "registry":
            contracts = import_contract_registry_from_excel(db, complex_obj, target_path)
            imports_summary["contracts"] = contracts
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при импорте данных из Excel: {exc}") from exc

    await invalidate_complex_cache()

    return {
        "status": "success",
        "message": f"Файл '{target_filename}' заменён в ЖК '{name}'",
        "imports": imports_summary,
    }


# --- Новый эндпоинт: Получить все забронированные квартиры ---
@router.get("/reserved-apartments", summary="Get reserved apartments for a given residential complex")
async def get_reserved_apartments(jkName: str, db: Session = Depends(get_db)):
    complex_obj = _get_db_complex(db, jkName)

    reserved_units = (
        db.query(ApartmentUnit)
        .filter(
            ApartmentUnit.complex_id == complex_obj.id,
            func.lower(ApartmentUnit.status) == "бронь",
        )
        .all()
    )

    reserved = [
        {
            "blockName": unit.block_name,
            "floor": unit.floor,
            "apartmentNumber": unit.unit_number,
        }
        for unit in reserved_units
    ]

    return {"reservedApartments": reserved}


# --- Новый эндпоинт: Получить статус конкретной квартиры ---
@router.get("/apartment-status", summary="Get status of a specific apartment")
async def get_apartment_status(
        jkName: str = Query(..., description="Name of the residential complex"),
        blockName: str = Query(..., description="Block name"),
        floor: int = Query(..., description="Floor number"),
        apartmentNumber: Union[int, str] = Query(..., description="Apartment number"),
        db: Session = Depends(get_db),
):
    complex_obj = _get_db_complex(db, jkName)

    normalized_number = _normalize_unit_number(apartmentNumber)
    candidates = (
        db.query(ApartmentUnit)
        .filter(
            ApartmentUnit.complex_id == complex_obj.id,
            ApartmentUnit.floor == floor,
            ApartmentUnit.unit_number == normalized_number,
        )
        .all()
    )

    target_unit = next(
        (
        unit for unit in candidates
        if _normalize_block_name(unit.block_name) == _normalize_block_name(blockName)
        ),
        None,
    )

    if not target_unit:
        raise HTTPException(status_code=404, detail="Apartment not found")

    return {"apartmentStatus": target_unit.status}


# --- Новый эндпоинт: Скачать один из трех файлов для ЖК ---
@router.get("/complexes/{jkName}/download", summary="Download specific file for a residential complex")
async def download_complex_file(
        jkName: str = Path(..., description="Name of the residential complex"),
        fileType: str = Query(..., description="Type of file to download: 'jk_data', 'price', or 'template'")
):
    """
    Downloads one of the configured files for the given residential complex.
    Allowed fileType values:
      - 'jk_data' -> jk_data.xlsx
      - 'price' -> price_shaxamtka.xlsx
      - 'template' -> contract_template.docx
      - 'registry' -> contract_registry.xlsx
    """
    filename_map = {
        "jk_data": "jk_data.xlsx",
        "price": "price_shaxamtka.xlsx",
        "template": "contract_template.docx",
        "registry": "contract_registry.xlsx"
    }
    file_name = filename_map.get(fileType)
    if not file_name:
        raise HTTPException(status_code=400,
                            detail=f"Unknown fileType '{fileType}'. Valid options are: {', '.join(filename_map.keys())}")
    file_path = os.path.join(BASE_STATIC_PATH, jkName, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found for complex '{jkName}'")
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=file_name
    )
