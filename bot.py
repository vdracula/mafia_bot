import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)

from db import Database

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

lobbies = {}
ongoing_games = {}

def get_lobby_menu(is_host=False):
    buttons = [
        [InlineKeyboardButton(text="🙋 Присоединиться", callback_data="join_lobby")]
    ]
    if is_host:
        buttons.append([InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_lobby")])
        buttons.append([InlineKeyboardButton(text="🛑 Завершить игру", callback_data="end_game")])
        buttons.append([InlineKeyboardButton(text="🗳 Начать голосование", callback_data="start_vote")])
        buttons.append([InlineKeyboardButton(text="📊 Вся статистика", callback_data="all_stats")])
    buttons.append([InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start(message: Message):
    buttons = [
        [InlineKeyboardButton(text="🎮 Создать игру", callback_data="create_lobby")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👋 Привет! Что хотите сделать?", reply_markup=markup)

@dp.callback_query(lambda c: c.data == "create_lobby")
async def create_lobby(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    lobbies[chat_id] = {
        "host_id": user_id,
        "players": {}
    }
    await callback.message.answer(
        f"🎮 Игра создана ведущим {callback.from_user.full_name}. Игроки могут присоединяться.",
        reply_markup=get_lobby_menu(is_host=True)
    )

@dp.callback_query(lambda c: c.data == "join_lobby")
async def join_lobby(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    if chat_id not in lobbies:
        await callback.message.answer("Нет активной лобби. Сначала создайте игру.")
        return
    lobbies[chat_id]["players"][user_id] = callback.from_user.full_name
    await db.add_player(user_id, callback.from_user.full_name)
    await callback.message.answer(f"{callback.from_user.full_name} присоединился к игре.")

@dp.callback_query(lambda c: c.data == "start_lobby")
async def start_lobby(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    lobby = lobbies.get(chat_id)
    if not lobby or lobby["host_id"] != user_id:
        await callback.message.answer("❌ Только ведущий может начать игру.")
        return

    players = list(lobby["players"].keys())
    if len(players) < 2:
        await callback.message.answer("Недостаточно игроков (минимум 2).")
        return

    chat_title = callback.message.chat.title or "Без названия"
    game_id = await db.create_game(chat_id, chat_title)

    mafia_count = 2 if len(players) >= 5 else 1
    mafia_ids = random.sample(players, mafia_count)

    alive = {}
    for uid in players:
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
        "host_id": user_id,
        "alive_players": alive,
        "votes": {}
    }
    lobbies.pop(chat_id)
    await callback.message.answer("🎲 Игра началась!", reply_markup=get_lobby_menu(is_host=True))

@dp.callback_query(lambda c: c.data == "start_vote")
async def start_vote(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    game = ongoing_games.get(chat_id)
    if not game or game["host_id"] != user_id:
        await callback.message.answer("❌ Только ведущий может начать голосование.")
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=uid, callback_data=f"vote_{uid}")]
            for uid in game["alive_players"]
        ]
    )
    await callback.message.answer("🗳 Голосование началось! Выберите, кого казнить:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    game = ongoing_games.get(chat_id)
    if not game:
        await callback.answer("Нет активной игры.")
        return

    voter = callback.from_user.id
    target = int(callback.data.split("_")[1])
    if voter not in game["alive_players"]:
        await callback.answer("Вы не участвуете в игре.")
        return

    game["votes"][voter] = target
    await callback.answer("Ваш голос учтён.")

    if len(game["votes"]) == len(game["alive_players"]):
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

@dp.callback_query(lambda c: c.data == "end_game")
async def end_game(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    game = ongoing_games.get(chat_id)
    if not game or game["host_id"] != user_id:
        await callback.message.answer("❌ Только ведущий может завершить игру.")
        return

    await db.finalize_game(game["game_id"], winner="Прервано")
    ongoing_games.pop(chat_id)
    await callback.message.answer("🛑 Игра завершена ведущим.")

@dp.callback_query(lambda c: c.data == "my_stats")
async def my_stats(callback: CallbackQuery, db: Database):
    row = await db.get_player_stats(callback.from_user.id)
    if row:
        text = (
            f"👤 Ваша статистика:\n"
            f"Игры: {row['games_played']}\n"
            f"Победы: {row['games_won']}\n"
            f"Победы за мафию: {row['mafia_wins']}\n"
            f"Победы за мирных: {row['citizen_wins']}"
        )
    else:
        text = "Нет статистики."
    await callback.message.answer(text)

@dp.callback_query(lambda c: c.data == "all_stats")
async def all_stats(callback: CallbackQuery, db: Database):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    game = ongoing_games.get(chat_id)
    if not game or game["host_id"] != user_id:
        await callback.message.answer("❌ Только ведущий может смотреть общую статистику.")
        return

    rows = await db.get_all_player_stats()
    if not rows:
        await callback.message.answer("Нет статистики.")
        return

    text = "📊 Статистика игроков:\n\n"
    for r in rows:
        text += (
            f"— {r['username']}\n"
            f"  Игры: {r['games_played']}, Победы: {r['games_won']}, "
            f"Мафия: {r['mafia_wins']}, Мирные: {r['citizen_wins']}\n\n"
        )
    await callback.message.answer(text)

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
