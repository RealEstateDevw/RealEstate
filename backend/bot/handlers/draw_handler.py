from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, \
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from sqlalchemy.exc import NoResultFound
from backend.database import SessionLocal
from backend.database.marketing.crud import DrawUserCRUD
from backend.database.models import UserLang

draw_router = Router()
crud = DrawUserCRUD()


class Registration(StatesGroup):
    lang = State()  # выбор языка
    name = State()  # ввод имени
    surname = State()  # ввод фамилии
    phone = State()  # получение контакта


@draw_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Открываем сессию и пробуем найти пользователя
    db = SessionLocal()
    try:
        existing = crud.get_exact_draw_user(db, message.from_user.id)
    except NoResultFound:
        existing = None
    finally:
        db.close()

    if existing:
        # Пользователь уже есть — показываем приветствие на его языке
        if existing.lang == UserLang.ru:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="О жилом комплексе", callback_data="about_complex")]]
            )
            await message.answer(
                "Здравствуйте! 👋\n"
                "Вы находитесь в официальном боте ЖК «Рассвет». "
                "Здесь вы можете узнать подробнее о комплексе, посмотреть планировки и зарегистрироваться на День открытых дверей.",
                reply_markup=kb
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="Majmua haqida", callback_data="about_complex")]]
            )
            await message.answer(
                "Assalomu alaykum! 👋\n"
                "Siz “Rassvet” turar joy majmuasining rasmiy botidasiz. "
                "Bu yerda kompleks haqida batafsil ma'lumot olishingiz, planirovkalarni ko‘rishingiz va Ochiq eshiklar kuniga ro‘yxatdan o‘tishingiz mumkin.",
                reply_markup=kb
            )
        return

    # Иначе — начинаем регистрацию
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Русский"), KeyboardButton(text="O'zbekcha")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выберите язык / Tilni tanlang:", reply_markup=kb)
    await state.set_state(Registration.lang)


@draw_router.message(Registration.lang)
async def process_lang(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text == "русский":
        lang = UserLang.ru
    elif text in ("o'zbekcha", "uzbekcha"):
        lang = UserLang.uz
    else:
        return await message.answer("Пожалуйста, выберите язык кнопкой: Русский или O'zbekcha.")

    await state.update_data(lang=lang)

    if lang == UserLang.ru:
        intro = (
            "Здравствуйте! 👋\n"
            "Вы находитесь в официальном боте регистрации на День открытых дверей ЖК «Рассвет», который состоится 15 июня.\n\n"
            "У вас будет возможность:\n"
            "🏡 — Посмотреть готовые шоурумы\n"
            "🎁 — Получить подарки при покупке квартиры\n"
            "🚗 — Принять участие в розыгрыше автомобиля!\n\n"
            "Давайте оформим вашу регистрацию. Это займёт всего минуту!"
        )
        prompt = "Пожалуйста, введите ваше имя:"
    else:
        intro = (
            "Assalomu alaykum! 👋\n"
            "Siz \"Rassvet\" turar joy majmuasining Ochiq eshiklar kuni uchun rasmiy ro‘yxatdan o‘tish botidasiz. Tadbir 15-iyun kuni bo‘lib o‘tadi.\n\n"
            "Sizni quyidagilar kutmoqda:\n"
            "🏡 — Tayyor shourumlarni ko‘rish\n"
            "🎁 — Kvartira xaridi uchun sovg‘alar\n"
            "🚗 — Yangi avtomobil yutib olish imkoniyati!\n\n"
            "Keling, ro‘yxatdan o‘tamiz. Bu atigi bir daqiqa vaqt oladi."
        )
        prompt = "Iltimos, ismingizni kiriting:"

    await message.answer(intro, reply_markup=ReplyKeyboardRemove())
    await message.answer(prompt)
    await state.set_state(Registration.name)


@draw_router.message(Registration.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    data = await state.get_data()
    reply = "Спасибо! Теперь введите вашу фамилию:" if data[
                                                           "lang"] == UserLang.ru else "Rahmat! Endi familiyangizni kiriting:"
    await message.answer(reply)
    await state.set_state(Registration.surname)


@draw_router.message(Registration.surname)
async def process_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    data = await state.get_data()

    if data["lang"] == UserLang.ru:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отправить мой номер телефона", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        prompt = "Пожалуйста, нажмите на кнопку и отправьте ваш номер телефона:"
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamimni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        prompt = "Iltimos, telefon raqamingizni yuboring:"

    await message.answer(prompt, reply_markup=kb)
    await state.set_state(Registration.phone)


@draw_router.message(Registration.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    user_data = {
        "telegram_id": message.from_user.id,
        "first_name": data["name"],
        "last_name": data["surname"],
        "phone": message.contact.phone_number,
        "lang": data["lang"],
    }

    # Сохраняем в БД
    db = SessionLocal()
    try:
        crud.add_draw_user(db, **user_data)
    finally:
        db.close()

    # Отправляем подтверждение
    if data["lang"] == UserLang.ru:
        confirm = (
            "✅ Спасибо! Вы успешно зарегистрированы на День открытых дверей ЖК «Рассвет».\n\n"
            "📍 Адрес: ул. Амир Темур, 125, г. Чирчик\n"
            "⏰ Начало: 15:00\n\n"
            "Мы свяжемся с вами ближе к дате события. Не забудьте пригласить родных и друзей — будет интересно!"
        )
    else:
        confirm = (
            "✅ Rahmat! Siz 15-iyun kuni bo‘lib o‘tadigan \"Rassvet\" MJM ochiq eshiklar kuniga muvaffaqiyatli ro‘yxatdan o‘tdingiz.\n\n"
            "📍 Manzil: ул. Амир Темур, 125, г. Чирчик\n"
            "⏰ Boshlanish vaqti: 15:00\n\n"
            "Tadbir sanasiga yaqin biz siz bilan aloqaga chiqamiz. Oila a'zolaringiz va do‘stlaringizni ham taklif qiling — qiziqarli bo‘ladi!"
        )

    await message.answer(confirm, reply_markup=ReplyKeyboardRemove())
    await state.clear()


@draw_router.callback_query(F.data == "about_complex")
async def about_complex_handler(callback: CallbackQuery):
    await callback.answer()

    # Берём пользователя из БД
    db = SessionLocal()
    try:
        user = crud.get_exact_draw_user(db, callback.from_user.id)
    finally:
        db.close()

    # Формируем подпись и отправляем фото
    if user.lang == UserLang.ru:
        caption = (
            "🏙 О жилом комплексе «Рассвет»\n\n"
            "ЖК «Рассвет» — это современный жилой комплекс класса Комфорт+, "
            "расположенный в экологически чистом районе города Чирчик, рядом с Ормон Парком.\n\n"
            "📍 Адрес: ул. Амир Темур, 125, г. Чирчик\n\n"
            "⸻\n\n"
            "🔹 Преимущества:\n"
            "▪️ Современные планировки: 1-, 2-, 3-комнатные квартиры\n"
            "▪️ Коммерческие помещения от 54 до 107 м²\n"
            "▪️ Удобная локация: рядом школы, детсады, магазины, институт, больница\n"
            "▪️ Зелёная и тихая зона, рядом Экопарк"
        )
    else:
        caption = (
            "🏙 «Rassvet» turar joy majmuasi haqida\n\n"
            "«Rassvet» — bu Komfort+ sinfidagi zamonaviy turar joy majmuasi bo‘lib, "
            "Chirchik shahrining ekologik toza hududida, Ormon parkiga yaqin joylashgan.\n\n"
            "📍 Manzil: Amir Temur ko‘chasi, 125, Chirchik shahr\n\n"
            "⸻\n\n"
            "🔹 Afzalliklari:\n"
            "▪️ Zamonaviy rejalashtirishlar: 1-, 2-, 3-xonali kvartiralar\n"
            "▪️ Tijorat maydonlari: 54 dan 107 m² gacha\n"
            "▪️ Qulay infratuzilma: maktablar, bog‘cha, do‘konlar, institut, shifoxona yaqinida\n"
            "▪️ Yashil va tinch zona, Ekopark yonida"
        )

    photo_path = "static/images/IMG_6956.JPG"
    await callback.message.answer_photo(photo=FSInputFile(photo_path), caption=caption)
