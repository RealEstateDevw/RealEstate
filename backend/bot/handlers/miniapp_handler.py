"""Telegram Mini App bot handler."""
import asyncio
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import logger
from settings import settings
from backend.database import SessionLocal
from backend.api.miniapp.crud import miniapp_crud
from backend.database.sales_service.crud import lead_crud
from backend.api.leads.schemas import LeadCreate
from backend.database.models import LeadStatus, LeadState


miniapp_router = Router()


class ContactStates(StatesGroup):
    """FSM states for contact collection."""
    waiting_for_contact = State()


def get_miniapp_url(payload: str = "") -> str:
    """Get Mini App URL with optional payload."""
    base_url = settings.MINIAPP_URL or "https://your-domain.com"
    if payload:
        return f"{base_url}/complexes?source={payload}"
    return f"{base_url}/complexes"


@miniapp_router.message(CommandStart(deep_link=True))
async def cmd_start_with_payload(message: Message, command: CommandObject, state: FSMContext):
    """
    Handle /start PAYLOAD - entry from ads.
    """
    payload = command.args or "telegram"
    tg_id = message.from_user.id

    logger.info(f"User {tg_id} started bot with payload: {payload}")

    db = SessionLocal()
    try:
        # Create or update user with source_payload
        user = miniapp_crud.get_or_create_user(
            db=db,
            telegram_id=tg_id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
            source_payload=payload
        )

        # Check for pending request (user came back from Mini App)
        pending = miniapp_crud.get_pending_request(db, user.id)

        if pending:
            # Show apartment confirmation
            await show_apartment_confirmation(message, pending)
        else:
            # Show Mini App button
            await show_miniapp_button(message, payload)

    finally:
        db.close()


@miniapp_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle /start without payload.
    """
    tg_id = message.from_user.id

    logger.info(f"User {tg_id} started bot without payload")

    db = SessionLocal()
    try:
        # Create or update user
        user = miniapp_crud.get_or_create_user(
            db=db,
            telegram_id=tg_id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username
        )

        # Check for pending request
        pending = miniapp_crud.get_pending_request(db, user.id)

        if pending:
            await show_apartment_confirmation(message, pending)
        else:
            await show_miniapp_button(message, "telegram")

    finally:
        db.close()


async def show_miniapp_button(message: Message, payload: str):
    """Show button to open Mini App catalog."""
    user_name = message.from_user.first_name or "друг"
    text = (
        f"Привет, {user_name}! Добро пожаловать в Bahor JK Bot.\n\n"
        "Здесь вы можете:\n"
        "• Посмотреть доступные квартиры\n"
        "• Узнать цены и условия рассрочки\n"
        "• Оставить заявку на понравившуюся квартиру\n\n"
        "Нажмите кнопку ниже, чтобы открыть каталог:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Смотреть квартиры",
            web_app=WebAppInfo(url=get_miniapp_url(payload))
        )]
    ])

    await message.answer(text, reply_markup=kb)


async def show_apartment_confirmation(message: Message, request):
    """Show message: 'Looks like you're interested in apartment X'."""
    text = "Похоже, вас заинтересовала квартира:\n\n"
    text += f"ЖК: {request.complex_name}\n"
    text += f"Блок: {request.block_name}, Этаж: {request.floor}\n"
    text += f"Квартира №{request.unit_number}"

    if request.area_sqm:
        text += f", {request.area_sqm} м²"
    if request.rooms:
        text += f", {request.rooms}-комн."
    text += "\n"

    if request.price_snapshot:
        text += f"Цена: {request.price_snapshot:,.0f} сум\n"

    if request.payment_type_interest:
        text += f"Способ оплаты: {request.payment_type_interest}\n"

    text += "\nЭто та квартира, по которой у вас вопрос?"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, эта", callback_data=f"confirm:{request.id}"),
            InlineKeyboardButton(text="Нет, другая", callback_data="choose_another")
        ],
        [InlineKeyboardButton(text="Общий вопрос", callback_data="general_question")]
    ])

    await message.answer(text, reply_markup=kb)


@miniapp_router.callback_query(F.data.startswith("confirm:"))
async def handle_confirm(callback: CallbackQuery, state: FSMContext):
    """User confirmed interest - request contact."""
    request_id = int(callback.data.split(":")[1])

    db = SessionLocal()
    try:
        request = miniapp_crud.get_request_by_id(db, request_id)
        if not request:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Mark as confirmed
        miniapp_crud.confirm_request(db, request_id)

        # Store request_id in FSM for later use
        await state.update_data(request_id=request_id)
        await state.set_state(ContactStates.waiting_for_contact)

        # Request phone number
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await callback.message.answer(
            "Отлично! Для связи с вами, пожалуйста, поделитесь номером телефона:",
            reply_markup=kb
        )
        await callback.answer()

    finally:
        db.close()


@miniapp_router.callback_query(F.data == "choose_another")
async def handle_choose_another(callback: CallbackQuery):
    """User wants to look at other apartments."""
    await callback.message.answer(
        "Хорошо! Вы можете выбрать другую квартиру в каталоге:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Открыть каталог",
                web_app=WebAppInfo(url=get_miniapp_url())
            )]
        ])
    )
    await callback.answer()


@miniapp_router.callback_query(F.data == "general_question")
async def handle_general_question(callback: CallbackQuery, state: FSMContext):
    """User has a general question."""
    await state.set_state(ContactStates.waiting_for_contact)
    await state.update_data(request_id=None, is_general=True)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "Хорошо! Поделитесь номером телефона, и наш менеджер свяжется с вами:",
        reply_markup=kb
    )
    await callback.answer()


@miniapp_router.message(ContactStates.waiting_for_contact, F.contact)
async def handle_contact(message: Message, state: FSMContext):
    """Handle received contact - create CRM lead."""
    phone = message.contact.phone_number
    tg_id = message.from_user.id

    data = await state.get_data()
    request_id = data.get("request_id")
    is_general = data.get("is_general", False)

    db = SessionLocal()
    try:
        # Update user phone
        user = miniapp_crud.update_user_phone(db, tg_id, phone)

        if not user:
            await message.answer(
                "Произошла ошибка. Пожалуйста, попробуйте снова.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Get request details if exists
        request = None
        if request_id:
            request = miniapp_crud.get_request_by_id(db, request_id)

        # Create CRM lead
        lead = await create_crm_lead(db, user, request, is_general)

        if lead and request:
            # Mark request as converted
            miniapp_crud.convert_to_lead(db, request_id, lead.id)

        # Send confirmation
        await message.answer(
            "Спасибо! Ваша заявка принята.\n"
            "Наш менеджер свяжется с вами в ближайшее время.",
            reply_markup=ReplyKeyboardRemove()
        )

        # Clear state
        await state.clear()

    finally:
        db.close()


@miniapp_router.message(ContactStates.waiting_for_contact)
async def handle_waiting_text(message: Message):
    """Handle text when waiting for contact."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Пожалуйста, нажмите кнопку ниже, чтобы поделиться номером телефона:",
        reply_markup=kb
    )


async def create_crm_lead(db, user, request, is_general: bool = False):
    """Create Lead in CRM system."""
    try:
        # Determine lead status based on interest score
        status = LeadStatus.NEW
        lead_state = LeadState.COLD

        if request and request.interest_score:
            if request.interest_score > 15:
                lead_state = LeadState.HOT
            elif request.interest_score > 8:
                lead_state = LeadState.WARM

        # Build full name
        full_name = ""
        if user.first_name:
            full_name = user.first_name
        if user.last_name:
            full_name += f" {user.last_name}"
        full_name = full_name.strip() or f"Telegram {user.telegram_id}"

        # Create lead data
        lead_data = LeadCreate(
            full_name=full_name,
            phone=user.phone or "",
            region="Ташкент",
            contact_source=user.source_payload,
            status=status,
            state=lead_state,
            complex_name=request.complex_name if request else None,
            block=request.block_name if request else None,
            floor=request.floor if request else None,
            square_meters=request.area_sqm if request else None,
            rooms=request.rooms if request else None,
            total_price=request.price_snapshot if request else None,
            payment_type=request.payment_type_interest if request else "Не указано",
            notes=f"Telegram Mini App. Score: {request.interest_score if request else 'N/A'}"
        )

        # Create lead
        lead = lead_crud.create_lead(db, lead_data)

        # Update lead with telegram info
        lead.telegram_user_id = user.telegram_id
        if request:
            lead.interest_score_snapshot = request.interest_score
        db.commit()

        logger.info(f"Created CRM lead {lead.id} for telegram user {user.telegram_id}")
        return lead

    except Exception as e:
        logger.exception(f"Failed to create CRM lead: {e}")
        return None
