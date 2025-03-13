import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Body, Query
from starlette.responses import FileResponse

from backend.core.google_sheets import get_price_data_for_sheet, get_shaxmatka_data, update_shaxmatka_status, \
    SPREADSHEET_ID_REESTR_ID, get_google_sheets_service, read_from_google_sheet, get_all_sheet_names, \
    append_to_google_sheet, SPREADSHEET_ID_LID_ID, get_google_sheets_data

router = APIRouter(prefix='/api/complexes')


@router.get('/')
async def get_complexes():
    base_dir = os.path.join('static', 'images', 'Жилые_Комплексы')
    complexes = []

    # Сканируем папку "Жилые_Комплексы"
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path):
            render_path = os.path.join(folder_path, 'render')
            renders = []
            if os.path.exists(render_path):
                renders = [
                    f"/static/images/Жилые_Комплексы/{folder_name}/render/{file}"
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
    # if jk_name not in shaxmatka_cache:
    #     available_jks = list(shaxmatka_cache.keys())
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"Данные для ЖК {jk_name} не найдены. Доступные ЖК: {available_jks}"
    #     )

    shaxmatka_data = shaxmatka_cache
    render_folder = os.path.join('static', 'images', 'Жилые_Комплексы', jk_name, 'render')
    render_image = None

    if os.path.exists(render_folder):
        images = [
            f"/static/images/Жилые_Комплексы/{jk_name}/render/{img}"
            for img in os.listdir(render_folder)
            if img.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        render_image = images[0] if images else None

    # Пример обработки данных, аналогичный исходному коду
    for row in shaxmatka_data:
        if row[2].lower() == "свободна":
            try:
                floor = int(row[6])
                area = float(row[5].replace(',', '.'))
                # Предположим, что цена также кэшируется отдельной функцией (пример ниже)
                price_data = await get_price_data_for_sheet(jk_name)
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
        else:
            row.append(None)

    return {"status": "success", "shaxmatka": shaxmatka_data, "render": render_image}


@router.get("/plan-image")
async def get_plan_image(
        jkName: str = Query(..., alias="jkName"),
        blockName: str = Query(..., alias="blockName"),
        apartmentSize: str = Query(..., alias="apartmentSize")
):
    """
    Возвращает изображение планировки, если оно существует.
    Параметры: jkName, blockName, apartmentSize
    """
    if not all([jkName, blockName, apartmentSize]):
        raise HTTPException(status_code=400, detail="Отсутствуют обязательные параметры")

    # Путь к директории с изображениями
    base_path = os.path.join(
        'static', 'images', 'Жилые_Комплексы',
        jkName, 'Planirovki', blockName
    )
    print(f"Looking for plans in: {base_path}")
    # Проверяем, существует ли директория
    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail="Планировки для указанного ЖК не найдены")

    possible_files = [f"{apartmentSize}.{ext}" for ext in ['jpg', 'jpeg', 'png', 'svg']]

    for file_name in possible_files:
        file_path = os.path.join(base_path, file_name)
        if os.path.exists(file_path):
            return FileResponse(file_path)

        print(f"Looking for plans in: {base_path}")
        if not os.path.exists(base_path):
            print("Plan directory does not exist.")
        else:
            print(f"Files in plan directory: {os.listdir(base_path)}")

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
                row_size = float(row[5].replace(',', '.')) if row[5] else None

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
        price_key_100 = f"{jkName}_{floor}_100"
        price_key_70 = f"{jkName}_{floor}_70"
        price_key_50 = f"{jkName}_{floor}_50"
        price_key_30 = f"{jkName}_{floor}_30"
        price_data_30 = await get_price_data_for_sheet(price_key_30)
        if isinstance(price_data_30, dict):
            try:
                # Если словарь содержит единственное значение, берем его
                price_30 = float(next(iter(price_data_30.values())))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка извлечения цены для ключа {price_key_30}: {e}")
        else:
            price_30 = float(price_data_30)

        price_data_100 = await get_price_data_for_sheet(price_key_100)
        if isinstance(price_data_100, dict):
            try:
                price_100 = float(next(iter(price_data_100.values())))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка извлечения цены для ключа {price_key_100}: {e}")
        else:
            price_100 = float(price_data_100)

        price_data_70 = await get_price_data_for_sheet(price_key_70)
        if isinstance(price_data_70, dict):
            try:
                price_70 = float(next(iter(price_data_70.values())))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка извлечения цены для ключа {price_key_70}: {e}")
        else:
            price_70 = float(price_data_70)

        price_data_50 = await get_price_data_for_sheet(price_key_50)
        if isinstance(price_data_50, dict):
            try:
                price_50 = float(next(iter(price_data_50.values())))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка извлечения цены для ключа {price_key_50}: {e}")
        else:
            price_50 = float(price_data_50)

        if None in [price_100, price_70, price_50, price_30]:
            raise HTTPException(status_code=404,
                                detail="Не найдены цены для некоторых вариантов оплаты. Проверьте кэш.")

        try:
            size = float(apartmentSize.replace(',', '.'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат размера квартиры")

        total_price = size * price_30
        print(f"price_30={price_30}, calculated total_price={total_price}")

        # Вычисляем оставшиеся месяцы (пример: до 30 июня 2027)
        current_date = datetime.now()
        end_date = datetime(2027, 6, 30)
        months_left = (end_date.year - current_date.year) * 12 + (end_date.month - current_date.month)

        return {
            "status": "success",
            "data": {
                "pricePerM2_100": round(price_100),
                "pricePerM2_70": round(price_70),
                "pricePerM2_50": round(price_50),
                "pricePerM2_30": round(price_30),
                "total_price": round(total_price),
                "status": apartment_status,
                "floor": floor,
                "size": apartmentSize,
                "months_left": months_left
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lid/data")
async def api_lid_data(jkName: str = Query(..., alias="jkName")):
    """
    Возвращает данные из таблицы Лид для заданного ЖК (лист).
    """
    if not jkName:
        raise HTTPException(status_code=400, detail="Параметр 'jkName' обязателен")

    sheet_name = f"{jkName}"
    range_name = f"{sheet_name}!A2:E"

    existing_sheets = get_all_sheet_names(SPREADSHEET_ID_LID_ID)
    if sheet_name not in existing_sheets:
        raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден")

    data = get_google_sheets_data(SPREADSHEET_ID_LID_ID, range_name)
    if isinstance(data, dict) and "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])

    return {"status": "success", "data": data}


@router.post("/lid/register")
async def register_client(data: Dict[str, Any] = Body(...)):
    """
    Регистрирует нового клиента (Лид) в Google Sheets и обновляет статус квартиры на "Бронь".
    """
    name = data.get('name')
    phone = data.get('phone')
    apartment_number = data.get('apartmentNumber')
    apartment_details = data.get('apartmentDetails')
    jk_name = data.get('jkName')
    block_name = data.get('block')

    if not all([name, phone, apartment_number, apartment_details, jk_name, block_name]):
        raise HTTPException(
            status_code=400,
            detail="Все поля (name, phone, apartmentNumber, apartmentDetails, jkName, block) обязательны"
        )

    sheet_name = f"{jk_name}"
    range_name = f"{sheet_name}!A2:E"

    existing_sheets = get_all_sheet_names(SPREADSHEET_ID_LID_ID)
    if sheet_name not in existing_sheets:
        raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = [timestamp, name, phone, apartment_number, apartment_details]

    append_result = append_to_google_sheet(SPREADSHEET_ID_LID_ID, range_name, [new_row])
    if "error" in append_result:
        raise HTTPException(status_code=500, detail=append_result["error"])

    # Обновляем статус в шахматке на "Бронь"
    update_result = update_shaxmatka_status(jk_name, block_name, apartment_number, "Бронь")
    if "error" in update_result:
        raise HTTPException(status_code=500, detail=update_result["error"])

    return {"status": "success", "message": "Бронь успешно зарегистрирована"}


@router.get("/last-contract-number")
async def get_last_contract_number(jkName: str = Query(..., alias="jkName")):
    """
    Возвращает следующий номер договора для указанного ЖК, основываясь на существующих данных в Google Sheets (реестр).
    """
    if not jkName:
        raise HTTPException(status_code=400, detail="Имя ЖК обязательно")

    sheet_name = jkName
    range_name = f"{sheet_name}!A2:A"

    result = read_from_google_sheet(SPREADSHEET_ID_REESTR_ID, range_name)
    if not result:
        # Если данных нет, начинаем с 1
        return {"status": "success", "lastContractNumber": 1}

    contract_numbers = [int(row[0]) for row in result if row and row[0].isdigit()]
    last_contract_number = max(contract_numbers) if contract_numbers else 0

    return {"status": "success", "lastContractNumber": last_contract_number + 1}


@router.post("/reestr/register_or_update")
async def register_or_update_contract(data: Dict[str, Any] = Body(...)):
    """
    Создаёт или обновляет запись договора в реестре (Google Sheets) и при необходимости меняет статус квартиры на "Продана".
    """
    try:
        jk_name = data.get("jkName")
        block_name = data.get("block")
        apartment_number = data.get("apartmentNumber")
        contract_number = data.get("contractNumber")

        if not all([jk_name, block_name, apartment_number, contract_number]):
            raise HTTPException(
                status_code=400,
                detail="Все поля (jkName, block, apartmentNumber, contractNumber) обязательны."
            )

        sheet_name = jk_name
        range_name = f"{sheet_name}!A2:R"

        existing_sheets = get_all_sheet_names(SPREADSHEET_ID_REESTR_ID)
        if sheet_name not in existing_sheets:
            raise HTTPException(status_code=404, detail=f"Лист '{sheet_name}' не найден.")

        contract_data = [
            data.get("contractNumber"),
            data.get("contractDate"),
            data.get("block"),
            data.get("floor"),
            data.get("apartmentNumber"),
            data.get("rooms"),
            data.get("size"),
            data.get("totalPrice"),
            data.get("pricePerM2"),
            data.get("paymentChoice"),
            data.get("initialPayment"),
            data.get("fullName"),
            data.get("passportSeries"),
            data.get("pinfl"),
            data.get("issuedBy"),
            data.get("registrationAddress"),
            data.get("phone"),
            data.get("salesDepartment")
        ]

        # Проверяем, что все поля заполнены
        if not all(contract_data):
            raise HTTPException(status_code=400, detail="Все поля обязательны для заполнения.")

        # Читаем существующие данные реестра
        existing_data = read_from_google_sheet(SPREADSHEET_ID_REESTR_ID, range_name)
        row_index = None
        for i, row in enumerate(existing_data or []):
            # Сравниваем номер договора (первый столбец)
            if len(row) > 0 and str(row[0]) == str(contract_number):
                row_index = i + 2  # +2, учитывая заголовок
                break

        service = get_google_sheets_service()

        # Если договор уже есть — обновляем
        if row_index:
            range_to_update = f"{sheet_name}!A{row_index}:R{row_index}"
            body = {"values": [contract_data]}
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID_REESTR_ID,
                range=range_to_update,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return {"status": "success", "message": f"Договор с номером {contract_number} успешно обновлен."}

        # Иначе — добавляем новую запись
        body = {"values": [contract_data]}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID_REESTR_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        # Меняем статус квартиры на "Продана"
        update_result = update_shaxmatka_status(jk_name, block_name, apartment_number, "Продана")
        if "error" in update_result:
            raise HTTPException(status_code=500, detail=update_result["error"])

        return {"status": "success", "message": "Договор успешно создан."}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при обработке договора: {e}")
        raise HTTPException(status_code=500, detail=str(e))
