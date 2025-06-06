from datetime import datetime
from typing import Optional

from aiogram import Bot, types
from sqlalchemy.orm import Session

from backend.database.models import TelegramRole, TelegramAccount, ClientRequest, ClientRequestStatus, ChatMessage, \
    SenderRole


class TgFuncs:
    def register_telegram_account(
            self,
            db: Session,
            tg_id: int,
            role: TelegramRole,
            crm_user_id: Optional[int] = None,
    ) -> TelegramAccount:
        """
        Регистрирует нового пользователя TelegramAccount (client или sales) или возвращает существующий.
        """
        existing = db.query(TelegramAccount).filter(
            TelegramAccount.telegram_id == tg_id
        ).first()
        if existing:
            return existing

        new_acc = TelegramAccount(
            telegram_id=tg_id, role=role, crm_user_id=crm_user_id
        )
        db.add(new_acc)
        db.commit()
        db.refresh(new_acc)
        return new_acc

    def create_client_request(self, db: Session, client_tg_id: int) -> ClientRequest:
        """
        Создаёт запись о запросе клиента (нажатие «Связаться с продажником»).
        """
        req = ClientRequest(client_tg_id=client_tg_id, status=ClientRequestStatus.new)
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    def take_client_request(
            self, db: Session, request_id: int, sales_tg_id: int
    ) -> ClientRequest:
        """
        Помечает запрос клиента как взятый (status → 'taken'), записывает Telegram ID продажника.
        """
        req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
        if not req:
            return None
        req.status = ClientRequestStatus.taken
        req.taken_at = datetime.utcnow()
        req.sales_tg_id = sales_tg_id
        db.commit()
        db.refresh(req)
        return req

    def close_client_request(self, db: Session, request: ClientRequest) -> ClientRequest:
        """
        Помечает запрос клиента как закрытый (status → 'closed').
        """
        request.status = ClientRequestStatus.closed
        request.closed_at = datetime.utcnow()
        db.commit()
        db.refresh(request)
        return request

    def save_chat_message(
            self,
            db: Session,
            lead_id: int,
            source: str,
            message_text: str,
            sender_id: int,
            sender_role: SenderRole,
    ) -> ChatMessage:
        """
        Сохраняет сообщение в таблицу ChatMessage (новая модель).
        - lead_id       : ID лида (если нет — можно передавать -1)
        - source        : 'telegram' (или другой источник)
        - message_text  : сам текст сообщения
        - sender_id     : Telegram ID пользователя, который отправил это сообщение
        - sender_role   : SenderRole.CLIENT или SenderRole.SALES
        """
        cm = ChatMessage(
            lead_id=lead_id if lead_id is not None else -1,
            source=source,
            text=message_text,
            sender_id=sender_id,
            sender_role=sender_role,
            is_from_sales=(sender_role == SenderRole.SALES),
            created_at=datetime.utcnow(),  # SQLAlchemy подставит сам, но явно не помешает
        )
        db.add(cm)
        db.commit()
        db.refresh(cm)
        return cm

    async def forward_to_sales(
            self, db: Session, bot: Bot, client_tg_id: int, text: str
    ) -> None:
        """
        Отправляет уведомление всем активным продажникам (role=TelegramRole.sales)
        о том, что появился новый клиент.
        """
        sales_list = (
            db.query(TelegramAccount)
            .filter(TelegramAccount.role == TelegramRole.sales)
            .all()
        )
        for sales_acc in sales_list:
            await bot.send_message(
                sales_acc.telegram_id,
                f"🔔 Новый клиент запросил связь:\n\n"
                f"— Client TG ID: {client_tg_id}\n"
                f"— Сообщение: {text}\n\n"
                f"Чтобы взять клиента, нажмите кнопку ниже.",
                reply_markup=self.generate_take_button_markup(client_tg_id),
            )

    def generate_take_button_markup(
            self, client_tg_id: int
    ) -> types.InlineKeyboardMarkup:
        """
        Создает Inline-клавиатуру с кнопкой «Взять клиента».
        callback_data будет вида \"take:<client_tg_id>\".
        """
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                text="🤝 Взять клиента", callback_data=f"take:{client_tg_id}"
            )
        )
        return kb

    def generate_client_menu(self) -> types.ReplyKeyboardMarkup:
        """
        Возвращает клавиатуру для клиента: одна кнопка «Связаться с продажником».
        """
        from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("Связаться с продажником"))
        return kb

    def generate_sales_menu(self) -> types.ReplyKeyboardMarkup:
        """
        Возвращает клавиатуру для продажника в режиме диалога:
        «Привязать к лиду», «Создать лид», «Завершить разговор».
        """
        from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(
            KeyboardButton("Привязать к лиду"),
            KeyboardButton("Создать лид"),
        )
        kb.add(KeyboardButton("Завершить разговор"))
        return kb
