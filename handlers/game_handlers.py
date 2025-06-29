# handlers/game_handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from db import rooms
from utils import get_user_name, count_votes, send_private_role

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    for room_name, room in rooms.items():
        if not rooms:
            await query.edit_message_text("Нет активных комнат.")
            return
        if user_id == room["host"] and not room["started"]:
            if len(room["players"]) < 4:
                await update.message.reply_text("Нужно минимум 4 игрока.")
                return
            assign_roles(room)
            room["started"] = True
            room["stage"] = "night"
            room["votes"] = {}
            for player_id in room["players"]:
                role = room["assigned_roles"][player_id]
                await send_private_role(context, player_id, role)
            await update.message.reply_text("🎮 Игра началась!\n🌙 Ночь. Все закрывают глаза...")
            return
    await update.message.reply_text("Вы не являетесь ведущим или игра уже начата.")

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