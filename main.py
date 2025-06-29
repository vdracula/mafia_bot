from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler
)
from config import TELEGRAM_BOT_TOKEN
from db import init_db

# Импорты обработчиков
from handlers.menu_handlers import show_main_menu
from handlers.start_handler import help_command
from handlers.room_handlers import (
    create_room_button, list_rooms, join_room_button
)
from handlers.game_handlers import (
    start_game, check_status_button,
    start_vote, handle_vote, end_vote
)
from handlers.role_handlers import (
    set_roles_start, edit_role_count,
    update_role_count, confirm_roles
)
from handlers.admin_handlers import (
    shutdown, admin_stats, clean_db,
    broadcast, show_end_buttons, record_winner
)

import nest_asyncio
nest_asyncio.apply()
import logging
logging.basicConfig(level=logging.INFO)

# здесь мы просто создаем Application
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


async def setup():
    # Инициализируем БД
    pool = await init_db()
    app.bot_data['pool'] = pool

    # Команды
    app.add_handler(CommandHandler("start", show_main_menu))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    app.add_handler(CommandHandler("start_vote", start_vote))
    app.add_handler(CommandHandler("end_game", show_end_buttons))

    # Админ-команды
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("clean_db", clean_db))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Callback-кнопки
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(create_room_button, pattern="^create_room$"))
    app.add_handler(CallbackQueryHandler(list_rooms, pattern="^join_room$"))
    app.add_handler(CallbackQueryHandler(join_room_button, pattern="^join_room_"))
    app.add_handler(CallbackQueryHandler(check_status_button, pattern="^check_status$"))
    app.add_handler(CallbackQueryHandler(edit_role_count, pattern="^edit_"))
    app.add_handler(CallbackQueryHandler(update_role_count, pattern="^set_"))
    app.add_handler(CallbackQueryHandler(confirm_roles, pattern="^confirm_roles$"))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern="^vote_"))
    app.add_handler(CallbackQueryHandler(end_vote, pattern="^end_vote_"))
    app.add_handler(CallbackQueryHandler(record_winner, pattern="^game_end_"))

# Запускаем setup() в существующем loop
asyncio.get_event_loop().run_until_complete(setup())

# Запускаем приложение синхронно
app.run_polling()
