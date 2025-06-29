import random
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers import *
import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

async def post_init(app):
    print("Бот успешно запущен!")

if __name__ == '__main__':
    app = ApplicationBuilder() \
        .token(os.getenv("TELEGRAM_BOT_TOKEN")) \
        .post_init(post_init) \
        .build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("join_room", join_room))
    app.add_handler(CommandHandler("rooms", list_rooms))
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()