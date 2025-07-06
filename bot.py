import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)

from db import Database  # предполагается, что у тебя есть db.py с классом Database

# Задаём токен и DSN из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

# Создаём бота с поддержкой HTML
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=types.ParseMode.HTML)
)
dp = Dispatcher()

# Словарь для хранения состояния активных игр
# Формат: {chat_id: {"game_id": int, "alive_players": {user_id: role}, "votes": {voter_id: voted_id}}}
ongoing_games = {}

def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🙋 Присоединиться", callback_data="join")],
            [InlineKeyboardButton("🎲 Начать игру", callback_data="startgame")],
        ]
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать! Нажмите кнопку ниже.",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "join")
async def join(callback: types.CallbackQuery, db: Database):
    await db.add_player(callback.from_user.id, callback.from_user.full_name)
    await callback.message.answer(f"{callback.from_user.full_name} зарегистрирован.")

@dp.callback_query(lambda c: c.data == "startgame")
async def startgame(callback: types.CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    game_id = await db.create_game(chat_id)

    # Для примера: приглашаем всех админов чата
    members = await bot.get_chat_administrators(chat_id)
    ids = [m.user.id for m in members if not m.user.is_bot]

    if not ids:
        await callback.message.answer("Нет игроков.")
        return

    mafia_count = 2 if len(ids) >= 5 else 1
    mafia_ids = random.sample(ids, mafia_count)

    alive = {}
    for uid in ids:
        role = "Мафия" if uid in mafia_ids else "Мирный"
        await db.add_participant(game_id, uid, role)
        image = await db.get_role_image(role)
        caption = f"Ваша роль: {role}"
        if image:
            await bot.send_photo(
                uid,
                BufferedInputFile(image, filename="role.jpg"),
                caption=caption
            )
        else:
            await bot.send_message(uid, caption)
        alive[uid] = role

    ongoing_games[chat_id] = {
        "game_id": game_id,
        "alive_players": alive,
        "votes": {}
    }

    await callback.message.answer("Игра началась!")

@dp.message(Command("vote"))
async def vote(message: types.Message):
    chat_id = message.chat.id
    game = ongoing_games.get(chat_id)
    if not game:
        await message.answer("Нет активной игры.")
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(str(uid), callback_data=f"vote_{uid}")]
            for uid in game["alive_players"]
        ]
    )

    await message.answer("Выберите, кого казнить:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    game = ongoing_games.get(chat_id)
    if not game:
        await callback.answer("Нет активной игры.")
        return

    voter = callback.from_user.id
    target = int(callback.data.split("_")[1])

    game["votes"][voter] = target
    await callback.answer("Ваш голос учтён.")

    if len(game["votes"]) == len(game["alive_players"]):
        # Подсчёт голосов
        tally = {}
        for t in game["votes"].values():
            tally[t] = tally.get(t, 0) + 1

        eliminated = max(tally, key=tally.get)
        await db.mark_dead(game["game_id"], eliminated)

        role = game["alive_players"].pop(eliminated)
        await bot.send_message(chat_id, f"{eliminated} выбыл. Его роль: {role}")

        mafia_left = [r for r in game["alive_players"].values() if r == "Мафия"]
        citizens_left = [r for r in game["alive_players"].values() if r != "Мафия"]

        winner = None
        if not mafia_left:
            winner = "Мирные"
        elif len(mafia_left) >= len(citizens_left):
            winner = "Мафия"

        if winner:
            await db.finalize_game(game["game_id"], winner)
            await bot.send_message(chat_id, f"🎉 Победили {winner}!")
            ongoing_games.pop(chat_id)
        else:
            game["votes"] = {}
            await bot.send_message(chat_id, "Следующий раунд голосования.")

@dp.message(Command("stats"))
async def stats(message: types.Message, db: Database):
    row = await db.get_player_stats(message.from_user.id)
    if row:
        text = (
            f"Игры сыграно: {row['games_played']}\n"
            f"Побед: {row['games_won']}\n"
            f"Побед за мафию: {row['mafia_wins']}\n"
            f"Побед за мирных: {row['citizen_wins']}"
        )
    else:
        text = "Нет данных о статистике."
    await message.answer(text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        db = Database(DB_URL)
        await db.connect()
        dp.workflow_data["db"] = db
        await dp.start_polling(bot)

    asyncio.run(main())
