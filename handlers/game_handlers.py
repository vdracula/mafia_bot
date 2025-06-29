# handlers/game_handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from db import rooms
from utils import get_user_name, count_votes, send_private_role

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['pool']
    user_id = update.effective_user.id
    
    async with pool.acquire() as conn:
        # Get room where user is host
        room = await conn.fetchrow(
            '''SELECT r.id, r.name, COUNT(p.id) as player_count 
               FROM rooms r
               JOIN players p ON r.id = p.room_id
               WHERE r.host_id = $1 AND r.started = FALSE
               GROUP BY r.id''',
            user_id
        )
        
        if not room:
            await update.message.reply_text("Вы не являетесь ведущим или игра уже начата.")
            return
            
        if room['player_count'] < MIN_PLAYERS_TO_START:
            await update.message.reply_text(f"Нужно минимум {MIN_PLAYERS_TO_START} игрока.")
            return
            
        # Assign roles
        players = await conn.fetch(
            'SELECT user_id FROM players WHERE room_id = $1',
            room['id']
        )
        
        roles = assign_roles(room['player_count'])
        for player, role in zip(players, roles):
            await conn.execute(
                'UPDATE players SET role = $1 WHERE user_id = $2 AND room_id = $3',
                role, player['user_id'], room['id']
            )
        
        # Update room status
        await conn.execute(
            'UPDATE rooms SET started = TRUE, stage = "night" WHERE id = $1',
            room['id']
        )
        
    await update.message.reply_text("🎮 Игра началась!\n🌙 Ночь. Все закрывают глаза...")

async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("vote_"):
        voted_player_id = int(data.split("_")[1])
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        for room_name, room in rooms.items():
            if chat_id == room["chat_id"] and room["stage"] == "day":
                room["votes"][user_id] = voted_player_id
                voter_name = await get_user_name(context, user_id)
                target_name = await get_user_name(context, voted_player_id)
                await query.edit_message_text(text=f"{voter_name}, вы проголосовали за {target_name}.")
                if len(room["votes"]) == len(room["players"]):
                    result = count_votes(room["votes"])
                    kicked = max(result, key=result.get)
                    kicked_name = await get_user_name(context, kicked)
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Игрок {kicked_name} был изгнан.")
                    room["players"].remove(kicked)
                    room["stage"] = "night"
                    room["votes"] = {}