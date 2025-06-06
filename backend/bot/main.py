import asyncio
import logging

from aiogram import Bot, Dispatcher

from backend.bot.handlers.client_handlers import client_bot_router
from backend.bot.handlers.sales_handlers import sales_bot_router

TOKEN = "6463653390:AAFCmUhro2O-FpGcTwlAlUIu_R3_Pq24WJ0"


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(sales_bot_router)
    dp.include_router(client_bot_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())