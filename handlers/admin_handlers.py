from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOUR_ADMIN_ID
from datetime import datetime

def is_admin(user_id: int) -> bool:
    return user_id == YOUR_ADMIN_ID

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return
    await update.message.reply_text("⛔ Бот завершает работу...")
    await context.application.stop()

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return
    pool = context.bot_data['pool']
    async with pool.acquire() as conn:
        room_count = await conn.fetchval("SELECT COUNT(*) FROM rooms")
        player_count = await conn.fetchval("SELECT COUNT(*) FROM players")
        game_count = await conn.fetchval("SELECT COUNT(*) FROM game_stats")
    await update.message.reply_text(
        f"📊 Статистика:\nКомнат: {room_count}\nИгроков: {player_count}\nИгр: {game_count}"
    )

async def clean_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return
    pool = context.bot_data['pool']
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM rooms WHERE started = FALSE AND created_at < NOW() - INTERVAL '1 day'"
        )
    await update.message.reply_text("🧹 Старые комнаты удалены.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return
    if not context.args:
        await update.message.reply_text("Введите сообщение для рассылки.")
        return
    message = " ".join(context.args)

    pool = context.bot_data['pool']
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT DISTINCT user_id FROM players")
        count = 0
        for row in users:
            try:
                await context.bot.send_message(chat_id=row["user_id"], text=message)
                count += 1
            except:
                continue
    await update.message.reply_text(f"📢 Отправлено {count} сообщений.")

async def show_end_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id FROM rooms WHERE host_id = $1 AND started = TRUE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await update.message.reply_text("Нет активной игры.")
            return

    keyboard = [
        [InlineKeyboardButton("🏴 Победила Мафия", callback_data="game_end_mafia")],
        [InlineKeyboardButton("🕊 Победили Мирные", callback_data="game_end_town")]
    ]
    await update.message.reply_text("Кто победил?", reply_markup=InlineKeyboardMarkup(keyboard))

async def record_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    result = query.data.split("_")[-1]
    winner = "Мафия" if result == "mafia" else "Мирные"

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id, created_at FROM rooms WHERE host_id = $1 AND started = TRUE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await query.edit_message_text("Нет активной игры.")
            return

        room_id = room["id"]
        created_at = room["created_at"]
        total_players = await conn.fetchval(
            "SELECT COUNT(*) FROM players WHERE room_id = $1", room_id
        )
        duration = datetime.utcnow() - created_at

        await conn.execute(
            "INSERT INTO game_stats (room_id, winner, total_players, duration) VALUES ($1, $2, $3, $4)",
            room_id, winner, total_players, duration
        )
        await query.edit_message_text(f"✅ Победили {winner}.")
