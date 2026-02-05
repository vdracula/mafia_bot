import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from db import Database
from middlewares import DBMiddleware
from game.handlers import router
from core import bot as core_bot


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

if not TOKEN or not DB_URL:
    raise ValueError("❌ BOT_TOKEN и/или DATABASE_URL не заданы в .env")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# прокидываем экземпляр в core, чтобы использовать в game.handlers
core_bot = bot  # type: ignore

dp = Dispatcher()
dp.include_router(router)


async def main():
    logging.basicConfig(level=logging.INFO)

    db = Database(DB_URL)
    await db.connect()

    dp.message.middleware(DBMiddleware(db))
    dp.callback_query.middleware(DBMiddleware(db))

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
