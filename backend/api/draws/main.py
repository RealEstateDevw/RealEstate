import io
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from backend import get_db
from backend.database.marketing.crud import DrawUserCRUD

router = APIRouter(
    prefix="/draw-users",
    tags=["draw-users"],
)


@router.get(
    "/export",
    summary="Экспорт пользователей в Excel",
    response_description="Файл .xlsx с данными зарегистрированных пользователей",
)
async def export_draw_users_excel(
        skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
        limit: int = Query(200, ge=1, le=1000, description="Максимум записей за запрос"),
        db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Генерирует Excel-файл со списком пользователей, зарегистрированных в розыгрыше.
    """
    # 1. Получаем данные из БД
    users = DrawUserCRUD().list_draw_users(db=db, skip=skip, limit=limit)  # List[DrawUser]

    # 2. Подготавливаем DataFrame
    df = pd.DataFrame([
        {
            "ID": u.id,
            "Telegram ID": u.telegram_id,
            "Имя": u.first_name,
            "Фамилия": u.last_name,
            "Телефон": u.phone,
            "Дата регистрации": u.created_at
        }
        for u in users
    ])

    # 3. Записываем в Excel в память
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="DrawUsers")
    output.seek(0)

    # 4. Возвращаем файл пользователю
    headers = {
        "Content-Disposition": "attachment; filename=draw_users.xlsx"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
