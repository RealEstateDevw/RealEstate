"""CRUD-слой для маркетинговых сущностей (розыгрыши и кампании).

Содержит две группы операций:
1) DrawUserCRUD — управление участниками розыгрышей (бот в Telegram);
2) CampaignCRUD — управление маркетинговыми кампаниями в CRM.

Все функции работают с синхронной сессией SQLAlchemy и выполняют
commit/rollback внутри себя. Если нужно объединить несколько операций
в одну транзакцию — расширяйте CRUD или следите, чтобы commit не
выполнялся промежуточно.
"""

import secrets
import string
from datetime import date
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy import or_

from backend.api.marketing.schemas import CampaignCreate, CampaignUpdate
from backend.database.models import DrawUser, UserLang, Campaign, Lead, CampaignStatus
from backend.api.leads.schemas import LeadState


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

    # =========================================================================
    # НОВЫЕ МЕТОДЫ ДЛЯ UTM И МЕТРИК
    # =========================================================================

    @staticmethod
    def _generate_utm_code(length: int = 8) -> str:
        """Генерирует уникальный UTM-код."""
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def generate_utm_link(
            self,
            db: Session,
            campaign_id: int,
            base_url: Optional[str] = None
    ) -> Optional[Campaign]:
        """
        Генерирует уникальную UTM-ссылку для кампании.

        Args:
            db: Сессия БД
            campaign_id: ID кампании
            base_url: Базовый URL (если не указан, используется target_url кампании)

        Returns:
            Обновлённая кампания или None если не найдена
        """
        campaign = self.get_campaign(db, campaign_id)
        if not campaign:
            return None

        # Генерируем уникальный utm_source если его нет
        if not campaign.utm_source:
            while True:
                utm_code = self._generate_utm_code()
                # Проверяем уникальность
                existing = db.query(Campaign).filter(Campaign.utm_source == utm_code).first()
                if not existing:
                    campaign.utm_source = utm_code
                    break

        # Определяем базовый URL
        target = base_url or campaign.target_url or "https://t.me/bahor_lc_bot/app"

        # Формируем UTM-параметры
        utm_params = {
            "utm_source": campaign.utm_source,
            "utm_medium": campaign.utm_medium or campaign.platform.value,
            "utm_campaign": campaign.utm_campaign or campaign.name.lower().replace(" ", "_"),
        }

        # Собираем полную ссылку
        parsed = urlparse(target)
        # Для Telegram mini app добавляем параметры через startapp
        if "t.me" in parsed.netloc:
            # Telegram формат: https://t.me/bot_name/app?startapp=utm_source
            campaign.utm_link = f"{target}?startapp={campaign.utm_source}"
        else:
            # Стандартный формат с UTM-параметрами
            query_string = urlencode(utm_params)
            campaign.utm_link = f"{target}?{query_string}"

        campaign.target_url = target

        try:
            db.commit()
            db.refresh(campaign)
            return campaign
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Ошибка при генерации ссылки: {e}") from e

    def get_campaign_by_utm(self, db: Session, utm_source: str) -> Optional[Campaign]:
        """Получить кампанию по UTM-коду."""
        return db.query(Campaign).filter(Campaign.utm_source == utm_source).first()

    def increment_clicks(self, db: Session, campaign_id: int, count: int = 1) -> Optional[Campaign]:
        """Увеличить счётчик кликов кампании."""
        campaign = self.get_campaign(db, campaign_id)
        if not campaign:
            return None

        campaign.clicks = (campaign.clicks or 0) + count
        db.commit()
        db.refresh(campaign)
        return campaign

    def track_click_by_utm(self, db: Session, utm_source: str) -> Optional[Campaign]:
        """Трекинг клика по UTM-коду."""
        campaign = self.get_campaign_by_utm(db, utm_source)
        if campaign:
            campaign.clicks = (campaign.clicks or 0) + 1
            db.commit()
            db.refresh(campaign)
        return campaign

    def get_campaign_metrics(self, db: Session, campaign_id: int) -> Dict[str, Any]:
        """
        Получить полные метрики кампании.

        Returns:
            Dict с метриками:
            - leads_count: количество лидов
            - deals_count: количество сделок
            - cr_lead: конверсия в лиды
            - cr_sale: конверсия в сделки
            - cr_total: общая конверсия
            - cpa: стоимость лида
            - cps: стоимость сделки
            - cost_per_click: стоимость клика
            - health_status: статус здоровья кампании
        """
        campaign = self.get_campaign(db, campaign_id)
        if not campaign:
            raise NoResultFound(f"Кампания ID={campaign_id} не найдена")

        # Считаем лидов и сделки из связанной таблицы
        leads_count = db.query(func.count(Lead.id)).filter(Lead.campaign_id == campaign_id).scalar() or 0
        deals_count = db.query(func.count(Lead.id)).filter(
            Lead.campaign_id == campaign_id,
            Lead.state == LeadState.CLOSED
        ).scalar() or 0

        clicks = campaign.clicks or 0
        spent = campaign.spent_budget or 0

        # Расчёт метрик
        cr_lead = round((leads_count / clicks) * 100, 2) if clicks > 0 else 0
        cr_sale = round((deals_count / leads_count) * 100, 2) if leads_count > 0 else 0
        cr_total = round((deals_count / clicks) * 100, 2) if clicks > 0 else 0
        cpa = round(spent / leads_count, 2) if leads_count > 0 else 0
        cps = round(spent / deals_count, 2) if deals_count > 0 else 0
        cost_per_click = round(spent / clicks, 2) if clicks > 0 else 0

        # Определяем health_status
        health_status = self._calculate_health_status(cr_total, cps, cr_lead, cr_sale, clicks)

        return {
            "campaign_id": campaign_id,
            "name": campaign.name,
            "platform": campaign.platform.value,
            "status": campaign.status.value,
            "clicks": clicks,
            "leads_count": leads_count,
            "deals_count": deals_count,
            "spent_budget": spent,
            "planned_budget": campaign.planned_budget or 0,
            "cr_lead": cr_lead,
            "cr_sale": cr_sale,
            "cr_total": cr_total,
            "cpa": cpa,
            "cps": cps,
            "cost_per_click": cost_per_click,
            "health_status": health_status,
            "utm_source": campaign.utm_source,
            "utm_link": campaign.utm_link,
        }

    @staticmethod
    def _calculate_health_status(
            cr_total: float,
            cps: float,
            cr_lead: float,
            cr_sale: float,
            clicks: int
    ) -> str:
        """Вычислить статус здоровья кампании."""
        # Пороговые значения
        CR_TOTAL_LOW = 1.0
        CR_TOTAL_HIGH = 5.0
        CPS_HIGH = 100.0
        CR_LEAD_LOW = 5.0
        CR_LEAD_HIGH = 15.0
        CR_SALE_LOW = 10.0
        CR_SALE_HIGH = 30.0

        if clicks < 100:
            return "neutral"

        if cr_total < CR_TOTAL_LOW and cps > CPS_HIGH:
            return "danger"

        if cr_total > CR_TOTAL_HIGH and (cps < CPS_HIGH or cps == 0):
            return "success"

        if cr_lead > CR_LEAD_HIGH and cr_sale < CR_SALE_LOW:
            return "warning_sales"

        if cr_lead < CR_LEAD_LOW and cr_sale > CR_SALE_HIGH:
            return "warning_creative"

        return "neutral"

    def get_dashboard_stats(self, db: Session) -> Dict[str, Any]:
        """
        Получить общую статистику для дашборда маркетинга.

        Returns:
            Dict:
            - total_clicks: общее число переходов
            - total_leads: общее число лидов
            - total_deals: общее число сделок
            - total_spent: общий расход
            - active_campaigns: количество активных кампаний
            - campaigns: список кампаний с метриками
        """
        # Агрегированные метрики
        total_clicks = db.query(func.sum(Campaign.clicks)).scalar() or 0
        total_spent = db.query(func.sum(Campaign.spent_budget)).scalar() or 0

        # Лиды и сделки с привязкой к кампаниям
        total_leads = db.query(func.count(Lead.id)).filter(Lead.campaign_id.isnot(None)).scalar() or 0
        total_deals = db.query(func.count(Lead.id)).filter(
            Lead.campaign_id.isnot(None),
            Lead.state == LeadState.CLOSED
        ).scalar() or 0

        # Активные кампании
        active_campaigns = db.query(func.count(Campaign.id)).filter(
            Campaign.status == CampaignStatus.ACTIVE
        ).scalar() or 0

        # Список кампаний с метриками
        campaigns = self.get_campaigns(db, limit=50)
        campaigns_with_metrics = []

        for campaign in campaigns:
            try:
                metrics = self.get_campaign_metrics(db, campaign.id)
                campaigns_with_metrics.append(metrics)
            except Exception:
                # Если метрики не удалось получить, добавляем базовую информацию
                campaigns_with_metrics.append({
                    "campaign_id": campaign.id,
                    "name": campaign.name,
                    "platform": campaign.platform.value,
                    "status": campaign.status.value,
                    "clicks": campaign.clicks or 0,
                    "health_status": "neutral"
                })

        return {
            "total_clicks": total_clicks,
            "total_leads": total_leads,
            "total_deals": total_deals,
            "total_spent": total_spent,
            "active_campaigns": active_campaigns,
            "campaigns": campaigns_with_metrics,
        }
