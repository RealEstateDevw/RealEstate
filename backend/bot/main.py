import asyncio
import logging

from aiogram import Bot, Dispatcher

from backend.bot.handlers.client_handlers import client_bot_router
from backend.bot.handlers.draw_handler import draw_router
from backend.bot.handlers.sales_handlers import sales_bot_router
from config import logger

TOKEN = "8065762456:AAH5lAM0w9edqUAG09qOTzSIStj4u2egHf0"


async def run_bot():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    # dp.include_router(sales_bot_router)
    # dp.include_router(client_bot_router)
    dp.include_router(draw_router)
    while True:
        try:
            logger.info("Запускаем Aiogram polling…")
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            # поймали ошибку, залогировали и перезапускаем через 5 секунд
            logger.exception("Polling упал с ошибкой, перезапускаем через 5 сек…")
            await asyncio.sleep(5)
            print()
        else:
            # start_polling вернётся лишь при cancel() — выходим из цикла
            break

    await bot.session.close()
    logger.info("Bot session closed")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())