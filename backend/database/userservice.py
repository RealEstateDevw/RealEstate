"""Сервисные функции для работы с пользователями и ролями.

Содержит операции создания/обновления/удаления пользователей, проверки
рабочего дня и статуса посещаемости. Все функции открывают сессию через
`get_db()` и сами выполняют commit/rollback.
"""

from datetime import date, datetime, time
from typing import List

from sqlalchemy.exc import IntegrityError

from backend.api.users.schemas import UserCreate, UserUpdate
from backend.database import get_db
from backend.database.models import User, Role, Attendance
from config import logger
from fastapi.encoders import jsonable_encoder


def parse_time(time_str: str) -> time:
    """Преобразует строку 'HH:MM:SS' в объект time."""
    return datetime.strptime(time_str, "%H:%M:%S").time()


# Пример использования

# Функция для добавления нового пользователя
def add_user(user_data: UserCreate) -> User:
    """Создаёт нового пользователя с дефолтными рабочими параметрами."""
    with next(get_db()) as db:
        try:
            work_days_list = [
                {"name": "ПН", "active": False},
                {"name": "ВТ", "active": False},
                {"name": "СР", "active": False},
                {"name": "ЧТ", "active": False},
                {"name": "ПТ", "active": False},
                {"name": "СБ", "active": True},
                {"name": "ВС", "active": True}
            ]
            work_start_time = parse_time("00:00:00")
            work_end_time = parse_time("23:59:59")
            """Создаёт нового пользователя в базе данных."""
            new_user = User(
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                birth_date=user_data.birth_date,
                login=user_data.login,
                phone=user_data.phone,
                email=user_data.email,
                company="RealEstate",
                work_start_time=work_start_time,
                work_end_time=work_end_time,
                work_days=work_days_list,
                # Используем уже вычисленный захешированный пароль
                hashed_password=user_data.hashed_password,
                role_id=user_data.role_id
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        except IntegrityError as e:
            logger.error(f"Ошибка целостности данных при добавлении пользователя: {str(e)}")
            db.rollback()
            raise e

        except Exception as e:
            logger.error(f"Произошла ошибка при добавлении пользователя: {str(e)}")
            db.rollback()
            raise e


def get_user_by_id(user_id: int) -> User:
    """Получить пользователя по ID."""
    with next(get_db()) as db:
        return db.query(User).filter(User.id == user_id).first()


def is_work_day(user) -> bool:
    """
    Определяет, является ли сегодняшний день рабочим для данного сотрудника.
    Ожидается, что user.work_days — список словарей вида:
      [{"name": "ПН", "active": true}, {"name": "ВТ", "active": true}, ...]
    """
    # Привязка weekday() (0 — понедельник, 6 — воскресенье) к названиям дней
    weekday_mapping = {
        0: "ПН",
        1: "ВТ",
        2: "СР",
        3: "ЧТ",
        4: "ПТ",
        5: "СБ",
        6: "ВС"
    }
    today_weekday = datetime.today().weekday()  # число от 0 до 6
    today_name = weekday_mapping.get(today_weekday, None)

    if today_name is None:
        return False

    # Поиск текущего дня в расписании
    for day in user.work_days:
        if day.get("name") == today_name:

            return day.get("active", False)
    # Если расписание не содержит запись для текущего дня, можно считать его выходным
    return True


def is_user_at_work(user_id: int) -> bool:
    """
    Проверяет, находится ли пользователь на работе.

    Пользователь считается находящимся на работе,
    если за сегодня существует запись с заполненным check_in и отсутствующим check_out.

    :param user_id: идентификатор пользователя
    :return: True, если пользователь на работе, иначе False
    """
    with next(get_db()) as db:
        today = date.today()
        attendance = db.query(Attendance).filter(Attendance.user_id == user_id,
                                                 Attendance.date == today).first()
        if attendance and attendance.check_in:
            return True
        return False


def get_all_users() -> List[dict]:
    """Получить список всех активных пользователей (кроме роли 5) с рассчитанным статусом."""
    with next(get_db()) as db:
        users = db.query(User).filter(User.role_id != 5).all()
        users_data = []
        for user in users:
            is_user_at_w = is_user_at_work(user.id)
            user_dict = {"id": user.id,
                         "first_name": user.first_name,
                         "last_name": user.last_name,
                         "work_days": user.work_days,
                         "work_start_time": user.work_start_time.strftime("%H:%M"),
                         "work_end_time": user.work_end_time.strftime("%H:%M"),
                         "birth_date": user.birth_date,
                         "login": user.login,
                         "role": user.role,
                         "phone": user.phone,
                         "email": user.email,
                         "company": user.company,
                         "work_status": "Выходной" if is_work_day(user) else "Рабочий",
                         "checkin_time": is_user_at_w,
                         "registration_date": user.reg_date.strftime("%d.%m.%Y"),
                         "background_theme": user.background_theme,
                         "password": "qwerty123"  # Показываем дефолтный пароль для админки
                         }
            # Вычисляем статус
            users_data.append(user_dict)

        return jsonable_encoder(users_data)


def update_user(user_id: int, user_data: UserUpdate) -> bool:
    with next(get_db()) as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Получаем только те поля, которые были переданы в запросе
        update_data = user_data.dict(exclude_unset=True)

        # Если обновляется пароль, нужно использовать правильное поле
        if "password" in update_data and update_data["password"] is not None:
            update_data["hashed_password"] = update_data.pop("password")

        # # Если обновляется поле work_days и элементы – это объекты WorkDay, то преобразуем их в список словарей
        # if "work_days" in update_data and update_data["work_days"] is not None:
        #     update_data["work_days"] = [
        #         wd if isinstance(wd, dict) else wd.dict() for wd in update_data["work_days"]
        #     ]

        # Обновляем атрибуты объекта User
        for key, value in update_data.items():
            setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return True


def add_role(name: str) -> Role:
    with next(get_db()) as db:
        try:
            """Создаёт новую роль в базе данных."""
            new_role = Role(name=name)
            db.add(new_role)
            db.commit()
            db.refresh(new_role)
            return new_role
        except IntegrityError as e:
            logger.error(f"Ошибка целостности данных при добавлении роли: {str(e)}")
            db.rollback()

        except Exception as e:
            logger.error(f"Произошла ошибка при добавлении роли: {str(e)}")
            db.rollback()


def get_user_by_login(login: str) -> User:
    """Получить пользователя по логину (для аутентификации)."""
    with next(get_db()) as db:
        user = db.query(User).filter(User.login == login).first()
        return user


def register_attendance(user_id: int, action: str) -> 'Attendance':
    """
    Регистрирует посещаемость пользователя.

    :param user_id: идентификатор пользователя
    :param action: 'check_in' для входа, 'check_out' для выхода
    :return: объект Attendance, обновлённый после операции
    """
    with next(get_db()) as db:
        today = date.today()
        now_time = datetime.now().time()

        # Ищем запись за сегодня для данного пользователя
        attendance = db.query(Attendance).filter(Attendance.user_id == user_id,
                                                 Attendance.date == today).first()

        if action == "check_in":
            if not attendance:
                # Если записи нет, создаём её с временем входа и статусом "на работе"
                attendance = Attendance(user_id=user_id, date=today,
                                        check_in=now_time, status="на работе")
                db.add(attendance)
            else:
                # Если запись уже существует, но пользователь ещё не оформил выход,
                # можно обновить статус на "на работе" (если требуется)
                if attendance.check_out is None:
                    attendance.status = "на работе"
        elif action == "check_out":
            if attendance and attendance.check_out is None:
                # Если запись существует и выход ещё не зарегистрирован,
                # обновляем время выхода и статус
                attendance.check_out = now_time
                attendance.status = "отработал"
            else:
                # Если записи нет или уже зарегистрирован выход, можно вернуть ошибку или просто вернуть существующую запись
                raise ValueError("Невозможно зарегистрировать выход: либо пользователь не зашел, либо уже вышел.")
        else:
            raise ValueError("Неверное действие. Используйте 'check_in' или 'check_out'.")

        db.commit()
        db.refresh(attendance)
        return attendance


def get_by_role_employees(role_id: int) -> List[User]:
    with next(get_db()) as db:
        users = db.query(User).filter(User.role_id == role_id).all()
        users_data = []
        for user in users:
            print(user.role.name)
            is_user_at_w = is_user_at_work(user.id)
            user_dict = {"id": user.id,
                         "first_name": user.first_name,
                         "last_name": user.last_name,
                         "work_days": user.work_days,
                         "work_start_time": user.work_start_time.strftime("%H:%M"),
                         "work_end_time": user.work_end_time.strftime("%H:%M"),
                         "birth_date": user.birth_date,
                         "login": user.login,
                         "role": user.role,
                         "phone": user.phone,
                         "email": user.email,
                         "company": user.company,
                         "work_status": "Выходной" if is_work_day(user) else "Рабочий",
                         "checkin_time": is_user_at_w,
                         "registration_date": user.reg_date.strftime("%d.%m.%Y"),
                         }
            # Вычисляем статус
            users_data.append(user_dict)

        return jsonable_encoder(users_data)


def get_all_roles() -> List[Role]:
    with next(get_db()) as db:
        return db.query(Role).filter(Role.id != 5).all()


def delete_user(user_id: int) -> bool:
    with next(get_db()) as db:
        try:
            db.query(Attendance).filter(Attendance.user_id == user_id).delete()
            db.query(User).filter(User.id == user_id).delete()
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
