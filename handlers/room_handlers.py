from telegram import Update
from telegram.ext import ContextTypes
import time
from db import create_pool

async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['pool']
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    name = f"room_{user_id}_{int(time.time())}"

    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if exists:
            await update.message.reply_text("У вас уже есть активная комната.")
            return

        await conn.execute("INSERT INTO rooms (name, host_id, chat_id) VALUES ($1, $2, $3)", name, user_id, chat_id)
        room_id = await conn.fetchval("SELECT id FROM rooms WHERE name = $1", name)
        await conn.execute("INSERT INTO players (user_id, room_id) VALUES ($1, $2)", user_id, room_id)

    await update.message.reply_text(f"✅ Комната '{name}' создана!")