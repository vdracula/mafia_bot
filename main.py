#!/usr/bin/env python3
import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
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

class MafiaBot:
    def __init__(self):
        self.app = None
        self.pool = None

    async def startup(self):
        """Инициализация при запуске"""
        try:
            self.pool = await init_db()
            logger.info("Бот инициализирован, БД подключена")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            return False

    async def shutdown(self):
        """Корректное завершение работы"""
        try:
            if self.pool:
                await self.pool.close()
                logger.info("Соединение с БД закрыто")
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}")

    def register_handlers(self):
        """Регистрация всех обработчиков"""
        from handlers.start_handler import start, help_command
        from handlers.room_handlers import create_room, join_room, list_rooms, message_handler
        from handlers.role_handlers import set_roles_start
        from handlers.game_handlers import start_game
        from handlers.admin_handlers import admin_panel
        from handlers.callback_handler import handle_callbacks

        # Основные команды
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("help", help_command))
        
        # Комнаты
        self.app.add_handler(CommandHandler("create_room", create_room))
        self.app.add_handler(CommandHandler("join_room", join_room))
        self.app.add_handler(CommandHandler("rooms", list_rooms))
        
        # Игра
        self.app.add_handler(CommandHandler("start_game", start_game))
        self.app.add_handler(CommandHandler("set_roles", set_roles_start))
        
        # Админка
        self.app.add_handler(CommandHandler("admin", admin_panel))
        
        # Обработчики
        self.app.add_handler(CallbackQueryHandler(handle_callbacks))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    async def run(self):
        """Основная функция запуска"""
        try:
            self.app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
            self.app.bot_data['pool'] = self.pool
            
            if not await self.startup():
                return

            self.register_handlers()
            
            logger.info("Запуск бота...")
            await self.app.run_polling()

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            await self.shutdown()

if __name__ == '__main__':
    bot = MafiaBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")