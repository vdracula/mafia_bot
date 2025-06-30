import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]

# Создаем бота и диспетчер
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Импорт роутеров
from handlers import main, game, voting

# Регистрируем роутеры
dp.include_router(main.router)
dp.include_router(game.router)
dp.include_router(voting.router)


async def main_runner():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main_runner())

from aiogram.client.default import DefaultBotProperties

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://{YOUR_DOMAIN_OR_RAILWAY_URL}{WEBHOOK_PATH}"

# При запуске:
await bot.set_webhook(WEBHOOK_URL)
