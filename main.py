# main.py

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers.start_handler import start, help_command
from handlers.room_handlers import create_room, join_room, list_rooms, message_handler, select_room_handler
from handlers.role_handlers import set_roles_start, edit_role_count, update_role_count, confirm_roles
from handlers.game_handlers import start_game, vote_handler
from handlers.admin_handlers import admin_panel, admin_button_handler
from handlers.callback_handler import handle_callbacks

if __name__ == '__main__':
    from config import TELEGRAM_BOT_TOKEN

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("join_room", join_room))
    app.add_handler(CommandHandler("rooms", list_rooms))
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    app.add_handler(CommandHandler("find_game", find_game))
    app.add_handler(CommandHandler("admin", admin_panel))

    # Кнопки
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    # Обработка текстовых сообщений
    app.add_handler(message_handler)

    print("Бот запущен...")
    app.run_polling()