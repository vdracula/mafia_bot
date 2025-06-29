# game_handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import MIN_PLAYERS_TO_START
from utils import assign_roles, send_private_role, get_user_name

# Запуск игры
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await update.message.reply_text("Комната не найдена или уже началась.")
            return

        room_id = room["id"]
        players = await conn.fetch("SELECT user_id FROM players WHERE room_id = $1", room_id)

        if len(players) < MIN_PLAYERS_TO_START:
            await update.message.reply_text(f"Для начала нужно минимум {MIN_PLAYERS_TO_START} игроков.")
            return

        await assign_roles(pool, room_id)
        await conn.execute("UPDATE rooms SET started = TRUE, stage = 'day' WHERE id = $1", room_id)

        for player in players:
            role = await conn.fetchval(
                "SELECT role FROM players WHERE user_id = $1 AND room_id = $2",
                player["user_id"], room_id
            )
            await send_private_role(context, player["user_id"], role)

        await update.message.reply_text("🎮 Игра началась! Роли разосланы игрокам.")

# Проверка своей роли
async def check_status_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        player = await conn.fetchrow(
            "SELECT role, alive FROM players WHERE user_id = $1 ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not player:
            await query.edit_message_text("Вы пока не участвуете в игре.")
            return

        status = "жив" if player["alive"] else "мертв"
        await query.edit_message_text(
            f"Ваша роль: {player['role']}\nСтатус: {status}"
        )

# Начало голосования
async def start_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id FROM rooms WHERE host_id = $1 AND started = TRUE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await update.message.reply_text("Вы не ведёте активную игру.")
            return

        room_id = room["id"]
        players = await conn.fetch(
            "SELECT user_id FROM players WHERE room_id = $1 AND alive = TRUE", room_id
        )

        buttons = [
            [InlineKeyboardButton(
                f"Проголосовать за {await get_user_name(context, p['user_id'])}",
                callback_data=f'vote_{room_id}_{p["user_id"]}'
            )]
            for p in players if p["user_id"] != user_id
        ]
        buttons.append([InlineKeyboardButton("🛑 Завершить голосование", callback_data=f'end_vote_{room_id}')])

        await update.message.reply_text(
            "Голосование началось. Выберите игрока:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# Обработка голоса
async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, room_id, target_id = query.data.split("_")
    voter_id = query.from_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO votes (room_id, voter_id, target_id) VALUES ($1, $2, $3) "
            "ON CONFLICT (room_id, voter_id) DO UPDATE SET target_id = EXCLUDED.target_id",
            int(room_id), voter_id, int(target_id)
        )
        await query.edit_message_text("Ваш голос учтён.")

# Завершение голосования
async def end_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, room_id = query.data.partition("_end_vote_")
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        results = await conn.fetch(
            "SELECT target_id, COUNT(*) as votes FROM votes WHERE room_id = $1 GROUP BY target_id ORDER BY votes DESC",
            int(room_id)
        )

        if not results:
            await query.edit_message_text("Голосов не было.")
            return

        top_vote = results[0]
        await conn.execute(
            "UPDATE players SET alive = FALSE WHERE user_id = $1 AND room_id = $2",
            top_vote["target_id"], int(room_id)
        )
        await conn.execute("DELETE FROM votes WHERE room_id = $1", int(room_id))
        await query.edit_message_text(f"Игрок {top_vote['target_id']} исключён из игры.")
