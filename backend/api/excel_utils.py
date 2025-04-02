# from __future__ import annotations
#
# import zipfile
# from io import BytesIO
# from typing import Union
#
# from fastapi import APIRouter, HTTPException, Body
# from num2words import num2words
# from openpyxl.reader.excel import load_workbook
# from openpyxl.workbook import Workbook
# from pydantic import BaseModel, Field
# import openpyxl
# import os
# import traceback  # Для логирования ошибок
#
# from starlette.responses import StreamingResponse, FileResponse
#
#
# # --- Вспомогательные функции ---
# def col_letter_to_index(letter: str) -> int:
#     """
#     Преобразует буквенное обозначение столбца в индекс, используемый openpyxl (1-индексация).
#     Например: 'A' -> 1, 'G' -> 7.
#     """
#     letter = letter.upper()
#     index = 0
#     for char in letter:
#         index = index * 26 + (ord(char) - ord('A') + 1)
#     return index  # openpyxl использует 1-based index
#
#
# # --- Конфигурация ---
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#
# # Словарь путей к файлам Excel для каждого ЖК
# EXCEL_FILE_PATHS = {
#     # !!! ЗАМЕНИТЕ НА ВАШИ РЕАЛЬНЫЕ ИМЕНА ЖК И ПУТИ !!!
#     "ЖК_Бахор": os.path.join("static", "Жилые_Комплексы", "ЖК_Бахор", "jk_data.xlsx"),
#     "Другой ЖК": os.path.join(BASE_DIR, "data", "shahmatka_drugoy.xlsx"),
# }
#
# # === НОВАЯ КОНФИГУРАЦИЯ СТОЛБЦОВ ===
# COLUMN_MAPPING = {
#     "blockName": 'A',  # Столбец 'A' для Блока
#     "status": 'C',  # Столбец 'C' для Статуса (для обновления)
#     "apartmentNumber": 'E',  # Столбец 'E' для Номера квартиры
#     "floor": 'G'  # Столбец 'G' для Этажа
# }
# DATA_START_ROW = 2  # Строка, с которой начинаются данные (1-based)
#
#
# # === КОНЕЦ НОВОЙ КОНФИГУРАЦИИ ===
#
# # --- Модель запроса (остается без изменений) ---
# class ApartmentStatusUpdate(BaseModel):
#     jkName: str
#     blockName: str
#     floor: int
#     apartmentNumber: Union[int, str]  # Номер квартиры может быть числом в JSON
#     newStatus: str = Field(default="бронь")
#
#
# class ContractData(BaseModel):
#     jkName: str
#     contractNumber: Union[str, None] = None  # Сделаем опциональным для генерации
#     contractDate: str
#     fullName: str
#     passportSeries: str
#     issuedBy: str
#     registrationAddress: str
#     phone: str
#     pinfl: str
#     block: str
#     floor: int
#     apartmentNumber: int
#     rooms: int
#     size: float  # Используем float для удобства, или str если нужно точное строковое представление
#     totalPrice: str  # Оставляем строкой для форматирования и number_to_words
#     pricePerM2: str  # Оставляем строкой
#     paymentChoice: str
#     initialPayment: str  # Оставляем строкой
#     salesDepartment: Union[str, None] = None  # Добавим, так как есть в реестре
#
#
# # Функция преобразования числа в слова (на русском языке)
# def number_to_words(number: str) -> str:
#     # Убираем все нечисловые символы и преобразуем в int
#     clean_number = ''.join(filter(str.isdigit, number))
#     return num2words(int(clean_number), lang='ru') + " сум"
#
#
# # --- Роутер (остается без изменений) ---
# router = APIRouter(prefix="/excel", tags=["Excel Operations"])  # Пример префикса
#
#
# # --- Обновленная Логика обновления Excel ---
# def find_row_and_update_status(file_path: str, update_data: ApartmentStatusUpdate):
#     try:
#         workbook = openpyxl.load_workbook(file_path)
#         sheet = workbook.active
#
#         block_col_idx = col_letter_to_index(COLUMN_MAPPING["blockName"])
#         floor_col_idx = col_letter_to_index(COLUMN_MAPPING["floor"])
#         apt_num_col_idx = col_letter_to_index(COLUMN_MAPPING["apartmentNumber"])
#         status_col_idx = col_letter_to_index(COLUMN_MAPPING["status"])
#
#         print(f"Поиск в файле: {file_path}")
#         print(f"Критерии: Блок='{update_data.blockName}', Этаж={update_data.floor}, Кв={update_data.apartmentNumber}")
#         print(f"Колонки: Блок={block_col_idx}, Этаж={floor_col_idx}, Кв={apt_num_col_idx}, Статус={status_col_idx}")
#
#         target_row_idx = -1
#         for row_idx in range(DATA_START_ROW, sheet.max_row + 1):
#             cell_block = sheet.cell(row=row_idx, column=block_col_idx).value
#             cell_floor = sheet.cell(row=row_idx, column=floor_col_idx).value
#             cell_apt_num = sheet.cell(row=row_idx, column=apt_num_col_idx).value
#
#             print(f"Строка {row_idx}: Блок='{cell_block}', Этаж='{cell_floor}', Кв='{cell_apt_num}'")
#
#             try:
#                 current_block = str(cell_block).strip().lower() if cell_block else ""
#                 update_block = str(update_data.blockName).strip().lower()
#                 matches_block = current_block == update_block
#
#                 current_floor = int(cell_floor) if cell_floor is not None else None
#                 matches_floor = current_floor == update_data.floor
#
#                 current_apt_num = int(cell_apt_num) if cell_apt_num is not None else None
#                 matches_apt_num = current_apt_num == update_data.apartmentNumber
#
#                 if matches_block and matches_floor and matches_apt_num:
#                     target_row_idx = row_idx
#                     print(f"Найдена строка {row_idx}!")
#                     break
#
#             except (ValueError, TypeError) as e:
#                 print(f"Ошибка в строке {row_idx}: {e}")
#                 continue
#
#         print(f"Итоговый target_row_idx: {target_row_idx}")
#         if target_row_idx != -1:
#             status_cell = sheet.cell(row=target_row_idx, column=status_col_idx)
#             old_status = status_cell.value
#             status_cell.value = update_data.newStatus
#             workbook.save(file_path)
#             print(f"Статус обновлен: строка {target_row_idx}, '{old_status}' -> '{update_data.newStatus}'")
#             return True
#         else:
#             print(
#                 f"Квартира не найдена: Блок={update_data.blockName}, Этаж={update_data.floor}, Кв={update_data.apartmentNumber}")
#             return False
#
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail=f"Excel file not found: {file_path}")
#     except Exception as e:
#         print(f"Ошибка при обновлении Excel: {e}")
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Error processing Excel file: {e}")
#
#
# @router.post("/excel/update-status")
# async def update_excel_status_endpoint(update_data: ApartmentStatusUpdate = Body(...)):
#     print(f"Запрос: {update_data.dict()}")
#     file_path = EXCEL_FILE_PATHS.get(update_data.jkName)
#
#     if not file_path:
#         return {"status": "warning", "message": f"Excel file path config missing for '{update_data.jkName}'"}
#
#     if not os.path.exists(file_path):
#         return {"status": "warning", "message": f"Excel file not found for '{update_data.jkName}'"}
#
#     success = find_row_and_update_status(file_path, update_data)
#     if success:
#         return {"status": "success", "message": "Apartment status updated successfully"}
#     else:
#         return {"status": "warning", "message": f"Apartment not found in Excel for '{update_data.jkName}'"}
#
#
# BASE_STATIC_PATH = "static/Жилые_Комплексы"
#
#
# @router.get("/last-contract-number")
# async def get_last_contract_number(jkName: str):
#     jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
#     REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")
#
#     if not os.path.exists(REGISTRY_PATH):
#         return {"lastContractNumber": None}  # Файл реестра не существует
#
#     try:
#         wb_registry = load_workbook(REGISTRY_PATH)
#         ws_registry = wb_registry.active
#         last_row = ws_registry.max_row
#
#         if last_row <= 1:  # Только заголовок или пустой файл
#             return {"lastContractNumber": None}
#
#         last_contract_number = ws_registry[f"A{last_row}"].value  # Предполагается, что номер в колонке A
#         return {"lastContractNumber": int(last_contract_number) + 1}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка при чтении реестра: {str(e)}")
#
#
# import os
# from io import BytesIO
# from openpyxl import load_workbook, Workbook
# from fastapi import APIRouter, HTTPException, Body, Depends  # Добавлен Depends, если нужна авторизация/зависимости
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel  # Убедитесь, что модель ContractData определена
# import zipfile  # Больше не нужен для отправки, но может быть нужен для других целей
#
# # --- Предполагается, что эти переменные/функции определены где-то ---
# # from your_models import ContractData # Пример импорта модели Pydantic
# # from your_utils import number_to_words # Пример импорта хелпера
# # BASE_STATIC_PATH = "/path/to/your/static/files" # Определите базовый путь
#
# # --- Начало определения роутера и модели (пример) ---
# router = APIRouter(prefix="/excel", tags=["Excel Operations"])  # Пример префикса
#
#
# # Примерная модель Pydantic, адаптируйте под вашу структуру
#
#
# # Пример функции-хелпера
# # def number_to_words(num_str: str) -> str:
# #     # Замените на вашу реальную реализацию конвертации числа в текст
# #     num_str_clean = num_str.replace(" ", "").replace(",", ".")
# #     try:
# #         num = float(num_str_clean)
# #         return f"{num:.2f} (прописью)"  # Заглушка
# #     except ValueError:
# #         return "Некорректное число"
#
#
# # --- Конец определения роутера и модели ---
#
#
# @router.post("/generate-contract")
# async def generate_contract(data: ContractData):
#     # Динамические пути к файлам в зависимости от jkName
#     jk_dir = os.path.join(BASE_STATIC_PATH, data.jkName)
#     TEMPLATE_PATH = os.path.join(jk_dir, "contract_template.xlsx")
#     REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")
#
#     # Проверка существования директории, если нет — создаем
#     if not os.path.exists(jk_dir):
#         try:
#             os.makedirs(jk_dir)
#             print(f"Создана директория: {jk_dir}")
#         except OSError as e:
#             raise HTTPException(status_code=500, detail=f"Не удалось создать директорию: {jk_dir}. Ошибка: {e}")
#
#     # 1. Генерация номера договора, если не указан
#     if not data.contractNumber:
#         next_contract_number_int = 1  # Номер по умолчанию
#         if os.path.exists(REGISTRY_PATH):
#             try:
#                 wb_registry_check = load_workbook(REGISTRY_PATH)
#                 ws_registry_check = wb_registry_check.active
#                 last_row = ws_registry_check.max_row
#                 if last_row > 1:  # Проверяем, есть ли строки после заголовка
#                     last_contract_val = ws_registry_check[f"A{last_row}"].value
#                     # Пробуем извлечь номер, если формат совпадает
#                     if last_contract_val and isinstance(last_contract_val, str) and last_contract_val.startswith("Д-"):
#                         try:
#                             last_num_str = last_contract_val.split('-')[1]
#                             last_contract_number_int = int(last_num_str)
#                             next_contract_number_int = last_contract_number_int + 1
#                         except (ValueError, IndexError):
#                             print(
#                                 f"Предупреждение: Не удалось извлечь номер из '{last_contract_val}' в реестре. Используется следующий номер.")
#                             # Можно добавить логику поиска максимального номера во всей колонке A, если последняя строка повреждена
#                             next_contract_number_int = last_contract_number_int + 1  # Или использовать 1 как fallback?
#                     else:
#                         print(
#                             f"Предупреждение: Последнее значение '{last_contract_val}' в колонке A реестра не соответствует формату 'Д-xxxx'. Нумерация может быть некорректной.")
#                         # Здесь тоже можно добавить более сложную логику поиска последнего номера
#
#             except Exception as e:  # Обработка ошибок чтения реестра
#                 print(
#                     f"Предупреждение: Не удалось прочитать реестр {REGISTRY_PATH} для определения номера договора. Ошибка: {e}. Начинаем с 1.")
#                 next_contract_number_int = 1
#
#         next_contract_number_str = str(next_contract_number_int).zfill(4)
#         data.contractNumber = f"Д-{next_contract_number_str}"
#         print(f"Сгенерирован номер договора: {data.contractNumber}")
#
#     # 2. Заполнение шаблона договора
#     if not os.path.exists(TEMPLATE_PATH):
#         raise HTTPException(status_code=404, detail=f"Шаблон договора не найден: {TEMPLATE_PATH}")  # 404 более уместен
#
#     try:
#         wb_contract = load_workbook(TEMPLATE_PATH)
#         ws_contract = wb_contract.active
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка загрузки шаблона договора: {TEMPLATE_PATH}. {e}")
#
#     # Функция для безопасной конвертации в слова
#     def safe_number_to_words(value_str):
#         if not value_str: return "N/A"
#         try:
#             return number_to_words(value_str)
#         except Exception as e:
#             print(f"Ошибка конвертации '{value_str}' в слова: {e}")
#             return "Ошибка конвертации"  # Возвращаем плейсхолдер ошибки
#
#     # Замена placeholders (добавлены проверки на None и str для значений)
#     replacements = {
#         "{{Номер_Договора}}": str(data.contractNumber or "N/A"),
#         "{{Дата}}": str(data.contractDate or "N/A"),
#         "{{Ф_И_О}}": str(data.fullName or "N/A"),
#         "{{Серия_Паспорта}}": str(data.passportSeries or "N/A"),
#         "{{Кем_Выдан}}": str(data.issuedBy or "N/A"),
#         "{{Прописка}}": str(data.registrationAddress or "N/A"),
#         "{{Номер_Тел}}": str(data.phone or "N/A"),
#         "{{ПИНФЛ}}": str(data.pinfl or "N/A"),
#         "{{Блок}}": str(data.block or "N/A"),
#         "{{Этаж}}": str(data.floor if data.floor is not None else "N/A"),
#         "{{Номер_КВ}}": str(data.apartmentNumber if data.apartmentNumber is not None else "N/A"),
#         "{{Кол-во_Ком}}": str(data.rooms if data.rooms is not None else "N/A"),
#         "{{Квадратура_Квартиры}}": str(data.size if data.size is not None else "N/A"),
#         "{{Общ_Стоимость}}": data.totalPrice.replace(" ", "") if data.totalPrice else "N/A",
#         "{{Общ_Стоимость_Про}}": safe_number_to_words(data.totalPrice),
#         "{{Стоимость_1_м2}}": data.pricePerM2.replace(" ", "") if data.pricePerM2 else "N/A",
#         "{{Стоимость_1_м2_Про}}": safe_number_to_words(data.pricePerM2),
#         "{{Процент_1_Взноса}}": data.paymentChoice.replace("%", "") if data.paymentChoice else "N/A",
#         "{{Сумма_1_Взноса}}": data.initialPayment.replace(" ", "") if data.initialPayment else "N/A",
#         "{{Сумма_1_Взноса_Про}}": safe_number_to_words(data.initialPayment),
#     }
#
#     # Итерация по ячейкам для замены
#     for row in ws_contract.iter_rows():
#         for cell in row:
#             if cell.value and isinstance(cell.value, str):
#                 original_value = cell.value
#                 modified_value = original_value
#                 for placeholder, value in replacements.items():
#                     # Заменяем, только если плейсхолдер найден
#                     if placeholder in modified_value:
#                         modified_value = modified_value.replace(placeholder, value)
#                 # Обновляем значение ячейки, если оно изменилось
#                 if modified_value != original_value:
#                     cell.value = modified_value
#
#     # Сохранение заполненного договора ВО ВРЕМЕННЫЙ БУФЕР В ПАМЯТИ
#     contract_buffer = BytesIO()
#     try:
#         wb_contract.save(contract_buffer)
#         contract_buffer.seek(0)  # Перемещаем указатель в начало буфера для чтения
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка сохранения сгенерированного договора в память: {e}")
#
#     # --- Удаляем сохранение договора во временный файл ---
#     # contract_file = os.path.join(jk_dir, f"contract_{data.contractNumber}.xlsx")
#     # wb_contract.save(contract_file) # Больше не нужно сохранять на диск здесь
#
#     # 3. Обновление реестра договоров (сохраняется на сервере)
#     try:
#         if os.path.exists(REGISTRY_PATH):
#             wb_registry = load_workbook(REGISTRY_PATH)
#             ws_registry = wb_registry.active
#         else:
#             # Создаем новый реестр с заголовками
#             wb_registry = Workbook()
#             ws_registry = wb_registry.active
#             ws_registry.append([
#                 "№ Договора", "Дата Договора", "Блок", "Этаж", "№ КВ", "Кол-во ком",
#                 "Квадратура Квартиры", "Общ Стоимость Договора", "Стоимость 1 кв.м",
#                 "Процент 1 Взноса", "Сумма 1 Взноса", "Ф/И/О", "Серия Паспорта",
#                 "ПИНФЛ", "Кем выдан", "Адрес прописки", "Номер тел", "Отдел Продаж"
#             ])
#
#         # Добавляем данные нового договора (с обработкой None и форматированием)
#         ws_registry.append([
#             data.contractNumber,
#             data.contractDate,
#             data.block,
#             data.floor,
#             data.apartmentNumber,
#             data.rooms,
#             data.size,
#             data.totalPrice.replace(" ", "") if data.totalPrice else None,
#             data.pricePerM2.replace(" ", "") if data.pricePerM2 else None,
#             data.paymentChoice.replace("%", "") if data.paymentChoice else None,
#             data.initialPayment.replace(" ", "") if data.initialPayment else None,
#             data.fullName,
#             data.passportSeries,
#             data.pinfl,
#             data.issuedBy,
#             data.registrationAddress,
#             data.phone,
#             data.salesDepartment  # Убедитесь, что это поле есть в ContractData
#         ])
#
#         wb_registry.save(REGISTRY_PATH)  # Сохраняем обновленный реестр на диск сервера
#         print(f"Реестр договоров обновлен: {REGISTRY_PATH}")
#
#     except Exception as e:
#         # Критическая ошибка - договор сгенерирован, но реестр не обновлен!
#         # Стоит ли откатывать? Или просто сообщить об ошибке?
#         # Пока просто логируем и возвращаем ошибку, не отправляя договор.
#         print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось обновить реестр {REGISTRY_PATH}. Ошибка: {e}")
#         # Можно вернуть 500 или специфический код ошибки
#         raise HTTPException(status_code=500,
#                             detail=f"Договор был подготовлен, но НЕ удалось обновить файл реестра на сервере. Обратитесь к администратору. Ошибка: {e}")
#
#     # --- Удаляем создание ZIP-архива ---
#     # zip_buffer = BytesIO()
#     # with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#     #     # zip_file.write(contract_file, f"contract_{data.contractNumber}.xlsx") # Больше не пишем из файла
#     #     # Вместо этого можно было бы писать из буфера, но нам не нужен zip
#     #     zip_file.write(REGISTRY_PATH, "contract_registry.xlsx")
#     # zip_buffer.seek(0)
#
#     # --- Удаляем удаление временного файла договора ---
#     # os.remove(contract_file) # Файл больше не создается на диске для отправки
#
#     # 6. Отправка сгенерированного файла договора Excel клиенту
#     contract_filename = f"contract_{data.contractNumber}.xlsx"
#     print(f"Отправка файла: {contract_filename}")
#
#     return StreamingResponse(
#         contract_buffer,  # Отправляем буфер с договором
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # MIME-тип для .xlsx
#         headers={
#             # Важно использовать кавычки вокруг имени файла для совместимости
#             "Content-Disposition": f"attachment; filename=\"{contract_filename}\""
#         }
#     )
#
#
# @router.get("/download-contract-registry")
# async def download_contract_registry(jkName: str):
#     jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
#     REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")
#
#     if not os.path.exists(REGISTRY_PATH):
#         raise HTTPException(status_code=404, detail="Реестр договоров не найден")
#
#     return FileResponse(
#         REGISTRY_PATH,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         filename=f"contract_registry_{jkName}.xlsx"
#     )
#
#
# @router.get("/get-contract-registry")
# async def get_contract_registry(jkName: str):
#     jk_dir = os.path.join(BASE_STATIC_PATH, jkName)
#     REGISTRY_PATH = os.path.join(jk_dir, "contract_registry.xlsx")
#
#     if not os.path.exists(REGISTRY_PATH):
#         raise HTTPException(status_code=404, detail="Реестр договоров не найден")
#
#     try:
#         wb_registry = load_workbook(REGISTRY_PATH)
#         ws_registry = wb_registry.active
#         data = []
#
#         # Читаем заголовки из первой строки
#         headers = [cell.value for cell in ws_registry[1]]
#
#         # Читаем данные из остальных строк
#         for row in ws_registry.iter_rows(min_row=2, values_only=True):
#             row_data = dict(zip(headers, row))
#             data.append(row_data)
#
#         return {"registry": data}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка при чтении реестра: {str(e)}")
