from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Union, Dict, List, Any
from dateutil.relativedelta import relativedelta
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from fastapi import APIRouter, HTTPException, Body, Query, Path
from fastapi import Form, UploadFile, File
import shutil
from num2words import num2words
from openpyxl.reader.excel import load_workbook
from openpyxl.workbook import Workbook
from pydantic import BaseModel, Field
import openpyxl
import os
import traceback  # Для логирования ошибок

from starlette.responses import StreamingResponse, FileResponse


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

# Словарь путей к файлам Excel для каждого ЖК
EXCEL_FILE_PATHS = {
    # !!! ЗАМЕНИТЕ НА ВАШИ РЕАЛЬНЫЕ ИМЕНА ЖК И ПУТИ !!!
    "ЖК_Бахор": os.path.join("static", "Жилые_Комплексы", "ЖК_Бахор", "jk_data.xlsx"),
    "ЖК_Рассвет": os.path.join("static", "Жилые_Комплексы", "ЖК_Рассвет", "jk_data.xlsx"),
}

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
    salesDepartment: Union[str, None] = None


# Функция преобразования числа в слова (на русском языке)
def _number_to_words(number: str) -> str:
    # Убираем все нечисловые символы и преобразуем в int
    clean_number = ''.join(filter(str.isdigit, number))
    return num2words(int(clean_number), lang='ru') + " сум"


router = APIRouter(prefix="/excel", tags=["Excel Operations"])  # Пример префикса


# --- Обновленная Логика обновления Excel ---
def find_row_and_update_status(file_path: str, update_data: ApartmentStatusUpdate):
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        block_col_idx = col_letter_to_index(COLUMN_MAPPING["blockName"])
        floor_col_idx = col_letter_to_index(COLUMN_MAPPING["floor"])
        apt_num_col_idx = col_letter_to_index(COLUMN_MAPPING["apartmentNumber"])
        status_col_idx = col_letter_to_index(COLUMN_MAPPING["status"])

        print(f"Поиск в файле: {file_path}")
        print(f"Критерии: Блок='{update_data.blockName}', Этаж={update_data.floor}, Кв={update_data.apartmentNumber}")
        print(f"Колонки: Блок={block_col_idx}, Этаж={floor_col_idx}, Кв={apt_num_col_idx}, Статус={status_col_idx}")

        target_row_idx = -1
        for row_idx in range(DATA_START_ROW, sheet.max_row + 1):
            cell_block = sheet.cell(row=row_idx, column=block_col_idx).value
            cell_floor = sheet.cell(row=row_idx, column=floor_col_idx).value
            cell_apt_num = sheet.cell(row=row_idx, column=apt_num_col_idx).value

            print(f"Строка {row_idx}: Блок='{cell_block}', Этаж='{cell_floor}', Кв='{cell_apt_num}'")

            try:
                current_block = str(cell_block).strip().lower() if cell_block else ""
                update_block = str(update_data.blockName).strip().lower()
                matches_block = current_block == update_block

                current_floor = int(cell_floor) if cell_floor is not None else None
                matches_floor = current_floor == update_data.floor

                current_apt_num = int(cell_apt_num) if cell_apt_num is not None else None
                matches_apt_num = current_apt_num == update_data.apartmentNumber

                if matches_block and matches_floor and matches_apt_num:
                    target_row_idx = row_idx
                    print(f"Найдена строка {row_idx}!")
                    break

            except (ValueError, TypeError) as e:
                print(f"Ошибка в строке {row_idx}: {e}")
                continue

        print(f"Итоговый target_row_idx: {target_row_idx}")
        if target_row_idx != -1:
            status_cell = sheet.cell(row=target_row_idx, column=status_col_idx)
            old_status = status_cell.value
            status_cell.value = update_data.newStatus
            workbook.save(file_path)
            print(f"Статус обновлен: строка {target_row_idx}, '{old_status}' -> '{update_data.newStatus}'")
            return True
        else:
            print(
                f"Квартира не найдена: Блок={update_data.blockName}, Этаж={update_data.floor}, Кв={update_data.apartmentNumber}")
            return False

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Excel file not found: {file_path}")
    except Exception as e:
        print(f"Ошибка при обновлении Excel: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {e}")


@router.post("/update-status")
async def update_excel_status_endpoint(update_data: ApartmentStatusUpdate = Body(...)):
    print(f"Запрос: {update_data.dict()}")
    file_path = EXCEL_FILE_PATHS.get(update_data.jkName)

    if not file_path:
        return {"status": "warning", "message": f"Excel file path config missing for '{update_data.jkName}'"}

    if not os.path.exists(file_path):
        return {"status": "warning", "message": f"Excel file not found for '{update_data.jkName}'"}

    success = find_row_and_update_status(file_path, update_data)
    if success:
        return {"status": "success", "message": "Apartment status updated successfully"}
    else:
        return {"status": "warning", "message": f"Apartment not found in Excel for '{update_data.jkName}'"}


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
async def get_last_contract_number(jkName: str):
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    if not os.path.exists(REGISTRY_PATH):
        return {"lastContractNumber": 1}  # Файл не существует — начинаем с первого номера

    try:
        wb_registry = load_workbook(REGISTRY_PATH)
        ws_registry = wb_registry.active
        last_number = 0

        # Ищем последнюю строку с номером договора в формате Д-XXXX
        for row in reversed(list(ws_registry.iter_rows(min_row=2, values_only=True))):
            contract_num = row[0]
            if contract_num and isinstance(contract_num, str):
                try:
                    number = int(contract_num.split('-')[0])
                    last_number = max(last_number, number)
                except (IndexError, ValueError):
                    continue

        next_number = last_number + 1
        return {"lastContractNumber": next_number}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении реестра: {str(e)}")


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


from pdf2image import convert_from_path

FLOORPLAN_IMAGES_DIR = os.path.join(BASE_DIR, "static", "floorplans")

PDF_PLAN_PATH = os.path.join(BASE_STATIC_PATH, "ЖК_Бахор", "Plan pradaja.pdf")


def convert_floorplan_pdf_to_images(pdf_path: str, output_dir: str) -> list[str]:
    """
    Конвертирует PDF поэтажных планов в PNG, сохраняет в output_dir.
    Возвращает список имен файлов изображений в том порядке, в каком страницы в PDF.
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Конвертируем PDF {pdf_path} в PNG в директории {output_dir}")

    pil_images = convert_from_path(pdf_path, dpi=150)

    saved_paths: list[str] = []

    crop_box = (529, 530, 960, 982)  # (left, upper, right, lower)

    for idx, image in enumerate(pil_images):
        page_number = idx + 1
        # full_fname = os.path.join(output_dir, f"floorplan_page_{page_number}_full.png")
        # image.save(full_fname, "PNG")

        cropped_img = image.crop(crop_box)

        cropped_fname = os.path.join(output_dir, f"floorplan_page_{page_number}.png")
        cropped_img.save(cropped_fname, "PNG")
        print(f"Сохранён скропанный план этажа: {cropped_fname}")
        saved_paths.append(cropped_fname)

    return saved_paths


floorplan_images = convert_floorplan_pdf_to_images(PDF_PLAN_PATH, FLOORPLAN_IMAGES_DIR)


@router.post("/generate-contract")
async def generate_contract(data: ContractData):
    """Генерация договора в формате DOCX и обновление реестра в XLSX (с использованием docxtpl)."""

    jk_dir = os.path.join(BASE_STATIC_PATH, data.jkName)
    TEMPLATE_PATH = os.path.join(jk_dir, "contract_template.docx")
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    os.makedirs(jk_dir, exist_ok=True)

    contract_number = data.contractNumber or _generate_contract_number(REGISTRY_PATH)
    data.contractNumber = contract_number  # Сохраняем сгенерированный номер обратно в данные

    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail=f"Шаблон договора не найден: {TEMPLATE_PATH}")

    try:
        # Загрузка шаблона с помощью DocxTemplate
        doc = DocxTemplate(TEMPLATE_PATH)  # Используем DocxTemplate

        # Подготовка контекста (словаря) для Jinja2
        # Имена ключей должны ТОЧНО соответствовать плейсхолдерам БЕЗ {{ }}
        context = _prepare_context_for_tpl(data)
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

        _update_registry(REGISTRY_PATH, data)  # Обновление реестра остается прежним

        contract_filename = f"contract_{contract_number}.docx"
        return StreamingResponse(
            contract_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{contract_filename}\"",
                "Content-Length": str(contract_buffer.getbuffer().nbytes)  # Длина буфера
            }
        )

    except Exception as e:
        # Добавим вывод traceback для лучшей диагностики
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка обработки договора: {str(e)}")


# --- Вспомогательные функции ---

def _generate_contract_number(registry_path: str) -> str:
    # ... (без изменений)
    if not os.path.exists(registry_path):
        return "Д-0001"

    try:
        wb = load_workbook(registry_path)
        ws = wb.active
        last_row = ws.max_row
        if last_row <= 1:  # Проверяем, есть ли строки с данными (не только заголовок)
            return "Д-0001"

        # Ищем последнюю непустую ячейку в столбце A, начиная с конца
        for row_idx in range(last_row, 1, -1):
            cell_value = ws[f"A{row_idx}"].value
            if cell_value and isinstance(cell_value, str) and cell_value.startswith("Д-"):
                try:
                    last_num = int(cell_value.split('-')[1])
                    return f"Д-{str(last_num + 1).zfill(4)}"
                except (IndexError, ValueError):
                    continue  # Если формат неверный, ищем дальше вверх
        # Если не нашли подходящий номер
        return "Д-0001"
    except Exception as e:
        print(f"Ошибка генерации номера договора: {e}")
        # В случае любой ошибки, лучше вернуть базовый номер
        return "Д-0001"


def _prepare_context_for_tpl(data: ContractData) -> Dict[str, any]:
    """Подготовка словаря (контекста) для docxtpl."""
    total_amount = clean_number(data.totalPrice)
    initial_payment = clean_number(data.initialPayment)



    # Не допускаем отрицательных значений
    # Осторожно с делением на 0, если total_amount может быть 0
    contract_date = parse_date(data.contractDate)  # Предполагаем, что parse_date возвращает datetime объект
    print(data.contractDate)
    if data.jkName == "ЖК_Бахор":
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
    total_months_left = max(total_months_left, 0)
    monthly_payment = (
                              total_amount - initial_payment) / total_months_left if total_amount and initial_payment is not None else 0

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


def _update_registry(registry_path: str, data: ContractData) -> None:
    # ... (без изменений, но проверьте заголовки и порядок данных)
    headers = [
        "№ Договора", "Дата Договора", "Блок", "Этаж", "№ КВ", "Кол-во ком",
        "Квадратура Квартиры", "Общ Стоимость Договора", "Стоимость 1 кв.м",
        "Процент 1 Взноса", "Сумма 1 Взноса", "Ф/И/О", "Серия Паспорта",
        "ПИНФЛ", "Кем выдан", "Адрес прописки", "Номер тел", "Отдел Продаж"
    ]

    # Используем очищенные числовые значения там, где это нужно для реестра

    total_amount = clean_number(data.totalPrice)
    price_m2 = clean_number(data.pricePerM2)
    initial_payment = clean_number(data.initialPayment)

    row = [
        data.contractNumber,
        data.contractDate,  # Дата как строка
        data.block,
        data.floor,
        data.apartmentNumber,
        data.rooms,
        data.size,  # Квадратура как строка? Или число?
        total_amount,  # Числовое значение для возможного анализа в Excel
        price_m2,  # Числовое значение
        (data.paymentChoice or "").replace("%", ""),  # Процент как строка без %
        initial_payment,  # Числовое значение
        data.fullName,
        data.passportSeries,
        data.pinfl,
        data.issuedBy,
        data.registrationAddress,
        data.phone,
        data.salesDepartment
    ]
    # Проверка типов данных перед добавлением
    final_row = []
    for item in row:
        # Даты оставляем как строки или конвертируем в datetime для Excel?
        # Если Excel должен понимать как дату, то:
        # parsed_date = parse_date(item) if isinstance(item, str) and "." in item else item # Пример
        final_row.append(item if item is not None else "")  # Заменяем None на пустую строку для Excel

    try:
        wb = load_workbook(registry_path) if os.path.exists(registry_path) else Workbook()
        ws = wb.active
        # Проверяем, пустой ли лист или только заголовки
        if ws.max_row == 0 or (ws.max_row == 1 and all(c.value is None for c in ws[1])):
            print("Добавляем заголовки в реестр")
            ws.append(headers)

        print(f"Добавляем строку в реестр: {final_row}")
        ws.append(final_row)
        wb.save(registry_path)
        print(f"Реестр сохранен: {registry_path}")

    except Exception as e:
        print(f"Ошибка обновления реестра: {e}")
        import traceback

        print(traceback.format_exc())
        # Можно перевыбросить исключение или обработать иначе
        # raise HTTPException(status_code=500, detail=f"Ошибка обновления реестра: {str(e)}")


@router.get("/download-contract-registry")
async def download_contract_registry(jkName: str):
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    if not os.path.exists(REGISTRY_PATH):
        raise HTTPException(status_code=404, detail="Реестр договоров не найден")

    return FileResponse(
        REGISTRY_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"contract_registry_{jkName}.xlsx"
    )


@router.get("/get-contract-registry")
async def get_contract_registry(jkName: str):
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    if not os.path.exists(REGISTRY_PATH):
        raise HTTPException(status_code=404, detail="Реестр договоров не найден")

    try:
        wb_registry = load_workbook(REGISTRY_PATH)
        ws_registry = wb_registry.active
        data = []

        # Читаем заголовки из первой строки
        headers = [cell.value for cell in ws_registry[1]]

        # Читаем данные из остальных строк
        for row in ws_registry.iter_rows(min_row=2, values_only=True):
            row_data = dict(zip(headers, row))
            data.append(row_data)

        return {"registry": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении реестра: {str(e)}")


NEW_STATUS_ON_DELETE = "свободна"  # Статус, который нужно установить в шахматке
REGISTRY_COLUMN_HEADERS = {
    "contractNumber": "№ Договора",  # Пример
    "block": "Блок",  # Пример
    "floor": "Этаж",  # Пример
    "apartmentNumber": "№ КВ"  # Пример
}


@router.delete("/delete-contract-from-registry")
async def delete_contract_from_registry_and_update_shaxmatka(  # Переименовал для ясности
        jkName: str = Query(..., description="Название жилого комплекса"),
        contractNumber: str = Query(..., description="Номер договора для удаления (например, Д-0001)")
):
    """
    Удаляет строку из реестра договоров и обновляет статус
    соответствующей квартиры в шахматке на 'свободна'.
    """
    print(f"Запрос на удаление договора и обновление шахматки: ЖК='{jkName}', Номер='{contractNumber}'")
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    if not os.path.exists(REGISTRY_PATH):
        print(f"Ошибка: Реестр не найден по пути {REGISTRY_PATH}")
        raise HTTPException(status_code=404, detail=f"Реестр договоров для ЖК '{jkName}' не найден")

    apartment_details = None  # Словарь для хранения данных квартиры из реестра
    found_row_index = None
    registry_headers = []

    try:
        wb_registry = load_workbook(REGISTRY_PATH)
        ws_registry = wb_registry.active

        # Читаем заголовки реестра из первой строки
        registry_headers = [cell.value for cell in ws_registry[1]]
        print(f"Заголовки реестра: {registry_headers}")

        # --- Определяем индексы нужных колонок в реестре ---
        try:
            col_idx_contract = registry_headers.index(REGISTRY_COLUMN_HEADERS["contractNumber"])
            col_idx_block = registry_headers.index(REGISTRY_COLUMN_HEADERS["block"])
            col_idx_floor = registry_headers.index(REGISTRY_COLUMN_HEADERS["floor"])
            col_idx_apt_num = registry_headers.index(REGISTRY_COLUMN_HEADERS["apartmentNumber"])
        except ValueError as e:
            print(f"Критическая ошибка: Не найдены необходимые заголовки в реестре {REGISTRY_PATH}. Ошибка: {e}")
            raise HTTPException(status_code=500,
                                detail=f"Ошибка конфигурации реестра: отсутствуют необходимые колонки ({e}).")

        # Ищем строку для удаления в реестре и извлекаем данные
        for idx, row_values in enumerate(ws_registry.iter_rows(min_row=2, values_only=True), start=2):
            current_contract_num = str(row_values[col_idx_contract]).strip() if row_values[col_idx_contract] else ""

            if current_contract_num == contractNumber.strip():
                found_row_index = idx
                print(f"Найден договор '{contractNumber}' в реестре, строка {found_row_index}")
                try:
                    # Извлекаем данные квартиры, обрабатывая возможные ошибки типа
                    apt_block = str(row_values[col_idx_block]).strip()
                    apt_floor = int(row_values[col_idx_floor])
                    apt_num = int(row_values[col_idx_apt_num])

                    if not apt_block:  # Проверяем, что блок не пустой
                        raise ValueError("Название блока не может быть пустым")

                    apartment_details = {
                        "blockName": apt_block,
                        "floor": apt_floor,
                        "apartmentNumber": apt_num
                    }
                    print(f"Извлечены данные квартиры из реестра: {apartment_details}")
                    break  # Строка найдена, выходим из цикла
                except (ValueError, TypeError, IndexError) as e:
                    print(
                        f"Ошибка извлечения данных квартиры из строки {found_row_index} реестра: {e}. Данные: {row_values}")
                    raise HTTPException(status_code=500,
                                        detail=f"Ошибка данных в реестре для договора {contractNumber} (строка {found_row_index}): {e}")
        # --- Конец поиска в реестре ---

        if found_row_index is None:
            print(f"Ошибка: Договор '{contractNumber}' не найден в реестре {REGISTRY_PATH}")
            raise HTTPException(status_code=404, detail=f"Договор '{contractNumber}' не найден в реестре ЖК '{jkName}'")

        # 1. Удаляем строку из реестра
        ws_registry.delete_rows(found_row_index)
        print(f"Строка {found_row_index} помечена для удаления из реестра.")

        # Сохраняем изменения в файле реестра ПЕРЕД обновлением шахматки
        # Это менее атомарно, но проще в реализации. Если обновление шахматки не удастся,
        # реестр уже будет изменен.
        try:
            wb_registry.save(REGISTRY_PATH)
            print(f"Реестр сохранен: {REGISTRY_PATH}")
        except PermissionError:
            print(
                f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось сохранить реестр {REGISTRY_PATH} после удаления строки. Файл может быть открыт.")
            # Важно сообщить об ошибке, так как реестр не обновлен
            raise HTTPException(status_code=500,
                                detail="Не удалось сохранить изменения в реестре после удаления строки. Возможно, файл открыт.")
        except Exception as save_err:
            print(
                f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось сохранить реестр {REGISTRY_PATH} после удаления строки. Ошибка: {save_err}")
            raise HTTPException(status_code=500, detail=f"Неизвестная ошибка при сохранении реестра: {save_err}")

        # 2. Обновляем статус в шахматке
        shaxmatka_updated = False
        if apartment_details:
            shaxmatka_path = EXCEL_FILE_PATHS.get(jkName)
            if not shaxmatka_path:
                print(f"Предупреждение: Путь к файлу шахматки для ЖК '{jkName}' не найден в конфигурации.")
                # Реестр обновлен, но шахматку обновить не можем. Вернем успех с предупреждением.
                return {
                    "status": "warning",
                    "message": f"Договор '{contractNumber}' удален из реестра, но конфигурация шахматки для '{jkName}' отсутствует."
                }
            if not os.path.exists(shaxmatka_path):
                print(f"Предупреждение: Файл шахматки не найден по пути: {shaxmatka_path}")
                return {
                    "status": "warning",
                    "message": f"Договор '{contractNumber}' удален из реестра, но файл шахматки не найден: {shaxmatka_path}."
                }

            update_data = ApartmentStatusUpdate(
                jkName=jkName,
                blockName=apartment_details["blockName"],
                floor=apartment_details["floor"],
                apartmentNumber=apartment_details["apartmentNumber"],
                newStatus=NEW_STATUS_ON_DELETE  # Устанавливаем статус "свободна"
            )
            print(f"Попытка обновить статус в шахматке: {update_data.dict()}")
            shaxmatka_updated = find_row_and_update_status(shaxmatka_path, update_data)
        else:
            # Это не должно произойти, если мы дошли до сюда, но на всякий случай
            print("Критическая ошибка: Данные квартиры не были извлечены из реестра.")
            # Реестр уже сохранен без строки. Сообщаем об успехе удаления, но с ошибкой данных.
            return {
                "status": "error",  # Или warning?
                "message": f"Договор '{contractNumber}' удален из реестра, но произошла ошибка при получении данных квартиры для обновления шахматки."
            }

        # Формируем финальный ответ
        if shaxmatka_updated:
            return {
                "status": "success",
                "message": f"Договор '{contractNumber}' удален из реестра, статус квартиры в шахматке обновлен на '{NEW_STATUS_ON_DELETE}'."
            }
        else:
            # Реестр обновлен, но шахматка - нет (квартира не найдена там или ошибка сохранения)
            return {
                "status": "warning",  # Используем warning, так как основное действие (удаление) выполнено
                "message": f"Договор '{contractNumber}' удален из реестра, НО не удалось обновить статус в шахматке (квартира не найдена или произошла ошибка при сохранении шахматки)."
            }

    except FileNotFoundError:
        print(f"Критическая ошибка: FileNotFoundError для {REGISTRY_PATH} после проверки существования.")
        raise HTTPException(status_code=404,
                            detail=f"Реестр договоров для ЖК '{jkName}' не найден (ошибка после проверки).")
    except HTTPException as http_err:
        # Перехватываем HTTPException, чтобы не попасть в общий Exception
        raise http_err
    except Exception as e:
        print(f"Непредвиденная ошибка при удалении/обновлении: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке запроса: {str(e)}")


import os


# Получить список всех ЖК (папок в BASE_STATIC_PATH)
@router.get("/complexes", summary="List all residential complexes")
async def list_complexes():
    """
    Возвращает список папок (названий ЖК) в каталоге BASE_STATIC_PATH.
    """
    complexes_dir = BASE_STATIC_PATH
    try:
        if not os.path.exists(complexes_dir):
            return {"complexes": []}
        items = [
            name for name in os.listdir(complexes_dir)
            if os.path.isdir(os.path.join(complexes_dir, name))
        ]
        return {"complexes": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении списка ЖК: {e}")


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
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении файлов ЖК: {e}")


# --- Новый эндпоинт: Получить price_shaxamtka.xlsx как JSON ---
@router.get("/complexes/{jkName}/price", summary="Get price data for a given residential complex")
async def get_price(jkName: str):
    """
    Возвращает содержимое файла price_shaxamtka.xlsx в папке ЖК в виде JSON:
    {
      "headers": [...],
      "rows": [{header1: value1, ...}, ...]
    }
    """
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    file_path = os.path.join(jk_dir, "price_shaxamtka.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Price file not found for '{jkName}'")
    # Load workbook
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active
    # Read header row
    headers = [cell.value for cell in ws[1]]
    # Read data rows
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_dict = {headers[i]: row[i] for i in range(len(headers))}
        rows.append(row_dict)
    return {"headers": headers, "rows": rows}


@router.put("/complexes/{jkName}/price", summary="Update price data for a given residential complex")
async def update_price(
        jkName: str,
        data: Dict[str, Any] = Body(...,
                                    description="JSON с ключами 'headers' (list) и 'rows' (list of dict)")
):
    headers = data.get("headers")
    rows = data.get("rows")

    # Validation
    if not headers or not rows:
        raise HTTPException(status_code=400, detail="Headers and rows must be provided")

    # Определяем директорию комплекса и путь к файлу
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    file_path = os.path.join(jk_dir, "price_shaxamtka.xlsx")

    if not os.path.isdir(jk_dir):
        raise HTTPException(status_code=404, detail=f"Residential complex '{jkName}' not found")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Price file not found for '{jkName}'")

    try:
        # Загружаем Excel файл
        wb = load_workbook(file_path)
        ws = wb.active

        # Читаем заголовки из Excel
        excel_headers = [cell.value for cell in ws[1]]

        # Создаем маппинг заголовок -> индекс колонки (1-based)
        col_map = {str(h): i + 1 for i, h in enumerate(excel_headers)}

        # Находим индекс колонки "Этаж" (обычно первая колонка)
        floor_col_idx = None
        for i, header in enumerate(excel_headers):
            if isinstance(header, str) and "этаж" in header.lower():
                floor_col_idx = i + 1
                break

        if floor_col_idx is None:
            # Если колонка "Этаж" не найдена, предполагаем что это первая колонка
            floor_col_idx = 1

        # Обновляем данные в Excel
        for row_idx, row_data in enumerate(rows, start=2):  # Excel rows are 1-indexed, header is row 1
            for header, value in row_data.items():
                col_idx = col_map.get(str(header))

                # Пропускаем колонку "Этаж"
                if col_idx is not None and col_idx != floor_col_idx:
                    # Конвертируем значение в число если это цена
                    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                        value = int(value)  # Убеждаемся что это целое число

                    # Обновляем ячейку
                    ws.cell(row=row_idx, column=col_idx, value=value)

        # Сохраняем изменения
        wb.save(file_path)

        return {"status": "success", "message": f"Price file updated for '{jkName}'"}

    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Error updating price file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating price file: {str(e)}")


class ChessUpdate(BaseModel):
    apt: str
    status: str


class ChessUpdates(BaseModel):
    updates: List[ApartmentStatusUpdate]


@router.get("/complexes/{jkName}/chess", summary="Get full chess grid")
async def get_chess(jkName: str):
    jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
    path = os.path.join(jk_dir, "jk_data.xlsx")
    if not os.path.exists(path):
        raise HTTPException(404, "Шахматка не найдена")

    wb = load_workbook(path)
    ws = wb.active

    # Считываем заголовки из первой строки
    headers = [cell.value for cell in ws[1]]

    grid = []
    # Проходим по строкам с 2 по max_row
    for i in range(2, ws.max_row + 1):
        row_obj = {}
        for j, h in enumerate(headers, start=1):
            row_obj[h] = ws.cell(row=i, column=j).value
        grid.append(row_obj)

    return {"grid": grid}


@router.put("/complexes/chess", summary="Update chess grid statuses")
async def update_chess(data: ChessUpdates):
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
    not_found = []
    for upd in data.updates:
        jk_dir = os.path.join(BASE_STATIC_PATH, upd.jkName)
        path = os.path.join(jk_dir, "jk_data.xlsx")
        if not os.path.exists(path):
            not_found.append(f"{upd.jkName}: файл не найден")
            continue

        success = find_row_and_update_status(path, upd)
        if not success:
            not_found.append(
                f"{upd.jkName} — Блок={upd.blockName}, этаж={upd.floor}, кв={upd.apartmentNumber}"
            )

    if not_found:
        raise HTTPException(status_code=404, detail={"not_updated": not_found})

    return {"detail": "Все статусы успешно сохранены"}


# --- Новый эндпоинт для замены файла в папке ЖК ---
@router.post("/replace-file", summary="Replace a file in a given residential complex")
async def replace_file(
        name: str = Form(..., description="Название жилого комплекса (jkName)"),
        category: str = Form(..., description="Категория файла: 'jk_data', 'price', 'template'"),
        file: UploadFile = File(..., description="Загружаемый файл")
):
    """
    Загружает новый файл и заменяет существующий в папке ЖК.
    """
    # Определяем директорию комплекса
    complex_dir = os.path.join(BASE_STATIC_PATH, name)
    if not os.path.isdir(complex_dir):
        raise HTTPException(status_code=404, detail=f"ЖК '{name}' не найден")

    # Определяем имя файла на сервере по категории
    filename_map = {
        "jk_data": "jk_data.xlsx",
        "price": "price_shaxamtka.xlsx",
        "template": "contract_template.docx"
    }
    target_filename = filename_map.get(category)
    if not target_filename:
        raise HTTPException(status_code=400, detail=f"Неизвестная категория файла: {category}")

    target_path = os.path.join(complex_dir, target_filename)
    # Сохраняем загруженный файл, перезаписывая существующий
    try:
        with open(target_path, "wb") as out_file:
            shutil.copyfileobj(file.file, out_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {e}")

    return {"status": "success", "message": f"Файл '{target_filename}' заменён в ЖК '{name}'"}


# --- Новый эндпоинт: Получить все забронированные квартиры ---
@router.get("/reserved-apartments", summary="Get reserved apartments for a given residential complex")
async def get_reserved_apartments(jkName: str):
    file_path = EXCEL_FILE_PATHS.get(jkName)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Excel file not found for '{jkName}'")
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    block_col = col_letter_to_index(COLUMN_MAPPING["blockName"])
    floor_col = col_letter_to_index(COLUMN_MAPPING["floor"])
    apt_col = col_letter_to_index(COLUMN_MAPPING["apartmentNumber"])
    status_col = col_letter_to_index(COLUMN_MAPPING["status"])

    reserved = []
    for row_idx in range(DATA_START_ROW, ws.max_row + 1):
        status_val = ws.cell(row=row_idx, column=status_col).value
        if str(status_val).strip().lower() == "бронь":
            reserved.append({
                "blockName": ws.cell(row=row_idx, column=block_col).value,
                "floor": ws.cell(row=row_idx, column=floor_col).value,
                "apartmentNumber": ws.cell(row=row_idx, column=apt_col).value
            })
    return {"reservedApartments": reserved}


# --- Новый эндпоинт: Получить статус конкретной квартиры ---
@router.get("/apartment-status", summary="Get status of a specific apartment")
async def get_apartment_status(
        jkName: str = Query(..., description="Name of the residential complex"),
        blockName: str = Query(..., description="Block name"),
        floor: int = Query(..., description="Floor number"),
        apartmentNumber: Union[int, str] = Query(..., description="Apartment number")
):
    file_path = EXCEL_FILE_PATHS.get(jkName)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Excel file not found for '{jkName}'")
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    block_col = col_letter_to_index(COLUMN_MAPPING["blockName"])
    floor_col = col_letter_to_index(COLUMN_MAPPING["floor"])
    apt_col = col_letter_to_index(COLUMN_MAPPING["apartmentNumber"])
    status_col = col_letter_to_index(COLUMN_MAPPING["status"])

    for row_idx in range(DATA_START_ROW, ws.max_row + 1):
        cell_block = ws.cell(row=row_idx, column=block_col).value
        cell_floor = ws.cell(row=row_idx, column=floor_col).value
        cell_apt = ws.cell(row=row_idx, column=apt_col).value

        if str(cell_block).strip().lower() == blockName.strip().lower() and cell_floor == floor and str(
                cell_apt) == str(apartmentNumber):
            status_val = ws.cell(row=row_idx, column=status_col).value
            return {"apartmentStatus": status_val}
    raise HTTPException(status_code=404, detail="Apartment not found")


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
    """
    filename_map = {
        "jk_data": "jk_data.xlsx",
        "price": "price_shaxamtka.xlsx",
        "template": "contract_template.docx"
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
