import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile, CallbackQuery
)

from db import Database

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# В памяти только активные игры
ongoing_games = {}

def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🙋 Присоединиться",
                    callback_data="join"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎲 Начать игру",
                    callback_data="startgame"
                )
            ]
        ]
    )

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Добро пожаловать! Нажмите кнопку ниже.",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "join")
async def join(callback: CallbackQuery, db: Database):
    await db.add_player(callback.from_user.id, callback.from_user.full_name)
    await callback.message.answer(f"{callback.from_user.full_name} зарегистрирован.")

@dp.callback_query(lambda c: c.data == "startgame")
async def startgame(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    game_id = await db.create_game(chat_id)

    # Получаем админов (для примера)
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
async def vote(message: Message):
    chat_id = message.chat.id
    game = ongoing_games.get(chat_id)
    if not game:
        await message.answer("Нет активной игры.")
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"👤 {uid}",
                    callback_data=f"vote_{uid}"
                )
            ]
            for uid in game["alive_players"]
        ]
    )
    await message.answer("Выберите, кого казнить:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, db: Database):
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
        tally = {}
        for t in game["votes"].values():
            tally[t] = tally.get(t, 0) + 1

        eliminated = max(tally, key=tally.get)
        await db.mark_dead(game["game_id"], eliminated)
        role = game["alive_players"].pop(eliminated)

        await bot.send_message(chat_id, f"👤 {eliminated} выбыл. Его роль: {role}")

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
async def stats(message: Message, db: Database):
    row = await db.get_player_stats(message.from_user.id)
    if row:
        text = (
            f"👤 Статистика:\n"
            f"• Игры сыграно: {row['games_played']}\n"
            f"• Побед: {row['games_won']}\n"
            f"• Побед за мафию: {row['mafia_wins']}\n"
            f"• Побед за мирных: {row['citizen_wins']}"
        )
    else:
        text = "Нет данных о статистике."
    await message.answer(text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        db = Database(DB_URL)
        if not DB_URL:
            raise ValueError("DATABASE_URL не установлен!")
        await db.connect()
        dp.workflow_data["db"] = db
        await dp.start_polling(bot)

    asyncio.run(main())
