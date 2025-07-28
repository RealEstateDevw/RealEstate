import asyncio
import re
import threading
import time
import pandas as pd

from dotenv import load_dotenv
import os

from fastapi import HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

load_dotenv()

# GOOGLE_SHEETS_API_KEY = os.getenv('GOOGLE_SHEETS_API_KEY')
# GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
# SPREADSHEET_ID_SHAXMATKA_ID = os.getenv('SPREADSHEET_ID_SHAXMATKA_ID')
# SPREADSHEET_ID_LID_ID = os.getenv('SPREADSHEET_ID_LID_ID')
# SPREADSHEET_ID_PRICE_ID = os.getenv('SPREADSHEET_ID_PRICE_ID')
# SPREADSHEET_ID_REESTR_ID = os.getenv('SPREADSHEET_ID_REESTR_ID')
# SECRET_KEY = os.getenv('SECRET_KEY')


def col_letter_to_index(letter: str) -> int:
    """
    Преобразует буквенное обозначение столбца в индекс (0-индексация).
    Например: 'A' -> 0, 'G' -> 6.
    """
    letter = letter.upper()
    index = 0
    for char in letter:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


def parse_range(range_string: str):
    """
    Разбирает строку диапазона в формате "[SheetName!]A2:G".
    Если имя листа указано (до знака '!'), оно игнорируется.
    Возвращает:
      - start_row: начальный номер строки,
      - start_col_index: индекс первого столбца,
      - end_col_index: индекс последнего столбца.
    """
    # Если есть разделитель '!', игнорируем часть до него
    if "!" in range_string:
        _, cell_range = range_string.split("!", 1)
    else:
        cell_range = range_string

    # Ожидается формат типа "A2:G"
    match = re.match(r"([A-Z]+)(\d+):([A-Z]+)", cell_range)
    if match:
        start_col, start_row, end_col = match.groups()
        start_row = int(start_row)
        start_col_index = col_letter_to_index(start_col)
        end_col_index = col_letter_to_index(end_col)
        return start_row, start_col_index, end_col_index
    else:
        raise ValueError("Неверный формат диапазона: " + cell_range)


def get_local_excel_data(file_path: str, range_string: str):
    """
    Читает данные из локального Excel-файла по указанному диапазону.
    Имя листа, если указано, игнорируется – всегда используется первый лист файла.
    Диапазон передаётся в формате "[SheetName!]A2:G".
    Возвращает данные в виде списка списков.
    """
    try:
        start_row, start_col_index, end_col_index = parse_range(range_string)
        # Читаем данные из первого листа файла, независимо от указанного имени листа
        df = pd.read_excel(file_path, header=None)
        # Срез данных: строки начинаются с (start_row - 1), так как pandas использует 0-индексацию
        data = df.iloc[start_row - 1:, start_col_index:end_col_index + 1]
        return data.values.tolist()
    except Exception as e:
        print(f"Ошибка при чтении локального файла: {e}")
        return {"error": str(e)}


# Переписываем функцию для получения данных "шахматки" из локального файла
@cache(expire=15, namespace="shaxmatka")
def get_shaxmatka_data(jk_name: str):
    """
    Читает данные файла shaxmatka.xlsx для заданного ЖК.
    Диапазон данных: A2:G.
    Даже если в строке диапазона указано имя листа, используется первый лист файла.
    """
    file_path = os.path.join("static", "Жилые_Комплексы", jk_name, "jk_data.xlsx")
    range_string = "A2:G"  # Теперь имя листа не требуется
    data = get_local_excel_data(file_path, range_string)
    return data


# Переписываем функцию для получения данных цены из локального файла


@cache(expire=15)
def get_price_data_for_sheet(jk_floor_key: str):
    """
    Читает данные из файла price_shaxamtka.xlsx для заданного ЖК.
    Аргумент jk_floor_key формируется как f"{jkName}_{floor}_{suffix}" (например, "ЖК_Бахор_1_30").
    Файл содержит единственную таблицу, поэтому лист не указывается.
    """
    # Извлекаем jkName из ключа (предполагаем, что jkName — первая часть, разделённая знаком '_')
    components = jk_floor_key.split('_')
    if len(components) < 3:
        raise HTTPException(status_code=400, detail="Некорректный формат ключа")
    # jkName составляется из всех компонентов, кроме последних двух
    jkName = '_'.join(components[:-2])
    file_path = os.path.join("static", "Жилые_Комплексы", jkName, "price_shaxamtka.xlsx")
    range_string = "A2:E"  # Листов нет – используем единственный диапазон
    return get_local_excel_data(file_path, range_string)


@cache(expire=15)
def get_price_data_for_sheet_all(sheet_name: str):
    """
    Читает данные файла price.xlsx для заданного ЖК.
    Диапазон данных: A2:E.
    Даже если в строке диапазона указано имя листа, используется первый лист файла.
    """
    file_path = os.path.join("static", "Жилые_Комплексы", sheet_name, "price_shaxamtka.xlsx")
    range_string = "A2:E"  # Имя листа не используется
    price_data = get_local_excel_data(file_path, range_string)
    return price_data


# Получаем данные таблицы Лид для конкретного ЖК. Кэшируем на 60 секунд.
# @cache(expire=600, namespace="lid")
# def get_lid_data(jk_name: str):
#     range_name = f"{jk_name}!A2:E"
#     data = get_google_sheets_data(SPREADSHEET_ID_LID_ID, range_name)
#     return data
#
#
# # Получаем список листов (названия ЖК) из таблицы шахматки.
# @cache(expire=600, namespace="shaxmatka_names")
# def get_shaxmatka_sheet_names():
#     return get_all_sheet_names(SPREADSHEET_ID_SHAXMATKA_ID)

#
# def read_from_google_sheet(spreadsheet_id, range_name):
#     try:
#         # Загружаем учетные данные
#         credentials = Credentials.from_service_account_file(
#             GOOGLE_CREDENTIALS_PATH,
#             scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
#         )
#         service = build('sheets', 'v4', credentials=credentials)
#
#         # Выполняем запрос данных
#         sheet = service.spreadsheets()
#         result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
#
#         # Извлекаем данные из ответа
#         values = result.get('values', [])
#         return values
#     except Exception as e:
#         print(f"Ошибка при чтении из Google Sheets: {e}")
#         return None
#
#
# def append_to_google_sheet(spreadsheet_id, range_name, values):
#     try:
#         service = get_google_sheets_service()  # Твоя функция для получения Google Sheets API сервиса
#         body = {
#             'values': values
#         }
#         result = service.spreadsheets().values().append(
#             spreadsheetId=spreadsheet_id,
#             range=range_name,
#             valueInputOption="USER_ENTERED",
#             insertDataOption="INSERT_ROWS",
#             body=body
#         ).execute()
#         return result
#     except Exception as e:
#         return {"error": str(e)}
#
#
# def get_all_sheet_names(spreadsheet_id):
#     try:
#         print("=== Получение названий листов ===")
#         credentials = Credentials.from_service_account_file(
#             GOOGLE_CREDENTIALS_PATH,
#             scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
#         )
#         service = build('sheets', 'v4', credentials=credentials)
#         sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
#
#         # Выводим метаданные таблицы
#         print(f"Метаданные таблицы: {sheet_metadata}")
#
#         sheets = sheet_metadata.get('sheets', [])
#         sheet_names = [sheet['properties']['title'] for sheet in sheets]
#         print(f"Названия листов: {sheet_names}")
#         return sheet_names
#     except Exception as e:
#         print(f"Ошибка при получении листов: {e}")
#         return []
#
#
# # Получаем данные из таблиц
# def get_google_sheets_data(spreadsheet_id, range_name):
#     try:
#         # Загружаем учетные данные
#         credentials = Credentials.from_service_account_file(
#             GOOGLE_CREDENTIALS_PATH,
#             scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
#         )
#         print("Учетные данные успешно загружены.")
#
#         # Подключаемся к Google Sheets API
#         service = build('sheets', 'v4', credentials=credentials, )
#         print("Сервис Google Sheets API успешно инициализирован.")
#
#         # Выполняем запрос данных
#         sheet = service.spreadsheets()
#         print(f"Отправляем запрос на диапазон {range_name} в таблице {spreadsheet_id}...")
#         result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
#
#         # Извлекаем данные из ответа
#         values = result.get('values', [])
#         print(f"Извлеченные данные: {values}")
#         return values
#     except Exception as e:
#         print(f"Ошибка при запросе данных: {e}")
#         return {"error": str(e)}
#
#
# def get_google_sheets_service():
#     try:
#         credentials = Credentials.from_service_account_file(
#             GOOGLE_CREDENTIALS_PATH,
#             scopes=["https://www.googleapis.com/auth/spreadsheets"]
#         )
#         service = build('sheets', 'v4', credentials=credentials)
#         return service
#     except Exception as e:
#         print(f"Ошибка при создании Google Sheets сервиса: {e}")
#         raise
#
#
# def update_shaxmatka_status(jk_name: str, block: str, apartment_number: str, status: str):
#     """
#     Обновляет статус квартиры в Google Sheets и очищает кэш для данного ЖК.
#     """
#     try:
#         sheet_name = jk_name
#         range_name = f"{sheet_name}!A2:G"
#         # Получаем данные через кэшированную функцию
#         shaxmatka_data = get_shaxmatka_data(jk_name)
#         if not shaxmatka_data:
#             return {"error": "Данные шахматки не найдены"}
#         for i, row in enumerate(shaxmatka_data):
#             if len(row) > 4 and row[0] == block and row[4] == apartment_number:
#                 row_index = i + 2  # Сдвиг на строки заголовка
#                 range_to_update = f"{sheet_name}!C{row_index}"  # Колонка C для статуса
#                 service = get_google_sheets_service()
#                 body = {"values": [[status]]}
#                 service.spreadsheets().values().update(
#                     spreadsheetId=SPREADSHEET_ID_SHAXMATKA_ID,
#                     range=range_to_update,
#                     valueInputOption="USER_ENTERED",
#                     body=body
#                 ).execute()
#                 # После обновления очищаем кэш для данного ЖК,
#                 # чтобы при следующем вызове get_shaxmatka_data() вернуть актуальные данные.
#                 FastAPICache.clear(namespace="shaxmatka")
#                 return {"status": "success", "message": f"Статус обновлен на '{status}'"}
#         return {"error": "Квартира не найдена в шахматке"}
#     except Exception as e:
#         return {"error": str(e)}
#
#
# async def check_and_update_status_from_lid():
#     """
#     Сравнивает данные шахматки и таблицы Лид и обновляет статусы квартир:
#       - Если квартира присутствует в Лиде, меняем статус на "Бронь".
#       - Если квартиры нет в Лиде, а статус "Бронь" — меняем на "Свободна".
#     """
#     try:
#         jk_names = await get_shaxmatka_sheet_names()
#         for jk_name in jk_names:
#             print(f"Проверяем записи в таблице Лид для ЖК: {jk_name}")
#             shaxmatka_data = await get_shaxmatka_data(jk_name)
#             if not shaxmatka_data:
#                 print(f"Шахматка для ЖК {jk_name} пуста или недоступна.")
#                 continue
#             lid_data = await get_lid_data(jk_name)
#             # Предполагаем, что номер квартиры находится в колонке с индексом 3.
#             lid_apartments = set(row[3] for row in lid_data if len(row) > 3)
#             # Шаг 1: Если квартира присутствует в Лиде и статус не равен "Бронь" — обновляем статус.
#             for row in shaxmatka_data:
#                 try:
#                     block = row[0]
#                     current_status = row[2]
#                     apartment_number = row[4]
#                     if apartment_number in lid_apartments and current_status != "Бронь":
#                         print(f"Квартира {apartment_number} в блоке {block} будет забронирована.")
#                         await update_shaxmatka_status(jk_name, block, apartment_number, "Бронь")
#                 except IndexError as e:
#                     print(f"Ошибка обработки строки {row}: {e}")
#                     continue
#             # Шаг 2: Если квартира отсутствует в Лиде, а статус равен "Бронь" — обновляем статус на "Свободна".
#             for row in shaxmatka_data:
#                 try:
#                     block = row[0]
#                     current_status = row[2]
#                     apartment_number = row[4]
#                     if apartment_number not in lid_apartments and current_status == "Бронь":
#                         print(f"Квартира {apartment_number} в блоке {block} будет освобождена.")
#                         await update_shaxmatka_status(jk_name, block, apartment_number, "Свободна")
#                 except IndexError as e:
#                     print(f"Ошибка обработки строки {row}: {e}")
#                     continue
#     except Exception as e:
#         print(f"Ошибка при проверке таблицы Лид: {e}")

# async def schedule_lid_check(interval: int = 60, initial_delay: int = 60):
#     # Задержка перед первым выполнением проверки
#     await asyncio.sleep(initial_delay)
#     while True:
#         await asyncio.sleep(interval)
#         await check_and_update_status_from_lid()



