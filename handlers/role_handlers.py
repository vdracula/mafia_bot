# handlers/role_handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import rooms

async def set_roles_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    for room_name, room in rooms.items():
        if user_id == room["host"] and not room["started"]:
            keyboard = [
                [InlineKeyboardButton("Мафия", callback_data="edit_mafia")],
                [InlineKeyboardButton("Доктор", callback_data="edit_doctor")],
                [InlineKeyboardButton("Комиссар", callback_data="edit_sheriff")],
                [InlineKeyboardButton("Мирный житель", callback_data="edit_peaceful")],
                [InlineKeyboardButton("Подтвердить настройки", callback_data="confirm_roles")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите роль для изменения:", reply_markup=reply_markup)
            return
    await update.message.reply_text("Вы не являетесь ведущим или игра уже началась.")

async def edit_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role_key = query.data.replace("edit_", "")
    role_map = {
        "mafia": "Мафия",
        "doctor": "Доктор",
        "sheriff": "Комиссар",
        "peaceful": "Мирный житель"
    }
    role = role_map.get(role_key)
    if not role:
        return

    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return

    room = rooms[room_name]
    current_count = room["roles"][role]
    buttons = []
    for delta in [-1, 0, +1]:
        new_count = max(0, current_count + delta)
        buttons.append(
            InlineKeyboardButton(str(new_count), callback_data=f"set_{role_key}_{new_count}")
        )
    keyboard = [[*buttons]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Выберите количество для роли '{role}':", reply_markup=reply_markup)

async def update_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    role_key = data[1]
    count = int(data[2])
    role_map = {
        "mafia": "Мафия",
        "doctor": "Доктор",
        "sheriff": "Комиссар",
        "peaceful": "Мирный житель"
    }
    role = role_map.get(role_key)
    if not role:
        return

    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return

    room = rooms[room_name]
    room["roles"][role] = count
    keyboard = [
        [InlineKeyboardButton("Мафия", callback_data="edit_mafia")],
        [InlineKeyboardButton("Доктор", callback_data="edit_doctor")],
        [InlineKeyboardButton("Комиссар", callback_data="edit_sheriff")],
        [InlineKeyboardButton("Мирный житель", callback_data="edit_peaceful")],
        [InlineKeyboardButton("Подтвердить настройки", callback_data="confirm_roles")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите роль для изменения:", reply_markup=reply_markup)

async def confirm_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return
    room = rooms[room_name]
    total_players = sum(room["roles"].values())
    msg = f"✅ Роли установлены:\n"
    for role, count in room["roles"].items():
        msg += f"{role}: {count}\n"
    msg += f"\nОбщее количество игроков: {total_players}"
    await query.edit_message_text(msg)