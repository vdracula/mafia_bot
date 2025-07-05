import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

API_TOKEN = os.getenv("BOT_TOKEN")  # Укажи свой токен через переменную окружения

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Глобальные переменные состояния
players = {}
roles = {}
alive_players = set()
votes = {}
game_started = False

ROLE_LIST = ["Мафия", "Доктор", "Комиссар", "Мирный"]

# Главное меню
def get_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🙋‍♂️ Присоединиться", callback_data="join"),
                InlineKeyboardButton(text="👥 Список игроков", callback_data="status")
            ],
            [
                InlineKeyboardButton(text="🎲 Начать игру", callback_data="startgame"),
                InlineKeyboardButton(text="⚔️ Голосование", callback_data="vote")
            ]
        ]
    )

def back_to_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
        ]
    )

# /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Привет! Это Мафия-бот.\nВыберите действие:",
        reply_markup=get_main_menu()
    )

# /menu
@dp.message(Command("menu"))
async def menu(message: Message):
    await message.answer(
        "📋 Главное меню:",
        reply_markup=get_main_menu()
    )

# /help
@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "ℹ️ Бот для игры в мафию.\n"
        "Используйте кнопки меню или команды:\n"
        "/menu – открыть меню\n"
        "/join – присоединиться\n"
        "/startgame – начать игру\n"
        "/status – список игроков\n"
        "/vote – голосование"
    )

# Кнопка: меню
@dp.callback_query(lambda c: c.data == "menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Главное меню:",
        reply_markup=get_main_menu()
    )

# Кнопка: присоединиться
@dp.callback_query(lambda c: c.data == "join")
async def cb_join(callback: CallbackQuery):
    global game_started
    uid = callback.from_user.id
    uname = callback.from_user.full_name

    if game_started:
        await callback.answer("Игра уже идёт!")
        return

    if uid in players:
        await callback.answer("Вы уже присоединились.")
    else:
        players[uid] = uname
        await callback.message.answer(f"{uname} присоединился. Всего игроков: {len(players)}.")

    await callback.message.edit_text(
        "✅ Вы присоединились.",
        reply_markup=back_to_menu()
    )

# Кнопка: статус
@dp.callback_query(lambda c: c.data == "status")
async def cb_status(callback: CallbackQuery):
    if not players:
        text = "❌ Никто ещё не присоединился."
    else:
        text = "👥 Игроки:\n" + "\n".join(f"- {n}" for n in players.values())

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu()
    )

# Кнопка: начать игру
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
    await callback.message.answer("🎮 Игра началась! Роли рассылаются в личные сообщения.")

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

    await callback.message.edit_text(
        "✅ Роли розданы.",
        reply_markup=back_to_menu()
    )

# Кнопка: голосование
@dp.callback_query(lambda c: c.data == "vote")
async def cb_vote(callback: CallbackQuery):
    if not game_started:
        await callback.message.edit_text(
            "⚠️ Игра ещё не началась.",
            reply_markup=back_to_menu()
        )
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=players[uid],
                    callback_data=f"vote_{uid}"
                )
            ] for uid in alive_players
        ]
    )

    await callback.message.edit_text(
        "⚔️ Голосование: кого казнить?",
        reply_markup=markup
    )

# Обработка голосов
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
            f"☠️ {players[victim]} был казнён.\n"
            f"Он был ролью: {roles[victim]}."
        )
        await bot.send_message(callback.message.chat.id, text)

        mafia_alive = [uid for uid in alive_players if roles[uid] == "Мафия"]
        others_alive = [uid for uid in alive_players if roles[uid] != "Мафия"]
        if not mafia_alive:
            await bot.send_message(callback.message.chat.id, "🎉 Мирные победили!")
            reset_game()
        elif len(mafia_alive) >= len(others_alive):
            await bot.send_message(callback.message.chat.id, "💀 Мафия победила!")
            reset_game()
        else:
            votes.clear()
            await bot.send_message(callback.message.chat.id, "🌙 Наступает ночь (в этой версии ночь вручную).")

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
