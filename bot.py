import asyncio
import logging
import os
import random
from collections import Counter
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from aiogram.enums import ParseMode

import asyncpg

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

players = {}
roles = {}
alive_players = set()
votes = {}
game_started = False
current_game_id = None

async def create_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def setup_database(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id BIGINT PRIMARY KEY,
                username TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                citizen_wins INTEGER DEFAULT 0
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                winner_side TEXT
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS game_participants (
                game_id INTEGER REFERENCES games(id),
                user_id BIGINT REFERENCES players(id),
                role TEXT,
                survived BOOLEAN
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS role_images (
                role TEXT PRIMARY KEY,
                image BYTEA
            );
        """)

def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("➕ Присоединиться", callback_data="join")],
            [InlineKeyboardButton("🚀 Начать игру", callback_data="startgame")]
        ]
    )

@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в игру Мафия!\nНажмите кнопку, чтобы присоединиться.",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "join")
async def cb_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.full_name
    players[user_id] = username
    await callback.message.answer(f"{username} присоединился!")

@dp.callback_query(lambda c: c.data == "startgame")
async def cb_start(callback: types.CallbackQuery, db_pool):
    global game_started, alive_players, current_game_id
    if game_started:
        await callback.answer("Игра уже началась.")
        return
    if len(players) < 3:
        await callback.message.answer("Нужно минимум 3 игрока.")
        return

    game_started = True
    alive_players = set(players.keys())
    votes.clear()

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO games(start_time) VALUES($1) RETURNING id;
        """, datetime.utcnow())
        current_game_id = row["id"]

        for uid, username in players.items():
            await conn.execute("""
                INSERT INTO players(id, username)
                VALUES($1, $2)
                ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username;
            """, uid, username)

    ids = list(players.keys())
    mafia = random.sample(ids, k=2 if len(ids) >= 5 else 1)
    for uid in ids:
        role = "Мафия" if uid in mafia else "Мирный"
        roles[uid] = role
        await send_role(uid, role, db_pool)

async def send_role(user_id, role, db_pool):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT image FROM role_images WHERE role=$1;
        """, role)
        if row and row["image"]:
            await bot.send_photo(
                user_id,
                types.BufferedInputFile(row["image"], filename=f"{role}.jpg"),
                caption=f"Ваша роль: {role}"
            )
        else:
            await bot.send_message(user_id, f"Ваша роль: {role}")

@dp.message(commands=["vote"])
async def cmd_vote(message: types.Message):
    if not game_started:
        await message.answer("Игра ещё не началась.")
        return
    for uid in alive_players:
        kb = InlineKeyboardMarkup(row_width=1)
        for target in alive_players:
            if uid == target:
                continue
            kb.add(InlineKeyboardButton(players[target], callback_data=f"vote_{target}"))
        await bot.send_message(uid, "Голосуйте:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def cb_vote(callback: types.CallbackQuery, db_pool):
    voter = callback.from_user.id
    target = int(callback.data.split("_")[1])
    votes[voter] = target
    await callback.answer("Голос принят.")

    if len(votes) == len(alive_players):
        tally = Counter(votes.values())
        eliminated, _ = tally.most_common(1)[0]
        alive_players.remove(eliminated)

        if roles[eliminated] == "Мафия":
            winner = "Мирные"
        elif all(roles[uid] == "Мафия" for uid in alive_players):
            winner = "Мафия"
        else:
            winner = None

        if winner:
            await finalize_game(db_pool, winner)
        else:
            votes.clear()
            await bot.send_message(callback.message.chat.id, f"{players[eliminated]} выбыл!")

async def finalize_game(db_pool, winner_side):
    global game_started, players, roles, alive_players, votes, current_game_id
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE games SET end_time=$1, winner_side=$2 WHERE id=$3;
        """, datetime.utcnow(), winner_side, current_game_id)
        for uid in players:
            survived = uid in alive_players
            await conn.execute("""
                INSERT INTO game_participants(game_id, user_id, role, survived)
                VALUES($1, $2, $3, $4);
            """, current_game_id, uid, roles[uid], survived)

            # Обновляем статистику
            await conn.execute("""
                UPDATE players
                SET games_played = games_played + 1,
                    games_won = games_won + CASE WHEN
                        ($1='Мафия' AND role='Мафия') OR
                        ($1='Мирные' AND role='Мирный')
                    THEN 1 ELSE 0 END,
                    mafia_wins = mafia_wins + CASE WHEN ($1='Мафия' AND role='Мафия') THEN 1 ELSE 0 END,
                    citizen_wins = citizen_wins + CASE WHEN ($1='Мирные' AND role='Мирный') THEN 1 ELSE 0 END
                WHERE id=$2;
            """, winner_side, uid)

    await bot.send_message(
        list(players.keys())[0],
        f"🎉 Игра окончена! Победили: {winner_side}"
    )
    game_started = False
    players.clear()
    roles.clear()
    alive_players.clear()
    votes.clear()
    current_game_id = None

@dp.message(commands=["stats"])
async def cmd_stats(message: types.Message, db_pool):
    uid = message.from_user.id
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT games_played, games_won, mafia_wins, citizen_wins FROM players WHERE id=$1;
        """, uid)
        if row:
            text = (
                f"Ваши игры:\n"
                f"Всего игр: {row['games_played']}\n"
                f"Побед: {row['games_won']}\n"
                f"Побед за Мафию: {row['mafia_wins']}\n"
                f"Побед за Мирных: {row['citizen_wins']}"
            )
        else:
            text = "Вы ещё не играли."
        await message.answer(text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    async def main():
        db_pool = await create_db_pool()
        await setup_database(db_pool)
        dp.workflow_data["db_pool"] = db_pool
        await dp.start_polling(bot)
    asyncio.run(main())
