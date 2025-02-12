from backend.database import get_db
from backend.database.models import Role


def init_roles():
    """Добавляет роли в БД, если их ещё нет."""
    roles = ["Продажник", "МОП", "РОП", "Финансист", "Админ"]

    db = next(get_db())
    try:
        existing_roles = {role.name for role in db.query(Role).all()}
        new_roles = [Role(name=role) for role in roles if role not in existing_roles]

        if new_roles:
            db.add_all(new_roles)
            db.commit()
            print(f"Добавлены новые роли: {', '.join([r.name for r in new_roles])}")
        else:
            print("Все роли уже существуют.")

    except Exception as e:
        print(f"Ошибка при инициализации ролей: {e}")
    finally:
        db.close()

