from aiogram.fsm.state import StatesGroup, State


class ClientStates(StatesGroup):
    WAITING_FOR_REQUEST = State()
    IN_CHAT_WITH_SALES = State()


class SalesStates(StatesGroup):
    WAITING_LINK_ID = State()
    WAITING_CREATE_LEAD = State()