import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import asyncio

API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Игровые данные
players = {}          # user_id -> username
roles = {}            # user_id -> роль
alive_players = set()
votes = {}
game_started = False

ROLE_LIST = ["Мафия", "Доктор", "Комиссар", "Мирный"]

# /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Это Мафия-бот на aiogram v3.\n"
        "Команды:\n"
        "/join - присоединиться\n"
        "/startgame - начать игру\n"
        "/status - список игроков\n"
        "/vote - голосование"
    )

# /join
@dp.message(Command("join"))
async def join(message: Message):
    global game_started
    if game_started:
        await message.answer("Игра уже идёт!")
        return
    uid = message.from_user.id
    uname = message.from_user.full_name
    if uid in players:
        await message.answer("Вы уже в игре.")
    else:
        players[uid] = uname
        await message.answer(f"{uname} присоединился. Всего игроков: {len(players)}.")

# /status
@dp.message(Command("status"))
async def status(message: Message):
    if not players:
        await message.answer("Никто не присоединился.")
        return
    text = "Игроки:\n" + "\n".join(f"- {n}" for n in players.values())
    await message.answer(text)

# /startgame
@dp.message(Command("startgame"))
async def startgame(message: Message):
    global game_started, alive_players
    if game_started:
        await message.answer("Игра уже идёт.")
        return
    if len(players) < 3:
        await message.answer("Нужно минимум 3 игрока.")
        return

    game_started = True
    alive_players = set(players.keys())
    await message.answer("Игра началась. Роли рассылаются в личные сообщения.")

    ids = list(players.keys())
    random.shuffle(ids)

    mafia = ids.pop()
    roles[mafia] = "Мафия"
    await bot.send_message(mafia, "Вы МАФИЯ.")

    if ids:
        doctor = ids.pop()
        roles[doctor] = "Доктор"
        await bot.send_message(doctor, "Вы ДОКТОР.")

    if ids:
        commissar = ids.pop()
        roles[commissar] = "Комиссар"
        await bot.send_message(commissar, "Вы КОМИССАР.")

    for uid in ids:
        roles[uid] = "Мирный"
        await bot.send_message(uid, "Вы МИРНЫЙ житель.")

    await message.answer("Роли розданы. Начинаем игру.")

# /vote
@dp.message(Command("vote"))
async def vote(message: Message):
    if not game_started:
        await message.answer("Игра ещё не началась.")
        return

    markup = InlineKeyboardMarkup()
    for uid in alive_players:
        markup.add(
            InlineKeyboardButton(players[uid], callback_data=f"vote_{uid}")
        )
    await message.answer("Голосование. Кого казнить?", reply_markup=markup)

# Обработка голосования
@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery):
    voter = callback.from_user.id
    target = int(callback.data.split("_")[1])

    if voter not in alive_players:
        await callback.answer("Вы мертвы.")
        return

    votes[voter] = target
    await callback.answer(f"Голос за {players[target]}.")

    if len(votes) == len(alive_players):
        tally = {}
        for t in votes.values():
            tally[t] = tally.get(t, 0) + 1
        victim = max(tally, key=tally.get)
        alive_players.remove(victim)

        text = (
            f"{players[victim]} был казнён.\n"
            f"Он был ролью: {roles[victim]}."
        )
        await bot.send_message(callback.message.chat.id, text)

        # Проверим победу
        mafia_alive = [uid for uid in alive_players if roles[uid] == "Мафия"]
        others_alive = [uid for uid in alive_players if roles[uid] != "Мафия"]
        if not mafia_alive:
            await bot.send_message(callback.message.chat.id, "Мирные победили!")
            reset_game()
        elif len(mafia_alive) >= len(others_alive):
            await bot.send_message(callback.message.chat.id, "Мафия победила!")
            reset_game()
        else:
            votes.clear()
            await bot.send_message(callback.message.chat.id, "Следующая ночь (в этой версии ночь вручную не реализована).")

def reset_game():
    global game_started, players, roles, alive_players, votes
    game_started = False
    players = {}
    roles = {}
    alive_players = set()
    votes = {}

# Запуск
if __name__ == "__main__":
    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())
