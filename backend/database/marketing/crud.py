"""CRUD-слой для маркетинговых сущностей (розыгрыши и кампании).

Содержит две группы операций:
1) DrawUserCRUD — управление участниками розыгрышей (бот в Telegram);
2) CampaignCRUD — управление маркетинговыми кампаниями в CRM.

Все функции работают с синхронной сессией SQLAlchemy и выполняют
commit/rollback внутри себя. Если нужно объединить несколько операций
в одну транзакцию — расширяйте CRUD или следите, чтобы commit не
выполнялся промежуточно.
"""

from datetime import date
from typing import Optional, List, Dict, Any

from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy import or_

from backend.api.marketing.schemas import CampaignCreate, CampaignUpdate
from backend.database.models import DrawUser, UserLang, Campaign


class DrawUserCRUD:
    """Операции с участниками розыгрышей (DrawUser)."""

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


class CampaignCRUD:
    """CRUD-операции для маркетинговых кампаний."""

    def get_campaign(self, db: Session, campaign_id: int) -> Optional[Campaign]:
        """Получить кампанию по ID или вернуть None, если не найдена."""
        return db.query(Campaign).filter(Campaign.id == campaign_id).first()

    def search_campaigns(
            self,
            db: Session,
            query: str,
            skip: int = 0,
            limit: int = 10
    ) -> List[Campaign]:
        """
        Ищет кампании по частичному совпадению в name или account (case-insensitive).
        """
        pattern = f"%{query}%"
        return (
            db.query(Campaign)
            .filter(
                or_(
                    Campaign.name.ilike(pattern),
                    Campaign.account.ilike(pattern)
                )
            )
            .order_by(desc(Campaign.launch_date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_campaigns(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            platform: Optional[str] = None,
            status: Optional[str] = None
    ) -> List[Campaign]:
        """
        Возвращает список кампаний с необязательной фильтрацией
        по платформе и статусу, отсортированный по дате запуска.
        """
        query = db.query(Campaign)
        if platform:
            query = query.filter(Campaign.platform == platform)
        if status:
            query = query.filter(Campaign.status == status)
        return query.order_by(desc(Campaign.launch_date)).offset(skip).limit(limit).all()

    def create_campaign(self, db: Session, campaign_in: CampaignCreate) -> Campaign:
        """Создать кампанию из схемы CampaignCreate и вернуть сохранённый объект."""
        db_obj = Campaign(**campaign_in.dict())
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Не удалось создать кампанию: {e}") from e

    def update_campaign(
            self,
            db: Session,
            campaign_id: int,
            campaign_in: CampaignUpdate
    ) -> Optional[Campaign]:
        """
        Частично обновить кампанию.
        Возвращает обновлённый объект или None, если не найдена.
        """
        db_obj = self.get_campaign(db, campaign_id)
        if not db_obj:
            return None

        update_data = campaign_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Ошибка при обновлении кампании: {e}") from e

    def delete_campaign(self, db: Session, campaign_id: int) -> bool:
        db_obj = self.get_campaign(db, campaign_id)
        if not db_obj:
            return False
        db.delete(db_obj)
        db.commit()
        return True

    def get_statistics(self, db: Session, campaign_id: int) -> Dict[str, Any]:
        """
        Считает:
        - budget_spent: сколько уже потрачено
        - cost_per_deal: во сколько в среднем обошлась 1 успешная сделка
        - success_rate: процент лидов, которые стали активными
        - date: текущее число
        """
        campaign = self.get_campaign(db, campaign_id)
        if not campaign:
            raise NoResultFound(f"Кампания ID={campaign_id} не найдена")

        spent = campaign.spent_budget
        leads_total = campaign.leads_total or 0
        leads_active = campaign.leads_active or 0

        cost_per_deal = None
        if leads_active > 0:
            cost_per_deal = spent / leads_active

        success_rate = None
        if leads_total > 0:
            success_rate = round((leads_active / leads_total) * 100, 2)

        return {
            "budget_spent": spent,
            "cost_per_deal": cost_per_deal,
            "success_rate": success_rate,
            "date": date.today().isoformat()
        }
