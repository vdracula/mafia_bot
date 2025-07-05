import asyncio
import random
import logging
from collections import Counter
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode
import os

# Читаем токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

ROLE_IMAGES = {
    "Мафия": [
        "images/mafia1.jpg",
        "images/mafia2.jpg",
        "images/mafia3.jpg"
    ],
    "Доктор": "images/doctor.jpg",
    "Комиссар": "images/commissar.jpg",
    "Мирный": [
        "images/citizen1.jpg",
        "images/citizen2.jpg"
    ]
}

players = {}        # user_id -> username
roles = {}          # user_id -> роль
alive_players = set()
votes = {}
game_started = False

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Присоединиться", callback_data="join")],
        [InlineKeyboardButton(text="🚀 Начать игру", callback_data="startgame")]
    ])

def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu")]
    ])

@dp.message(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "👋 <b>Добро пожаловать в игру Мафия!</b>\n"
        "Нажмите кнопку, чтобы присоединиться или начать игру.",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "join")
async def cb_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.full_name
    if user_id not in players:
        players[user_id] = username
        await callback.answer("✅ Вы присоединились.")
    else:
        await callback.answer("Вы уже в игре.")
    await callback.message.edit_text(
        "👥 Игроки:\n" + "\n".join(players.values()),
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "startgame")
async def cb_startgame(callback: CallbackQuery):
    global game_started, alive_players
    if game_started:
        await callback.answer("Игра уже идёт.")
        return
    if len(players) < 3:
        await callback.message.edit_text(
            "❗ Нужно минимум 3 игрока.",
            reply_markup=back_to_menu()
        )
        return

    game_started = True
    alive_players = set(players.keys())
    await callback.message.answer("🎮 Игра началась! Роли рассылаются...")

    ids = list(players.keys())
    random.shuffle(ids)

    mafia_count = 2 if len(ids) >= 5 else 1
    mafia_ids = [ids.pop() for _ in range(mafia_count)]
    for uid in mafia_ids:
        roles[uid] = "Мафия"

    doctor = ids.pop() if ids else None
    if doctor:
        roles[doctor] = "Доктор"

    commissar = ids.pop() if ids else None
    if commissar:
        roles[commissar] = "Комиссар"

    for uid in ids:
        roles[uid] = "Мирный"

    for uid, role in roles.items():
        img_data = ROLE_IMAGES[role]
        img_path = random.choice(img_data) if isinstance(img_data, list) else img_data
        with open(img_path, "rb") as photo:
            await bot.send_photo(uid, photo=photo, caption=f"Ваша роль: {role}")

    await callback.message.edit_text(
        "✅ Роли розданы.\n\nЧтобы начать голосование, напишите команду:\n/vote",
        reply_markup=back_to_menu()
    )

@dp.message(commands=["vote"])
async def vote(message: types.Message):
    if not game_started:
        await message.answer("Игра ещё не началась.")
        return
    for uid in alive_players:
        kb = InlineKeyboardMarkup(row_width=1)
        for tid in alive_players:
            if uid == tid:
                continue
            kb.add(InlineKeyboardButton(
                text=players[tid],
                callback_data=f"vote_{tid}"
            ))
        await bot.send_message(uid, "🔘 За кого голосуете?", reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("vote_"))
async def cb_vote(callback: CallbackQuery):
    voter = callback.from_user.id
    if voter not in alive_players:
        await callback.answer("Вы не можете голосовать.")
        return
    target = int(callback.data.split("_")[1])
    if target not in alive_players:
        await callback.answer("Этот игрок уже выбыл.")
        return
    votes[voter] = target
    await callback.answer("Голос принят.")

    if len(votes) == len(alive_players):
        await tally_votes(callback.message.chat.id)

async def tally_votes(chat_id):
    global votes
    tally = Counter(votes.values())
    text = "📊 <b>Результаты голосования:</b>\n"
    for uid, count in tally.items():
        text += f"{players[uid]} — {count} голос(ов)\n"
    if tally:
        eliminated, _ = tally.most_common(1)[0]
        alive_players.discard(eliminated)
        text += f"\n☠️ {players[eliminated]} выбыл из игры."
    else:
        text += "\nНикто не выбыл."
    votes.clear()
    await bot.send_message(chat_id, text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
