#!/usr/bin/env python3
import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from db import init_db, create_pool

# Загружаем переменные окружения
load_dotenv()

async def post_init(app):
    """Функция инициализации после запуска бота"""
    print("Бот успешно запущен!")
    # Инициализируем БД и сохраняем пул соединений
    pool = await init_db()
    app.bot_data['pool'] = pool

async def register_handlers(app):
    """Регистрация всех обработчиков"""
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
    
    # Обработчики callback'ов и сообщений
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение
        app = ApplicationBuilder() \
            .token(os.getenv("TELEGRAM_BOT_TOKEN")) \
            .post_init(post_init) \
            .build()

        # Регистрируем обработчики
        await register_handlers(app)

        # Запускаем бота
        print("Запуск бота...")
        await app.run_polling()

    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        # Закрываем соединения с БД при завершении
        if 'pool' in app.bot_data:
            await app.bot_data['pool'].close()

if __name__ == '__main__':
    asyncio.run(main())