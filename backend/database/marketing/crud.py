from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, IntegrityError

from backend.database.models import DrawUser, UserLang


class DrawUserCRUD:
    def get_exact_draw_user(self, db: Session, telegram_id: int) -> DrawUser:
        """
        Возвращает одного пользователя DrawUser по telegram_id.
        Бросает NoResultFound, если не найден.
        """
        try:
            user = db.query(DrawUser) \
                     .filter(DrawUser.telegram_id == telegram_id) \
                     .one()
            print(f"Найден DrawUser: id={user.id}, telegram_id={telegram_id}")
            return user
        except NoResultFound:
            msg = f"DrawUser с telegram_id={telegram_id} не найден."
            print(msg)
            raise NoResultFound(msg)
        except Exception as e:
            print(f"Ошибка при get_exact_draw_user: {e}")
            raise Exception("Ошибка базы данных при получении пользователя.") from e

    def add_draw_user(
        self,
        db: Session,
        telegram_id: int,
        first_name: str,
        last_name: str,
        phone: str,
        lang: UserLang = UserLang.ru
    ) -> DrawUser:
        """
        Создаёт нового участника DrawUser.
        Бросает ValueError, если telegram_id или phone уже заняты.
        """
        try:
            new_user = DrawUser(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                lang=lang
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"Создан новый DrawUser: id={new_user.id}, telegram_id={telegram_id}")
            return new_user
        except IntegrityError as ie:
            db.rollback()
            print(f"IntegrityError при add_draw_user: {ie}")
            raise ValueError("Пользователь с таким telegram_id или телефоном уже существует.") from ie
        except Exception as e:
            db.rollback()
            print(f"Ошибка при add_draw_user: {e}")
            raise Exception("Ошибка базы данных при создании пользователя.") from e

    def list_draw_users(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> list[DrawUser]:
        """
        Возвращает список зарегистрированных пользователей,
        с поддержкой пагинации через skip/limit.
        """
        try:
            users = (
                db.query(DrawUser)
                  .order_by(DrawUser.created_at.desc())
                  .offset(skip)
                  .limit(limit)
                  .all()
            )
            print(f"Получено {len(users)} DrawUser (skip={skip}, limit={limit})")
            return users
        except Exception as e:
            print(f"Ошибка при list_draw_users: {e}")
            raise Exception("Ошибка базы данных при получении списка пользователей.") from e