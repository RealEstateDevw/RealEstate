from __future__ import annotations

from typing import Union

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
import openpyxl
import os
import traceback  # Для логирования ошибок


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
    "ЖК_Бахор": os.path.join(BASE_DIR, "data", "shahmatka_baxor.xlsx"),
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
    newStatus: str = Field(default="Бронь")


# --- Роутер (остается без изменений) ---
router = APIRouter(prefix="/api", tags=["Excel Operations"])  # Пример префикса


# --- Обновленная Логика обновления Excel ---
def find_row_and_update_status(file_path: str, update_data: ApartmentStatusUpdate):
    """
    Находит строку квартиры в Excel и обновляет ее статус.
    Возвращает True в случае успеха, False в случае неудачи (квартира не найдена).
    Вызывает исключения при ошибках файла или openpyxl.
    """
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active  # Предполагаем работу с активным листом

        # Получаем 1-based индексы столбцов из новой конфигурации
        try:
            block_col_idx = col_letter_to_index(COLUMN_MAPPING["blockName"])
            floor_col_idx = col_letter_to_index(COLUMN_MAPPING["floor"])
            apt_num_col_idx = col_letter_to_index(COLUMN_MAPPING["apartmentNumber"])
            status_col_idx = col_letter_to_index(COLUMN_MAPPING["status"])
        except ValueError as e:
            print(f"Критическая ошибка: Неверная буква столбца в COLUMN_MAPPING: {e}")
            raise ValueError(f"Неверная буква столбца в COLUMN_MAPPING: {e}") from e

        print(f"Поиск в файле: {file_path}")
        print(
            f"Критерии поиска: Блок='{update_data.blockName}', Этаж={update_data.floor}, № Квартиры='{update_data.apartmentNumber}'")
        print(
            f"Используемые колонки (1-based): Блок={block_col_idx}, Этаж={floor_col_idx}, № Кв.={apt_num_col_idx}, Статус={status_col_idx}")

        target_row_idx = -1
        # Итерация по строкам для поиска нужной квартиры
        for row_idx in range(DATA_START_ROW, sheet.max_row + 1):
            # Читаем значения ячеек
            cell_block = sheet.cell(row=row_idx, column=block_col_idx).value
            cell_floor = sheet.cell(row=row_idx, column=floor_col_idx).value
            cell_apt_num = sheet.cell(row=row_idx, column=apt_num_col_idx).value

            # Приведение типов и сравнение (с учетом None и разных типов)
            try:
                # 1. Сравниваем этаж как число
                current_floor = int(cell_floor) if cell_floor is not None else None
                matches_floor = (current_floor is not None and current_floor == update_data.floor)

                # 2. Сравниваем номер квартиры (безопаснее как строку, если могут быть не числа)
                # Но т.к. в Excel числа, попробуем как число сначала
                current_apt_num = int(cell_apt_num) if cell_apt_num is not None else None
                search_apt_num = int(update_data.apartmentNumber)  # JS присылает число
                matches_apt_num = (current_apt_num is not None and current_apt_num == search_apt_num)

                # 3. Сравниваем блок как строку (без учета регистра)
                current_block_str = str(cell_block).strip().lower() if cell_block is not None else ""
                update_block_str = str(update_data.blockName).strip().lower()
                matches_block = (current_block_str == update_block_str)

                # Если все совпало
                if matches_block and matches_floor and matches_apt_num:
                    target_row_idx = row_idx
                    print(f"Найдена строка {target_row_idx}!")
                    break  # Нашли нужную строку

            except (ValueError, TypeError) as e:
                # Ошибка приведения типа в строке Excel, пропускаем строку, но логируем
                # Это может случиться, если в ячейках этажа/номера не числа
                print(f"Предупреждение (Строка {row_idx}): Не удалось сравнить данные. Ошибка: {e}. "
                      f"Ячейки: Блок='{cell_block}', Этаж='{cell_floor}', Кв='{cell_apt_num}'. "
                      f"Ожидалось: Блок='{update_data.blockName}', Этаж={update_data.floor}, Кв={update_data.apartmentNumber}")
                continue

        if target_row_idx != -1:
            # Нашли строку, обновляем статус
            status_cell = sheet.cell(row=target_row_idx, column=status_col_idx)
            old_status = status_cell.value
            print(
                f"Обновление статуса в строке {target_row_idx}, колонке {status_col_idx}: '{old_status}' -> '{update_data.newStatus}'")
            status_cell.value = update_data.newStatus
            try:
                workbook.save(file_path)  # Сохраняем изменения в файл
                print(f"Файл {file_path} успешно сохранен.")
                return True  # Успех
            except Exception as save_error:
                print(
                    f"Критическая ошибка: Не удалось сохранить файл {file_path} после обновления. Ошибка: {save_error}")
                # Возможно, стоит попытаться откатить изменение status_cell.value = old_status перед пробросом ошибки
                raise save_error  # Пробрасываем ошибку сохранения

        else:
            # Квартира не найдена
            print(f"ОШИБКА ПОИСКА: Квартира НЕ НАЙДЕНА в файле {file_path} по заданным критериям.")
            return False  # Неудача (не найдено)

    except FileNotFoundError:
        print(f"Критическая ошибка: Excel файл не найден по пути: {file_path}")
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    except Exception as e:
        print(f"Критическая ошибка при работе с Excel файлом {file_path}: {e}")
        traceback.print_exc()  # Печатаем полный traceback для диагностики
        raise e  # Пробрасываем исключение дальше


# --- Эндпоинт (остается почти без изменений, только путь) ---
@router.post("/excel/update-status", summary="Обновить статус квартиры в Excel")
# Используем путь /api/excel/update-status, т.к. роутер имеет префикс /api
async def update_excel_status_endpoint(update_data: ApartmentStatusUpdate = Body(...)):
    """
    Эндпоинт для обновления статуса квартиры в соответствующем Excel файле ЖК.
    """
    print(f"Получен запрос на обновление статуса: {update_data.dict()}")
    file_path = EXCEL_FILE_PATHS.get(update_data.jkName)

    if not file_path:
        print(f"Предупреждение: Конфигурация пути к Excel для ЖК '{update_data.jkName}' не найдена.")
        return {"status": "warning",
                "message": f"Lead created, but Excel file path config missing for ЖК '{update_data.jkName}'."}

    if not os.path.exists(file_path):
        print(f"Ошибка: Excel файл не найден по сконфигурированному пути: {file_path}")
        return {"status": "warning",
                "message": f"Lead created, but Excel file not found at path for ЖК '{update_data.jkName}'."}

    try:
        # Вызываем обновленную функцию
        success = find_row_and_update_status(file_path, update_data)
        if success:
            return {"status": "success", "message": "Apartment status successfully updated in Excel."}
        else:
            # Квартира не найдена
            return {"status": "warning",
                    "message": f"Lead created, but apartment not found in Excel for ЖК '{update_data.jkName}'. Check search criteria and Excel data."}

    except FileNotFoundError:  # Эта ошибка маловероятна здесь из-за проверки os.path.exists
        return {"status": "warning",
                "message": f"Lead created, but Excel file disappeared for ЖК '{update_data.jkName}'."}
    except ValueError as ve:  # Ошибка конфигурации столбцов
        print(f"Ошибка конфигурации столбцов Excel: {ve}")
        # Это внутренняя ошибка сервера
        raise HTTPException(status_code=500, detail="Internal Server Error: Excel column configuration error.")
    except Exception as e:
        print(f"Непредвиденная ошибка при обновлении Excel для ЖК '{update_data.jkName}': {e}")
        # Это внутренняя ошибка сервера
        raise HTTPException(status_code=500,
                            detail=f"Internal Server Error: Unexpected error processing Excel file: {e}")
