from aiogram import types, F, Router
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from backend.bot.sup import TgFuncs
from backend.database import SessionLocal
from backend.database.models import TelegramAccount, TelegramRole, ClientRequest, ClientRequestStatus, SenderRole

crud = TgFuncs()

client_bot_router = Router()


@client_bot_router.message(Command("start"))
async def cmd_start_client(message: types.Message, state: FSMContext):
    """
    /start – первый запуск бота со стороны клиента.
    Регистрирует TelegramAccount, предлагает меню «Связаться с продажником».
    """
    db: Session = SessionLocal()
    try:
        tg_id = message.from_user.id
        existing = db.query(TelegramAccount).filter(
            TelegramAccount.telegram_id == tg_id
        ).first()

        if existing and existing.role == TelegramRole.client:
            await message.answer(
                "Вы уже зарегистрированы как клиент. Нажмите «Связаться с продажником», чтобы начать новый запрос.",
                reply_markup=crud.generate_client_menu(),
            )
            return

        # Регистрируем клиента
        crud.register_telegram_account(db, tg_id, role=TelegramRole.client)
        await message.answer(
            "Добро пожаловать! Чтобы связаться с нашими продажниками, нажмите кнопку ниже.",
            reply_markup=crud.generate_client_menu(),
        )
    finally:
        db.close()


@client_bot_router.message(F.text == "Связаться с продажником")
async def handle_client_menu(message: types.Message, state: FSMContext):
    """
    Обрабатываем нажатие «Связаться с продажником» (кнопка).
    Создаём ClientRequest и уведомляем продажников.
    """
    db: Session = SessionLocal()
    try:
        client_tg_id = message.from_user.id
        # Создаём новую запись ClientRequest (status='new')
        req = crud.create_client_request(db, client_tg_id)

        # Уведомляем всех продажников
        await crud.forward_to_sales(
            message.bot, client_tg_id, "Клиент хочет связаться с продажником"
        )

        # Сообщаем клиенту и убираем клавиатуру
        await message.answer(
            "Ваш запрос отправлен всем продажникам. Пожалуйста, подождите, пока кто-то вас возьмет.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        # Устанавливаем состояние ожидания (условно, можно не хранить, но оставим)
        await state.set_state("WAITING_SALES_ACCEPT")
    finally:
        db.close()


@client_bot_router.message()
async def client_sends_text_after_connected(message: types.Message, state: FSMContext):
    """
    Если клиент уже «взял» продажник (status = 'taken'),
    то пересылаем сообщение менеджеру, сохраняя в БД.
    """
    client_tg_id = message.from_user.id
    db: Session = SessionLocal()
    try:
        # 1) Находим активный запрос для этого клиента
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.client_tg_id == client_tg_id,
                ClientRequest.status == ClientRequestStatus.taken,
            )
            .order_by(ClientRequest.taken_at.desc())
            .first()
        )
        if not req:
            # Ещё не взят – ничего не делаем
            return

        sales_tg_id = req.sales_tg_id
        lead_id = req.lead_id if req.lead_id is not None else -1

        # 2) Сохраняем чат-сообщение в новую модель ChatMessage
        crud.save_chat_message(
            db=db,
            lead_id=lead_id,
            source="telegram",
            message_text=message.text or "[медиа]",
            sender_id=client_tg_id,
            sender_role=SenderRole.CLIENT,
        )

        # 3) Пересылаем (форвардим) сообщение менеджеру
        await message.forward(sales_tg_id)

    finally:
        db.close()
