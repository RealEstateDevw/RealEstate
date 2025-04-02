from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Union
from docx import Document
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Body, Query
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
    "Другой ЖК": os.path.join(BASE_DIR, "data", "shahmatka_drugoy.xlsx"),
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
    contractNumber: Union[str, None] = None  # Сделаем опциональным для генерации
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
    size: float  # Используем float для удобства, или str если нужно точное строковое представление
    totalPrice: str  # Оставляем строкой для форматирования и number_to_words
    pricePerM2: str  # Оставляем строкой
    paymentChoice: str
    initialPayment: str  # Оставляем строкой
    salesDepartment: Union[str, None] = None  # Добавим, так как есть в реестре


# Функция преобразования числа в слова (на русском языке)
def number_to_words(number: str) -> str:
    # Убираем все нечисловые символы и преобразуем в int
    clean_number = ''.join(filter(str.isdigit, number))
    return num2words(int(clean_number), lang='ru') + " сум"


# --- Роутер (остается без изменений) ---
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
        return {"lastContractNumber": None}  # Файл реестра не существует

    try:
        wb_registry = load_workbook(REGISTRY_PATH)
        ws_registry = wb_registry.active
        last_row = ws_registry.max_row

        if last_row <= 1:  # Только заголовок или пустой файл
            return {"lastContractNumber": None}

        last_contract_number = ws_registry[f"A{last_row}"].value  # Предполагается, что номер в колонке A
        return {"lastContractNumber": int(last_contract_number) + 1}
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


@router.post("/generate-contract")
async def generate_contract(data: ContractData):
    jk_dir = os.path.join(BASE_STATIC_PATH, data.jkName)
    TEMPLATE_PATH = os.path.join(jk_dir, "contract_template.xlsx")
    REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")

    if not os.path.exists(jk_dir):
        try:
            os.makedirs(jk_dir)
            print(f"Создана директория: {jk_dir}")
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Не удалось создать директорию: {jk_dir}. Ошибка: {e}")

    if not data.contractNumber:
        next_contract_number_int = 1
        if os.path.exists(REGISTRY_PATH):
            try:
                wb_registry_check = load_workbook(REGISTRY_PATH)
                ws_registry_check = wb_registry_check.active
                last_row = ws_registry_check.max_row
                if last_row > 1:
                    last_contract_val = ws_registry_check[f"A{last_row}"].value
                    if last_contract_val and isinstance(last_contract_val, str) and last_contract_val.startswith("Д-"):
                        try:
                            last_num_str = last_contract_val.split('-')[1]
                            last_contract_number_int = int(last_num_str)
                            next_contract_number_int = last_contract_number_int + 1
                        except (ValueError, IndexError):
                            print(f"Ошибка в формате номера договора: {last_contract_val}")
            except Exception as e:
                print(f"Ошибка чтения реестра: {e}")
        next_contract_number_str = str(next_contract_number_int).zfill(4)
        data.contractNumber = f"Д-{next_contract_number_str}"
        print(f"Сгенерирован номер договора: {data.contractNumber}")

    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail=f"Шаблон договора не найден: {TEMPLATE_PATH}")

    try:
        wb_contract = load_workbook(TEMPLATE_PATH)
        ws_contract = wb_contract.active
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки шаблона: {e}")

    def safe_number_to_words(value_str: str | None) -> str:
        if not value_str:
            return "N/A"
        try:
            return number_to_words(value_str.replace(" ", "").replace("\xa0", ""))
        except Exception as e:
            print(f"Ошибка конвертации '{value_str}' в слова: {e}")
            return "Ошибка конвертации"

    # Используем данные из таблицы
    total_amount = clean_number(data.totalPrice)  # ОБЩ СТОИМОСТЬ ДОГОВОРА
    initial_payment = clean_number(data.initialPayment)  # СУММА 1 ВЗНОСА
    num_payments = 24  # Оставшиеся 23 месяца после первого взноса
    monthly_payment = total_amount / num_payments if num_payments > 0 else 0

    contract_date = parse_date(data.contractDate)

    # Создаем словарь замен для графика финансирования
    payment_replacements = {}
    for i in range(25):
        payment_number = i
        payment_date = contract_date + relativedelta(months=i)
        if i == 0:
            pass
        else:
            # Последующие платежи
            payment_replacements[f"{{{{Дата_Платежа_{payment_number}}}}}"] = payment_date.strftime("%d.%m.%Y")
            payment_replacements[f"{{{{Сумма_Платежа_{payment_number}}}}}"] = f"{monthly_payment:,.0f}".replace(",", " ")
            payment_replacements[f"{{{{Оплачено_{payment_number}}}}}"] = f"{monthly_payment:,.0f}".replace(",", " ")

    # Основной словарь замен
    replacements = {
        "{{Номер_Договора}}": str(data.contractNumber or "N/A"),
        "{{Дата}}": str(data.contractDate or "N/A"),
        "{{Ф_И_О}}": str(data.fullName or "N/A"),
        "{{Серия_Паспорта}}": str(data.passportSeries or "N/A"),
        "{{Кем_Выдан}}": str(data.issuedBy or "N/A"),
        "{{Прописка}}": str(data.registrationAddress or "N/A"),
        "{{Номер_Тел}}": str(data.phone or "N/A"),
        "{{ПИНФЛ}}": str(data.pinfl or "N/A"),
        "{{Блок}}": str(data.block or "N/A"),
        "{{Этаж}}": str(data.floor if data.floor is not None else "N/A"),
        "{{Номер_КВ}}": str(data.apartmentNumber if data.apartmentNumber is not None else "N/A"),
        "{{Кол-во_Ком}}": str(data.rooms if data.rooms is not None else "N/A"),
        "{{Квадратура_Квартиры}}": str(data.size if data.size is not None else "N/A"),
        "{{Общ_Стоимость}}": f"{total_amount:,.0f}".replace(",", " "),  # Берем из данных
        "{{Общ_Стоимость_Про}}": safe_number_to_words(data.totalPrice),
        "{{Стоимость_1_м2}}": data.pricePerM2.replace(" ", "").replace("\xa0", "") if data.pricePerM2 else "N/A",
        "{{Стоимость_1_м2_Про}}": safe_number_to_words(data.pricePerM2),
        "{{Процент_1_Взноса}}": data.paymentChoice.replace("%", "") if data.paymentChoice else "N/A",
        "{{Сумма_1_Взноса}}": f"{initial_payment:,.0f}".replace(",", " "),  # Берем из данных
        "{{Сумма_1_Взноса_Про}}": safe_number_to_words(data.initialPayment),
    }

    # Объединяем основной словарь с заменами для графика финансирования
    replacements.update(payment_replacements)

    # Замена placeholders в ячейках
    for row in ws_contract.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                original_value = cell.value
                modified_value = original_value
                for placeholder, value in replacements.items():
                    if placeholder in modified_value:
                        modified_value = modified_value.replace(placeholder, value)
                if modified_value != original_value:
                    cell.value = modified_value

    # Сохранение в буфер
    contract_buffer = BytesIO()
    try:
        wb_contract.save(contract_buffer)
        contract_buffer.seek(0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения договора: {e}")

    # Обновление реестра
    try:
        if os.path.exists(REGISTRY_PATH):
            wb_registry = load_workbook(REGISTRY_PATH)
            ws_registry = wb_registry.active
        else:
            wb_registry = Workbook()
            ws_registry = wb_registry.active
            ws_registry.append([
                "№ Договора", "Дата Договора", "Блок", "Этаж", "№ КВ", "Кол-во ком",
                "Квадратура Квартиры", "Общ Стоимость Договора", "Стоимость 1 кв.м",
                "Процент 1 Взноса", "Сумма 1 Взноса", "Ф/И/О", "Серия Паспорта",
                "ПИНФЛ", "Кем выдан", "Адрес прописки", "Номер тел", "Отдел Продаж"
            ])

        ws_registry.append([
            data.contractNumber,
            data.contractDate,
            data.block,
            data.floor,
            data.apartmentNumber,
            data.rooms,
            data.size,
            data.totalPrice.replace(" ", "").replace("\xa0", "") if data.totalPrice else None,
            data.pricePerM2.replace(" ", "").replace("\xa0", "") if data.pricePerM2 else None,
            data.paymentChoice.replace("%", "") if data.paymentChoice else None,
            data.initialPayment.replace(" ", "").replace("\xa0", "") if data.initialPayment else None,
            data.fullName,
            data.passportSeries,
            data.pinfl,
            data.issuedBy,
            data.registrationAddress,
            data.phone,
            data.salesDepartment
        ])

        wb_registry.save(REGISTRY_PATH)
        print(f"Реестр обновлен: {REGISTRY_PATH}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления реестра: {e}")

    # Отправка файла клиенту
    contract_filename = f"contract_{data.contractNumber}.xlsx"
    print(f"Отправка файла: {contract_filename}")

    return StreamingResponse(
        contract_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"{contract_filename}\"",
            "Content-Length": str(contract_buffer.getbuffer().nbytes)
        }
    )

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
