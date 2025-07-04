import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import create_async_engine

from models import Base
from database import DATABASE_URL
from handlers import main, game, voting


BOT_TOKEN = os.environ["BOT_TOKEN"]

# Создаём бот и диспетчер
bot = Bot(token=BOT_TOKEN, default=None)
dp = Dispatcher()

# Функция автоматического создания таблиц
async def create_tables():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

# Регистрируем роутеры
dp.include_router(main.router)
dp.include_router(game.router)
dp.include_router(voting.router)

# Запуск
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_tables())  # Сначала создаём таблицы
    dp.run_polling(bot)           # Потом запускаем бота
