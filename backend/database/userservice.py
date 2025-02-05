from sqlalchemy.exc import IntegrityError

from backend.api.users.schemas import UserCreate
from backend.database import get_db
from backend.database.models import User
from config import logger


# Функция для добавления нового пользователя
def add_user(user_data: UserCreate) -> User:
    with next(get_db()) as db:
        try:
            """Создаёт нового пользователя в базе данных."""
            new_user = User(
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                birth_date=user_data.birth_date,
                login=user_data.login,
                phone=user_data.phone,
                email=user_data.email,
                company=user_data.company,
                work_start_time=user_data.work_start_time,
                work_end_time=user_data.work_end_time,
                work_days=user_data.work_days,
                # Используем уже вычисленный захешированный пароль
                hashed_password=user_data.hashed_password,
                role_id=1
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        except IntegrityError as e:
            logger.error(f"Ошибка целостности данных при добавлении пользователя: {str(e)}")
            db.rollback()

        except Exception as e:
            logger.error(f"Произошла ошибка при добавлении пользователя: {str(e)}")
            db.rollback()


def get_user_by_login(login: str) -> User:
    with next(get_db()) as db:
        """Получает пользователя по логину."""
        return db.query(User).filter(User.login == login).first()
