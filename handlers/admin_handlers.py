# handlers/admin_handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import rooms

YOUR_ADMIN_ID = 775424515  # замените на ваш ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("🔒 У вас нет доступа.")
        return
    text = "🛠 Админ-панель:\n"
    for room_name, room in rooms.items():
        text += f"Комната: {room_name}\n Игроков: {len(room['players'])}\n Статус: {'🎮 В игре' if room['started'] else '🕒 Ожидает'}\n"
    keyboard = [
        [InlineKeyboardButton("Завершить игру", callback_data="end_game_admin")],
        [InlineKeyboardButton("Перезапустить игру", callback_data="restart_game_admin")],
        [InlineKeyboardButton("Посмотреть историю", callback_data="view_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "restart_game_admin":
        keyboard = [[InlineKeyboardButton(room_name, callback_data=f"restart_room_{room_name}")] for room_name in rooms]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите комнату для перезапуска:", reply_markup=reply_markup)
    elif data.startswith("restart_room_"):
        room_name = data.replace("restart_room_", "")
        if room_name in rooms:
            room = rooms[room_name]
            room["started"] = False
            room["stage"] = None
            room["votes"] = {}
            room["assigned_roles"] = {}
            await query.edit_message_text(f"🔄 Игра в комнате '{room_name}' перезапущена.")
    elif data == "menu_back_admin":
        await admin_panel(update, context)