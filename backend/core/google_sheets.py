import asyncio
import threading
import time

from dotenv import load_dotenv
import os

from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

load_dotenv()

GOOGLE_SHEETS_API_KEY = os.getenv('GOOGLE_SHEETS_API_KEY')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
SPREADSHEET_ID_SHAXMATKA_ID = os.getenv('SPREADSHEET_ID_SHAXMATKA_ID')
SPREADSHEET_ID_LID_ID = os.getenv('SPREADSHEET_ID_LID_ID')
SPREADSHEET_ID_PRICE_ID = os.getenv('SPREADSHEET_ID_PRICE_ID')
SPREADSHEET_ID_REESTR_ID = os.getenv('SPREADSHEET_ID_REESTR_ID')
SECRET_KEY = os.getenv('SECRET_KEY')


@cache(expire=600, namespace="shaxmatka")
def get_shaxmatka_data(jk_name: str):
    range_name = f"{jk_name}!A2:G"
    data = get_google_sheets_data(SPREADSHEET_ID_SHAXMATKA_ID, range_name)
    return data


# Получаем данные таблицы Лид для конкретного ЖК. Кэшируем на 60 секунд.
@cache(expire=600, namespace="lid")
def get_lid_data(jk_name: str):
    range_name = f"{jk_name}!A2:E"
    data = get_google_sheets_data(SPREADSHEET_ID_LID_ID, range_name)
    return data


# Получаем список листов (названия ЖК) из таблицы шахматки.
@cache(expire=600, namespace="shaxmatka_names")
def get_shaxmatka_sheet_names():
    return get_all_sheet_names(SPREADSHEET_ID_SHAXMATKA_ID)


@cache(expire=600)  # Кэш истечёт через 600 секунд (10 минут)
def get_price_data_for_sheet(sheet_name: str):
    price_data = get_google_sheets_data(SPREADSHEET_ID_PRICE_ID, f"{sheet_name}!A2:E")
    return price_data


def read_from_google_sheet(spreadsheet_id, range_name):
    try:
        # Загружаем учетные данные
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build('sheets', 'v4', credentials=credentials)

        # Выполняем запрос данных
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

        # Извлекаем данные из ответа
        values = result.get('values', [])
        return values
    except Exception as e:
        print(f"Ошибка при чтении из Google Sheets: {e}")
        return None


def append_to_google_sheet(spreadsheet_id, range_name, values):
    try:
        service = get_google_sheets_service()  # Твоя функция для получения Google Sheets API сервиса
        body = {
            'values': values
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        return result
    except Exception as e:
        return {"error": str(e)}


def get_all_sheet_names(spreadsheet_id):
    try:
        print("=== Получение названий листов ===")
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build('sheets', 'v4', credentials=credentials)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

        # Выводим метаданные таблицы
        print(f"Метаданные таблицы: {sheet_metadata}")

        sheets = sheet_metadata.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        print(f"Названия листов: {sheet_names}")
        return sheet_names
    except Exception as e:
        print(f"Ошибка при получении листов: {e}")
        return []


# Получаем данные из таблиц
def get_google_sheets_data(spreadsheet_id, range_name):
    try:
        # Загружаем учетные данные
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        print("Учетные данные успешно загружены.")

        # Подключаемся к Google Sheets API
        service = build('sheets', 'v4', credentials=credentials, )
        print("Сервис Google Sheets API успешно инициализирован.")

        # Выполняем запрос данных
        sheet = service.spreadsheets()
        print(f"Отправляем запрос на диапазон {range_name} в таблице {spreadsheet_id}...")
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

        # Извлекаем данные из ответа
        values = result.get('values', [])
        print(f"Извлеченные данные: {values}")
        return values
    except Exception as e:
        print(f"Ошибка при запросе данных: {e}")
        return {"error": str(e)}


def get_google_sheets_service():
    try:
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        print(f"Ошибка при создании Google Sheets сервиса: {e}")
        raise


def update_shaxmatka_status(jk_name: str, block: str, apartment_number: str, status: str):
    """
    Обновляет статус квартиры в Google Sheets и очищает кэш для данного ЖК.
    """
    try:
        sheet_name = jk_name
        range_name = f"{sheet_name}!A2:G"
        # Получаем данные через кэшированную функцию
        shaxmatka_data = get_shaxmatka_data(jk_name)
        if not shaxmatka_data:
            return {"error": "Данные шахматки не найдены"}
        for i, row in enumerate(shaxmatka_data):
            if len(row) > 4 and row[0] == block and row[4] == apartment_number:
                row_index = i + 2  # Сдвиг на строки заголовка
                range_to_update = f"{sheet_name}!C{row_index}"  # Колонка C для статуса
                service = get_google_sheets_service()
                body = {"values": [[status]]}
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID_SHAXMATKA_ID,
                    range=range_to_update,
                    valueInputOption="USER_ENTERED",
                    body=body
                ).execute()
                # После обновления очищаем кэш для данного ЖК,
                # чтобы при следующем вызове get_shaxmatka_data() вернуть актуальные данные.
                FastAPICache.clear(namespace="shaxmatka")
                return {"status": "success", "message": f"Статус обновлен на '{status}'"}
        return {"error": "Квартира не найдена в шахматке"}
    except Exception as e:
        return {"error": str(e)}


async def check_and_update_status_from_lid():
    """
    Сравнивает данные шахматки и таблицы Лид и обновляет статусы квартир:
      - Если квартира присутствует в Лиде, меняем статус на "Бронь".
      - Если квартиры нет в Лиде, а статус "Бронь" — меняем на "Свободна".
    """
    try:
        jk_names = await get_shaxmatka_sheet_names()
        for jk_name in jk_names:
            print(f"Проверяем записи в таблице Лид для ЖК: {jk_name}")
            shaxmatka_data = await get_shaxmatka_data(jk_name)
            if not shaxmatka_data:
                print(f"Шахматка для ЖК {jk_name} пуста или недоступна.")
                continue
            lid_data = await get_lid_data(jk_name)
            # Предполагаем, что номер квартиры находится в колонке с индексом 3.
            lid_apartments = set(row[3] for row in lid_data if len(row) > 3)
            # Шаг 1: Если квартира присутствует в Лиде и статус не равен "Бронь" — обновляем статус.
            for row in shaxmatka_data:
                try:
                    block = row[0]
                    current_status = row[2]
                    apartment_number = row[4]
                    if apartment_number in lid_apartments and current_status != "Бронь":
                        print(f"Квартира {apartment_number} в блоке {block} будет забронирована.")
                        await update_shaxmatka_status(jk_name, block, apartment_number, "Бронь")
                except IndexError as e:
                    print(f"Ошибка обработки строки {row}: {e}")
                    continue
            # Шаг 2: Если квартира отсутствует в Лиде, а статус равен "Бронь" — обновляем статус на "Свободна".
            for row in shaxmatka_data:
                try:
                    block = row[0]
                    current_status = row[2]
                    apartment_number = row[4]
                    if apartment_number not in lid_apartments and current_status == "Бронь":
                        print(f"Квартира {apartment_number} в блоке {block} будет освобождена.")
                        await update_shaxmatka_status(jk_name, block, apartment_number, "Свободна")
                except IndexError as e:
                    print(f"Ошибка обработки строки {row}: {e}")
                    continue
    except Exception as e:
        print(f"Ошибка при проверке таблицы Лид: {e}")


async def schedule_lid_check(interval: int = 60, initial_delay: int = 60):
    # Задержка перед первым выполнением проверки
    await asyncio.sleep(initial_delay)
    while True:
        await asyncio.sleep(interval)
        await check_and_update_status_from_lid()


async def load_data_to_cache():
    try:
        # Здесь можно вызвать функции, помеченные декоратором @cache, чтобы заполнить кэш
        # Например, принудительно загрузить данные шахматки
        _ = await get_shaxmatka_data()
        _ = await get_lid_data()
        _ = await get_shaxmatka_sheet_names()
        _ = await get_price_data_for_sheet()
        # Если есть другие функции для загрузки данных, их можно вызвать аналогично
        print("Первоначальная загрузка данных в кэш выполнена.")
    except Exception as e:
        print(f"Ошибка при первоначальной загрузке данных в кэш: {e}")
