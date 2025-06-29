#!/usr/bin/env python3
import os
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from db import init_db

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

async def startup(app):
    """Инициализация при запуске"""
    try:
        # Инициализация БД
        pool = await init_db()
        app.bot_data['pool'] = pool
        logger.info("Бот инициализирован, БД подключена")
    except Exception as e:
        logger.error(f"Ошибка инициализации: {e}")
        raise

async def shutdown(app):
    """Корректное завершение работы"""
    try:
        if 'pool' in app.bot_data:
            await app.bot_data['pool'].close()
            logger.info("Соединение с БД закрыто")
    except Exception as e:
        logger.error(f"Ошибка при завершении работы: {e}")

def register_handlers(app):
    """Регистрация всех обработчиков"""
    from handlers.start_handler import start, help_command
    from handlers.room_handlers import create_room, join_room, list_rooms, message_handler
    from handlers.role_handlers import set_roles_start
    from handlers.game_handlers import start_game
    from handlers.admin_handlers import admin_panel
    from handlers.callback_handler import handle_callbacks

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Комнаты
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("join_room", join_room))
    app.add_handler(CommandHandler("rooms", list_rooms))
    
    # Игра
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    
    # Админка
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Обработчики
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

async def run_bot():
    """Основная функция запуска"""
    try:
        app = ApplicationBuilder() \
            .token(os.getenv("TELEGRAM_BOT_TOKEN")) \
            .post_init(startup) \
            .post_stop(shutdown) \
            .build()

        register_handlers(app)
        
        logger.info("Запуск бота...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Бесконечный цикл до остановки
        while True:
            await asyncio.sleep(3600)  # Проверка каждые 60 минут
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if 'app' in locals():
            logger.info("Остановка бота...")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")