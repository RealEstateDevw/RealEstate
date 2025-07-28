from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from backend.api.leads.schemas import LeadStatus, LeadState
from backend.bot.states import SalesStates
from backend.bot.sup import TgFuncs
from backend.database import SessionLocal
from backend.database.models import ClientRequest, TelegramRole, ClientRequestStatus, Lead, SenderRole, TelegramAccount, \
    User
from aiogram import types, F, Router

crud = TgFuncs()

sales_bot_router = Router()


class SalesDeepLinkFilter(Filter):
    async def __call__(self, message: types.Message, *, command: types.BotCommand) -> bool:
        args = command.args
        print("Deep link args:", args)
        return bool(args and args.startswith("sales_"))


@sales_bot_router.message(Command("start"), SalesDeepLinkFilter())
async def cmd_start_sales(message: types.Message, state: FSMContext):
    """
    /start sales_<user_id> – сначала проверяем наличие аргумента, потом регистрируем аккаунт продажника.
    """
    db: Session = SessionLocal()
    try:
        tg_id = message.from_user.id
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []

        if args:
            # Первый аргумент после /start - это наш параметр
            deep_link_param = args[0]
            # всё, что приходит после "/start "
            crm_id = None

            # Если args выглядит как "sales_<число>"
            if deep_link_param and deep_link_param.startswith("sales_"):
                try:
                    crm_id = int(deep_link_param.split("_", 1)[1])
                except ValueError:
                    crm_id = None

        # Проверяем, есть ли уже TelegramAccount с этой ролью
        existing = db.query(TelegramAccount).filter(
            TelegramAccount.telegram_id == tg_id
        ).first()

        if existing and existing.role == TelegramRole.sales:
            # Если уже зарегистрирован как продавец
            await message.answer(
                "Вы уже зарегистрированы как продажник. Выберите действие из меню:",
                reply_markup=crud.generate_sales_menu(),
            )
            return

        # Если аккаунта нет, регистрируем нового (передаём crm_id, если он есть)
        # В TgFuncs.register_telegram_account нужно дописать параметр crm_id
        crud.register_telegram_account(
            db,
            telegram_id=tg_id,
            role=TelegramRole.sales,
            crm_user_id=crm_id  # <-- сюда передаём ID из CRM (None, если аргумент некорректный)
        )
        if crm_id is not None:
            user_obj = db.query(User).filter(User.id == crm_id).first()
            if user_obj:
                user_obj.telegram_id = tg_id
                db.commit()

    finally:
        db.close()

    await message.answer(
        "Добро пожаловать, продажник! Ниже вы увидите доступные вам команды:",
        reply_markup=crud.generate_sales_menu(),
    )


@sales_bot_router.callback_query(F.data.startswith("take"))
async def take_client_callback(call: types.CallbackQuery):
    """
    Обработка callback от Inline-кнопки «Взять клиента»: callback_data="take:<client_tg_id>"
    """
    await call.answer()
    data = call.data.split(":")
    if len(data) != 2:
        return
    try:
        client_tg_id = int(data[1])
    except ValueError:
        return

    sales_tg_id = call.from_user.id
    db: Session = SessionLocal()
    try:
        # Находим «новый» запрос этого клиента
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.client_tg_id == client_tg_id,
                ClientRequest.status == ClientRequestStatus.new,
            )
            .order_by(ClientRequest.created_at.desc())
            .first()
        )
        if not req:
            await call.message.reply("Извините, этот запрос уже взяли другие.")
            return

        # Регистрируем (или подтверждаем) аккаунт продажника
        crud.register_telegram_account(db, sales_tg_id, role=TelegramRole.sales)

        # Обновляем статус запроса на 'taken'
        crud.take_client_request(db, req.id, sales_tg_id)

        # Переводим FSM-клиента в «режим переписки»
        # state_client = dp.current_state(chat=client_tg_id, user=client_tg_id)
        # await state_client.set_state("IN_CHAT_WITH_SALES")

        # Отправляем менеджеру меню «Привязать/Создать/Завершить»
        await call.message.reply(
            f"Вы взяли клиента {client_tg_id} в работу. Можете начать диалог. "
            f"По завершении нажмите кнопку «Завершить разговор».",
            reply_markup=crud.generate_sales_menu(),
        )

        # Уведомляем клиента
        await call.bot.send_message(
            client_tg_id, "Привет! Менеджер подключился к чату. Пишите сюда, он получил вашу заявку."
        )
    finally:
        db.close()


@sales_bot_router.message(F.text.in_(["Привязать к лиду", "Создать лид", "Завершить разговор"]))
async def handle_sales_menu(message: types.Message, state: FSMContext):
    """
    Обработчик ReplyKeyboard для управления «статусом разговора».
    Кнопки: «Привязать к лиду», «Создать лид», «Завершить разговор».
    """
    text = message.text
    sales_tg_id = message.from_user.id
    db: Session = SessionLocal()
    try:
        # Ищем активный запрос, взятый этим продавцом
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.sales_tg_id == sales_tg_id,
                ClientRequest.status == ClientRequestStatus.taken,
            )
            .order_by(ClientRequest.taken_at.desc())
            .first()
        )
        if not req:
            await message.answer("У вас нет активного клиента.")
            return

        if text == "Привязать к лиду":
            await message.answer(
                "Введите ID существующего лида (только цифры). Например: 1234"
            )
            await state.set_state(SalesStates.WAITING_LINK_ID)

        elif text == "Создать лид":
            await message.answer(
                "Введите данные нового лида в формате:\n"
                "<Полное имя>;<Телефон>;<Регион>;<Источник>\n"
                "Пример: Иван Петров;+998901234567;Ташкент;Instagram"
            )
            await state.set_state(SalesStates.WAITING_CREATE_LEAD)

        elif text == "Завершить разговор":
            # Закрываем клиентский запрос
            crud.close_client_request(db, req)

            # Снимаем состояние клиента из FSM
            # state_client = dp.current_state(chat=req.client_tg_id, user=req.client_tg_id)
            # await state_client.clear()

            # Уведомляем обе стороны
            await message.answer("Разговор завершён. Если нужно, создайте или привяжите лид.")
            await message.bot.send_message(
                req.client_tg_id, "Менеджер завершил диалог. Спасибо за обращение!"
            )
            await message.answer(
                "Для нового клиента снова нажмите «Взять клиента» в уведомлении или /start."
            )

    finally:
        db.close()


@sales_bot_router.message(SalesStates.WAITING_LINK_ID)
async def handle_sales_link_id(message: types.Message, state: FSMContext):
    """
    Ждём ввод ID лида (только цифры), чтобы привязать текущего клиента к существующему лид-карточке.
    """
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Неверный формат. Введите только цифры – ID существующего лида.")
        return

    lead_id = int(text)
    sales_tg_id = message.from_user.id
    db: Session = SessionLocal()
    try:
        lead_obj = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead_obj:
            await message.answer(f"Лид #{lead_id} не найден.")
            return

        # Берём текущий активный запрос
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.sales_tg_id == sales_tg_id,
                ClientRequest.status == ClientRequestStatus.taken,
            )
            .order_by(ClientRequest.taken_at.desc())
            .first()
        )
        if not req:
            await message.answer("У вас нет активного клиента.")
            return

        # Привязываем клиента к этому лиду
        req.lead_id = lead_id
        db.commit()

        await message.answer(
            f"Клиент (TG ID={req.client_tg_id}) привязан к лид-карточке #{lead_id}."
        )
        await state.clear()
    finally:
        db.close()


@sales_bot_router.message(SalesStates.WAITING_CREATE_LEAD)
async def handle_sales_create_lead(message: types.Message, state: FSMContext):
    """
    Ждём ввод для создания нового лида в формате:
      <Полное имя>;<Телефон>;<Регион>;<Источник>
    Затем создаём Lead и привязываем клиента к нему.
    """
    text = message.text.strip()
    parts = text.split(";")
    if len(parts) != 4:
        await message.answer(
            "Неверный формат. Введите через точку с запятой: "
            "<Полное имя>;<Телефон>;<Регион>;<Источник>"
        )
        return

    full_name, phone, region, contact_source = [p.strip() for p in parts]
    sales_tg_id = message.from_user.id
    db: Session = SessionLocal()
    try:
        # Создаём новый лид
        new_lead = Lead(
            full_name=full_name,
            phone=phone,
            region=region,
            contact_source=contact_source,
            status=LeadStatus.COLD,  # или строка-представление, как у вас определено
            state=LeadState.NEW,  # или тоже строка, если у вас так
            total_price=0.0,  # по умолчанию, чтобы не падало
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)

        # Берём текущий запрос
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.sales_tg_id == sales_tg_id,
                ClientRequest.status == ClientRequestStatus.taken,
            )
            .order_by(ClientRequest.taken_at.desc())
            .first()
        )
        if not req:
            await message.answer("У вас нет активного клиента.")
            return

        # Привязываем клиента к новому лид-карточке
        req.lead_id = new_lead.id
        db.commit()

        await message.answer(
            f"Создан новый лид #{new_lead.id} и привязан клиент TG ID={req.client_tg_id}."
        )
        await state.clear()
    finally:
        db.close()


@sales_bot_router.message()
async def sales_sends_text(message: types.Message):
    """
    Отправка сообщений от продажника клиенту.
    Сохраняем в табл. ChatMessage (новая модель) и пересылаем «forward» клиенту.
    """
    sales_tg_id = message.from_user.id
    db: Session = SessionLocal()
    try:
        # 1) Находим активный запрос, взятый этим sales
        req = (
            db.query(ClientRequest)
            .filter(
                ClientRequest.sales_tg_id == sales_tg_id,
                ClientRequest.status == ClientRequestStatus.taken,
            )
            .order_by(ClientRequest.taken_at.desc())
            .first()
        )
        if not req:
            # Если у продажи нет активного клиента — игнорируем
            return

        client_tg_id = req.client_tg_id
        lead_id = req.lead_id if req.lead_id is not None else -1

        # 2) Сохраняем текст в новую модель ChatMessage
        crud.save_chat_message(
            db=db,
            lead_id=lead_id,
            source="telegram",
            message_text=message.text or "[медиа]",
            sender_id=sales_tg_id,
            sender_role=SenderRole.SALES,
        )

        # 3) Форвардим сообщение клиенту
        await message.forward(client_tg_id)

    finally:
        db.close()
