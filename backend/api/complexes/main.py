import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict

import fitz
from fastapi import APIRouter, HTTPException, Body, Query, UploadFile, File, Form
from starlette.responses import FileResponse

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

    shaxmatka_data = shaxmatka_cache
    render_folder = os.path.join('static', 'Жилые_Комплексы', jk_name, 'render')
    render_image = None

    if os.path.exists(render_folder):
        images = [
            f"/static/Жилые_Комплексы/{jk_name}/render/{img}"
            for img in os.listdir(render_folder)
            if img.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        render_image = images[1] if images else images[0]

    # Пример обработки данных, аналогичный исходному коду
    for row in shaxmatka_data:
        # print(row[2])
        if row[2].strip().lower() in "свободна ":
            try:
                floor = int(row[6])
                area = float(row[5])
                # Предположим, что цена также кэшируется отдельной функцией (пример ниже)
                price_data = await get_price_data_for_sheet_all(jk_name)
                # Здесь производится поиск цены для этажа и расчёт
                # Например:
                price_30 = None
                if price_data:
                    for item in price_data:
                        try:
                            if int(item[0]) == floor:
                                price_30 = float(item[4])
                                break
                        except (ValueError, IndexError):
                            continue
                if price_30:
                    total_price_30 = round(price_30 * area)
                    row.append(total_price_30)
                else:
                    row.append(None)
            except (ValueError, TypeError) as e:
                print(f"Ошибка обработки строки {row}: {e}")
                row.append(None)
        # else:
        #     row.append(None)

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


@router.get("/apartment-info")
async def get_apartment_info(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize"),
        floor: str = Query(..., alias="floor")
):
    """
    Возвращает информацию о квартире (статус, цены, площадь, кол-во месяцев до конца периода и т.д.).
    Параметры: jkName, blockName, apartmentSize, floor
    """
    print(
        f"Запрос к /api/apartment-info: jk_name={jkName}, block_name={blockName}, apartment_size={apartmentSize}, floor={floor}")

    if not all([jkName, blockName, apartmentSize, floor]):
        raise HTTPException(status_code=400, detail="Отсутствуют обязательные параметры")

    try:
        shaxmatka_data = await get_shaxmatka_data(jkName)
        if not shaxmatka_data:
            print(f"Данные для ЖК {jkName} не найдены в кэше.")
            raise HTTPException(status_code=404, detail=f"Данные для ЖК {jkName} не найдены.")

        apartment_status = None
        for row in shaxmatka_data:
            try:
                row_block = row[0].strip().lower() if isinstance(row[0], str) else str(row[0]).lower()
                row_floor = int(row[6]) if row[6] else None
                row_size = float(row[5]) if row[5] else None

                if (
                        row_block == blockName.lower() and
                        row_floor == int(floor) and
                        row_size == float(apartmentSize.replace(',', '.'))
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
            raise HTTPException(status_code=404, detail="Квартира не найдена.")

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
        current_date = datetime.now()
        end_date = datetime(2027, 6, 30)
        months_left = (end_date.year - current_date.year) * 12 + (end_date.month - current_date.month)

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
                "months_left": months_left
            }
        }
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#
# @router.get("/lid/data")
# async def api_lid_data(jkName: str = Query(..., alias="jkName")):
#     """
#     Возвращает данные из таблицы Лид для заданного ЖК (лист).
#     """
#     if not jkName:
#         raise HTTPException(status_code=400, detail="Параметр 'jkName' обязателен")
#
#     sheet_name = f"{jkName}"
#     range_name = f"{sheet_name}!A2:E"
#
#     existing_sheets = get_all_sheet_names(SPREADSHEET_ID_LID_ID)
#     if sheet_name not in existing_sheets:
#         raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден")
#
#     data = get_google_sheets_data(SPREADSHEET_ID_LID_ID, range_name)
#     if isinstance(data, dict) and "error" in data:
#         raise HTTPException(status_code=500, detail=data["error"])
#
#     return {"status": "success", "data": data}
#
#
# @router.post("/lid/register")
# async def register_client(data: Dict[str, Any] = Body(...)):
#     """
#     Регистрирует нового клиента (Лид) в Google Sheets и обновляет статус квартиры на "Бронь".
#     """
#     name = data.get('name')
#     phone = data.get('phone')
#     apartment_number = data.get('apartmentNumber')
#     apartment_details = data.get('apartmentDetails')
#     jk_name = data.get('jkName')
#     block_name = data.get('block')
#
#     if not all([name, phone, apartment_number, apartment_details, jk_name, block_name]):
#         raise HTTPException(
#             status_code=400,
#             detail="Все поля (name, phone, apartmentNumber, apartmentDetails, jkName, block) обязательны"
#         )
#
#     sheet_name = f"{jk_name}"
#     range_name = f"{sheet_name}!A2:E"
#
#     existing_sheets = get_all_sheet_names(SPREADSHEET_ID_LID_ID)
#     if sheet_name not in existing_sheets:
#         raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден")
#
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     new_row = [timestamp, name, phone, apartment_number, apartment_details]
#
#     append_result = append_to_google_sheet(SPREADSHEET_ID_LID_ID, range_name, [new_row])
#     if "error" in append_result:
#         raise HTTPException(status_code=500, detail=append_result["error"])
#
#     # Обновляем статус в шахматке на "Бронь"
#     update_result = update_shaxmatka_status(jk_name, block_name, apartment_number, "Бронь")
#     if "error" in update_result:
#         raise HTTPException(status_code=500, detail=update_result["error"])
#
#     return {"status": "success", "message": "Бронь успешно зарегистрирована"}
#
#
# @router.get("/last-contract-number")
# async def get_last_contract_number(jkName: str = Query(..., alias="jkName")):
#     """
#     Возвращает следующий номер договора для указанного ЖК, основываясь на существующих данных в Google Sheets (реестр).
#     """
#     if not jkName:
#         raise HTTPException(status_code=400, detail="Имя ЖК обязательно")
#
#     sheet_name = jkName
#     range_name = f"{sheet_name}!A2:A"
#
#     result = read_from_google_sheet(SPREADSHEET_ID_REESTR_ID, range_name)
#     if not result:
#         # Если данных нет, начинаем с 1
#         return {"status": "success", "lastContractNumber": 1}
#
#     contract_numbers = [int(row[0]) for row in result if row and row[0].isdigit()]
#     last_contract_number = max(contract_numbers) if contract_numbers else 0
#
#     return {"status": "success", "lastContractNumber": last_contract_number + 1}
#
#
# @router.post("/reestr/register_or_update")
# async def register_or_update_contract(data: Dict[str, Any] = Body(...)):
#     """
#     Создаёт или обновляет запись договора в реестре (Google Sheets) и при необходимости меняет статус квартиры на "Продана".
#     """
#     try:
#         jk_name = data.get("jkName")
#         block_name = data.get("block")
#         apartment_number = data.get("apartmentNumber")
#         contract_number = data.get("contractNumber")
#
#         if not all([jk_name, block_name, apartment_number, contract_number]):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Все поля (jkName, block, apartmentNumber, contractNumber) обязательны."
#             )
#
#         sheet_name = jk_name
#         range_name = f"{sheet_name}!A2:R"
#
#         existing_sheets = get_all_sheet_names(SPREADSHEET_ID_REESTR_ID)
#         if sheet_name not in existing_sheets:
#             raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден.")
#
#         contract_data = [
#             data.get("contractNumber"),
#             data.get("contractDate"),
#             data.get("block"),
#             data.get("floor"),
#             data.get("apartmentNumber"),
#             data.get("rooms"),
#             data.get("size"),
#             data.get("totalPrice"),
#             data.get("pricePerM2"),
#             data.get("paymentChoice"),
#             data.get("initialPayment"),
#             data.get("fullName"),
#             data.get("passportSeries"),
#             data.get("pinfl"),
#             data.get("issuedBy"),
#             data.get("registrationAddress"),
#             data.get("phone"),
#             data.get("salesDepartment")
#         ]
#
#         # Проверяем, что все поля заполнены
#         if not all(contract_data):
#             raise HTTPException(status_code=400, detail="Все поля обязательны для заполнения.")
#
#         # Читаем существующие данные реестра
#         existing_data = read_from_google_sheet(SPREADSHEET_ID_REESTR_ID, range_name)
#         row_index = None
#         for i, row in enumerate(existing_data or []):
#             # Сравниваем номер договора (первый столбец)
#             if len(row) > 0 and str(row[0]) == str(contract_number):
#                 row_index = i + 2  # +2, учитывая заголовок
#                 break
#
#         service = get_google_sheets_service()
#
#         # Если договор уже есть — обновляем
#         if row_index:
#             range_to_update = f"{sheet_name}!A{row_index}:R{row_index}"
#             body = {"values": [contract_data]}
#             service.spreadsheets().values().update(
#                 spreadsheetId=SPREADSHEET_ID_REESTR_ID,
#                 range=range_to_update,
#                 valueInputOption="USER_ENTERED",
#                 body=body
#             ).execute()
#             return {"status": "success", "message": f"Договор с номером {contract_number} успешно обновлен."}
#
#         # Иначе — добавляем новую запись
#         body = {"values": [contract_data]}
#         service.spreadsheets().values().append(
#             spreadsheetId=SPREADSHEET_ID_REESTR_ID,
#             range=f"{sheet_name}!A1",
#             valueInputOption="USER_ENTERED",
#             insertDataOption="INSERT_ROWS",
#             body=body
#         ).execute()
#
#         # Меняем статус квартиры на "Продана"
#         update_result = update_shaxmatka_status(jk_name, block_name, apartment_number, "Продана")
#         if "error" in update_result:
#             raise HTTPException(status_code=500, detail=update_result["error"])
#
#         return {"status": "success", "message": "Договор успешно создан."}
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"Ошибка при обработке договора: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


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
