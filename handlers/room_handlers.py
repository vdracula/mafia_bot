from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# === Создание комнаты ===
async def create_room_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    username = user.username or f"user{user.id}"
    pool = context.bot_data['pool']

    room_name = f"Комната_{username}"
    async with pool.acquire() as conn:
        try:
            room = await conn.fetchrow(
                "INSERT INTO rooms (name, host_id, chat_id) VALUES ($1, $2, $3) RETURNING id",
                room_name, user_id, query.message.chat.id
            )
            await conn.execute(
                "INSERT INTO players (user_id, room_id) VALUES ($1, $2)",
                user_id, room["id"]
            )
            await query.edit_message_text(f"✅ Комната создана: {room_name}\nВы присоединились.")
        except Exception:
            await query.edit_message_text("❌ Ошибка при создании комнаты (возможно, уже есть).")

# === Список комнат ===
async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pool = context.bot_data['pool']
    async with pool.acquire() as conn:
        rooms = await conn.fetch(
            "SELECT id, name FROM rooms WHERE started = FALSE ORDER BY created_at DESC LIMIT 5"
        )

    if not rooms:
        await query.edit_message_text("ℹ️ Нет доступных комнат.")
        return

    keyboard = [
        [InlineKeyboardButton(room["name"], callback_data=f"join_room_{room['id']}")]
        for room in rooms
    ]
    await query.edit_message_text(
        "Выберите комнату:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === Присоединение к комнате ===
async def join_room_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # join_room_5
    room_id = int(data.split("_")[-1])
    user_id = query.from_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO players (user_id, room_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                user_id, room_id
            )
            await query.edit_message_text(f"✅ Вы присоединились к комнате #{room_id}.")
        except Exception:
            await query.edit_message_text("❌ Не удалось присоединиться.")
