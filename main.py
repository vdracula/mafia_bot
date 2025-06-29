import asyncio
import logging
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv

from config import TELEGRAM_BOT_TOKEN
from db import init_db
from handlers.start_handler import start, help_command
from handlers.room_handlers import create_room
from handlers.game_handlers import start_game

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run():
    pool = await init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data['pool'] = pool

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("start_game", start_game))

    logger.info("Бот запущен")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(run())