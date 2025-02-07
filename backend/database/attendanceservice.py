from datetime import date, datetime

from backend.database import get_db
from backend.database.models import Attendance


def has_user_checked_in(user_id: int) -> bool:
    """
    Проверяет, заходил ли пользователь за сегодняшний день.
    Возвращает True, если запись о входе (check_in) за сегодня найдена.
    """
    with next(get_db()) as db:
        today = date.today()
        attendance = db.query(Attendance).filter(
            Attendance.user_id == user_id,
            Attendance.date == today
        ).first()
        return bool(attendance and attendance.check_in)


def register_attendance(user_id: int, action: str) -> Attendance:
    """
    Регистрирует посещаемость пользователя.
    Если action равен "check_in", то создаётся запись с временем входа.
    Если action равен "check_out", то обновляется время выхода.
    """
    with next(get_db()) as db:
        today = date.today()
        now_time = datetime.now().time()
        attendance = db.query(Attendance).filter(
            Attendance.user_id == user_id,
            Attendance.date == today
        ).first()

        if action == "check_in":
            if not attendance:
                attendance = Attendance(user_id=user_id, date=today,
                                        check_in=now_time, status="на работе")
                db.add(attendance)
            else:
                # Если запись уже существует, можно оставить её без изменений или обновить статус
                if attendance.check_out is None:
                    attendance.status = "на работе"
        elif action == "check_out":
            if attendance and attendance.check_out is None:
                attendance.check_out = now_time
                attendance.status = "отработал"
            else:
                raise ValueError("Невозможно зарегистрировать выход: либо пользователь не зашел, либо уже вышел.")
        else:
            raise ValueError("Неверное действие. Используйте 'check_in' или 'check_out'.")

        db.commit()
        db.refresh(attendance)
        return attendance
