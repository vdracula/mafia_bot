# handlers/callback_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from handlers.start_handler import start
from handlers.room_handlers import select_room_handler, show_current_roles
from handlers.role_handlers import edit_role_count, update_role_count, confirm_roles
from handlers.game_handlers import vote_handler
from handlers.admin_handlers import admin_button_handler, admin_panel

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    print(f"[DEBUG] Получен callback: {data}")

    if data == "menu_play":
        from handlers.start_handler import main_menu_handler
        await main_menu_handler(update, context)
    elif data.startswith("room_info_"):
        from handlers.start_handler import main_menu_handler
        await main_menu_handler(update, context)
    elif data == "menu_help":
        from handlers.start_handler import main_menu_handler
        await main_menu_handler(update, context)
    elif data == "auto_join_prompt":
        from handlers.room_handlers import find_game
        await find_game(query, context)
        await query.edit_message_text("Вы автоматически присоединились к комнате.")
    elif data == "menu_back":
        from handlers.start_handler import main_menu_handler
        await main_menu_handler(update, context)
    elif data.startswith("select_join_"):
        await select_room_handler(update, context)
    elif data.startswith("edit_"):
        await edit_role_count(update, context)
    elif data.startswith("set_"):
        await update_role_count(update, context)
    elif data == "confirm_roles":
        await confirm_roles(update, context)
    elif data.startswith("vote_"):
        await vote_handler(update, context)
    elif data in ["restart_game_admin", "end_game_admin", "view_history"]:
        await admin_button_handler(update, context)
    elif data.startswith("restart_room_"):
        await admin_button_handler(update, context)
    elif data == "menu_back_admin":
        await admin_panel(update, context)
    else:
        await query.edit_message_text("Неизвестное действие.")