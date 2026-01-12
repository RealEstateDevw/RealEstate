import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import logger
from settings import settings
from backend.bot.handlers.miniapp_handler import miniapp_router


async def run_bot():
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Include Mini App router
    dp.include_router(miniapp_router)

    while True:
        try:
            logger.info("Запускаем Aiogram polling…")
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            logger.exception("Polling упал с ошибкой, перезапускаем через 5 сек…")
            await asyncio.sleep(5)
        else:
            break

    await bot.session.close()
    logger.info("Bot session closed")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())
