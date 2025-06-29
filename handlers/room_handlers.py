# handlers/room_handlers.py

__all__ = ["create_room", "join_room", "list_rooms", "message_handler", "select_room_handler"]
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import rooms
from utils import get_user_name, assign_roles, send_private_role

async def find_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    found = False
    for room_name, room in rooms.items():
        if not room["started"] and len(room["players"]) < 8:
            room["players"].append(user_id)
            await update.message.reply_text(f"✅ Вы присоединились к комнате '{room_name}'.")
            found = True
            break
    if not found:
        new_room = f"room_{len(rooms) + 1}"
        rooms[new_room] = {
            "host": user_id,
            "chat_id": update.effective_chat.id,
            "players": [user_id],
            "roles": {"Мафия": 1, "Доктор": 1, "Комиссар": 1, "Мирный житель": 5},
            "assigned_roles": {},
            "started": False,
            "stage": None,
            "votes": {}
        }
        await update.message.reply_text(f"✅ Создана новая комната: {new_room}")
        
async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update, Update):
        await update.message.reply_text("Введите название новой комнаты:")
    else:
        await update.edit_message_text("Введите название новой комнаты:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if context.user_data.get('waiting_for_room_name'):
        room_name = text
        if room_name in rooms:
            await update.message.reply_text("Комната с таким названием уже существует.")
            return

        from config import YOUR_ADMIN_ID
        rooms[room_name] = {
            "host": user_id,
            "chat_id": update.effective_chat.id,
            "players": [],
            "roles": {
                "Мафия": 1,
                "Доктор": 1,
                "Комиссар": 1,
                "Мирный житель": 5
            },
            "assigned_roles": {},
            "started": False,
            "stage": None,
            "votes": {}
        }

        await update.message.reply_text(f"✅ Комната '{room_name}' успешно создана!")
        rooms[room_name]["players"].append(user_id)
        await update.message.reply_text(f"Вы автоматически присоединились к комнате '{room_name}'.")
        await show_current_roles(update, context, room_name, rooms[room_name])

async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rooms:
        await update.message.reply_text("Нет доступных комнат.")
        return

    keyboard = [[InlineKeyboardButton(room_name, callback_data=f"select_join_{room_name}")] for room_name in rooms]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите комнату, к которой хотите присоединиться:", reply_markup=reply_markup)

async def select_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("select_join_"):
        room_name = data.replace("select_join_", "")
        if room_name in rooms:
            room = rooms[room_name]
            if query.from_user.id in room["players"]:
                await query.edit_message_text("Вы уже состоите в этой комнате.")
                return
            room["players"].append(query.from_user.id)
            await query.edit_message_text(f"✅ Вы присоединились к комнате '{room_name}'.")
            await show_current_roles(query, context, room_name, room)

async def show_current_roles(update: Update, context: ContextTypes.DEFAULT_TYPE, room_name=None, room=None):
    if not room_name or not room:
        user_id = update.effective_user.id
        for rn, r in rooms.items():
            if user_id in r["players"]:
                room_name = rn
                room = r
                break
        else:
            return
    msg = "🎭 Текущие роли:\n"
    for role, count in room["roles"].items():
        msg += f"{role}: {count}\n"
    total = sum(room["roles"].values())
    msg += f"\nОбщее количество игроков: {total}"
    await update.message.reply_text(msg)

    # handlers/room_handlers.py

async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rooms:
        await update.message.reply_text("Пока нет активных комнат.")
        return

    msg = "🚪 Доступные комнаты:\n"
    for room_name, room in rooms.items():
        status = "🎮 В игре" if room["started"] else "🕒 Ожидает игроков"
        players_count = len(room["players"])
        msg += f"• {room_name} ({players_count} игроков) — {status}\n"

    await update.message.reply_text(msg)

__all__ = ["create_room", "join_room", "list_rooms", "message_handler", "select_room_handler"]