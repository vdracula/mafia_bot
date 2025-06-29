from telegram import Update
from telegram.ext import ContextTypes
from utils import get_user_name

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        player = await conn.fetchrow(
            "SELECT role, alive, room_id FROM players WHERE user_id = $1 ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not player:
            await update.callback_query.answer("Вы ещё не присоединились ни к одной комнате.")
            return

        role = player["role"] or "Не назначена"
        alive = "жив" if player["alive"] else "мертв"
        room_id = player["room_id"]
        await update.callback_query.edit_message_text(
            f"🧾 Статус:\n"
            f"Роль: {role}\n"
            f"Состояние: {alive}\n"
            f"Комната: #{room_id}"
        )
