from telegram import Update
from telegram.ext import ContextTypes
from config import MIN_PLAYERS_TO_START
from utils import assign_roles, send_private_role

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['pool']
    user_id = update.effective_user.id

    async with pool.acquire() as conn:
        room = await conn.fetchrow("SELECT * FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if not room:
            await update.message.reply_text("Вы не являетесь ведущим или игра уже началась.")
            return

        players = await conn.fetch("SELECT user_id FROM players WHERE room_id = $1", room["id"])
        if len(players) < MIN_PLAYERS_TO_START:
            await update.message.reply_text(f"Нужно минимум {MIN_PLAYERS_TO_START} игроков.")
            return

        await assign_roles(pool, room["id"])
        await conn.execute("UPDATE rooms SET started = TRUE, stage = 'night' WHERE id = $1", room["id"])

        for p in players:
            role = await conn.fetchval("SELECT role FROM players WHERE user_id = $1 AND room_id = $2", p["user_id"], room["id"])
            await send_private_role(context, p["user_id"], role)

        await update.message.reply_text("🎮 Игра началась! 🌙 Ночь наступила.")