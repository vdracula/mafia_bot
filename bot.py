import asyncio, logging, os, random
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
from aiogram.exceptions import TelegramMigrateToChat
from db import Database
from middlewares import DBMiddleware

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

lobbies = {}
ongoing_games = {}

def get_lobby_menu(is_host=False):
    buttons = [[InlineKeyboardButton(text="🙋 Присоединиться", callback_data="join_lobby")]]
    if is_host:
        buttons += [
            [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_lobby")],
            [InlineKeyboardButton(text="🛑 Завершить игру", callback_data="end_game")],
            [InlineKeyboardButton(text="👤 Выбрать кандидатов", callback_data="select_vote_candidates")],
            [InlineKeyboardButton(text="🗳 Начать голосование", callback_data="start_vote")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    buttons = [
        [InlineKeyboardButton(text="🎮 Создать игру", callback_data="create_lobby")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📊 Статистика игр", callback_data="all_stats")]
    ]
    await message.answer("👋 Привет! Что хотите сделать?",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda c: c.data == "create_lobby")
async def create_lobby(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await callback.message.answer("❌ Игру можно создавать только в группе.")
        return


    cid = callback.message.chat.id
    uid = callback.from_user.id
    name = callback.from_user.full_name

    lobbies[cid] = {"host_id": uid, "players": {uid: name}}
    await callback.message.answer(
        f"🎮 Игра создана ведущим {name}. Игроки могут присоединяться.",
        reply_markup=get_lobby_menu(is_host=True)
    )

@dp.callback_query(lambda c: c.data == "join_lobby")
async def join_lobby(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    name = callback.from_user.full_name

    if cid not in lobbies:
        await callback.message.answer("Нет активной лобби.")
        return

    lobbies[cid]["players"][uid] = name
    await db.add_player(uid, name)
    await callback.message.answer(f"{name} присоединился к игре.")

@dp.callback_query(lambda c: c.data == "start_lobby")
async def start_lobby(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    lobby = lobbies.get(cid)

    if not lobby or lobby["host_id"] != uid:
        await callback.message.answer("❌ Только ведущий может начать игру.")
        return

    players = lobby["players"]
    if len(players) < 4:
        await callback.message.answer("Нужно минимум 4 игрока.")
        return

    try:
        gid = await db.create_game(cid, callback.message.chat.title)

        player_ids = list(players)
        random.shuffle(player_ids)

        mafia_count = 2 if len(players) >= 6 else 1
        mafia_ids = set(player_ids[:mafia_count])
        remaining = [pid for pid in player_ids if pid not in mafia_ids]
        commissioner_id = remaining[0] if len(remaining) >= 1 else None
        doctor_id = remaining[1] if len(remaining) >= 2 else None

        alive = {}

        for pid in player_ids:
            if pid in mafia_ids:
                role = "Мафия"
            elif pid == commissioner_id:
                role = "Комиссар"
            elif pid == doctor_id:
                role = "Доктор"
            else:
                role = "Мирный"

            await db.add_participant(gid, pid, role)

            image = await db.get_role_image(role)
            if image:
                await bot.send_photo(
                    pid,
                    BufferedInputFile(image, filename="role.jpg"),
                    caption=f"🕵 Ваша роль: <b>{role}</b>"
                )
            else:
                await bot.send_message(pid, f"🕵 Ваша роль: <b>{role}</b>")

            alive[pid] = role

        ongoing_games[cid] = {
            "game_id": gid,
            "host_id": uid,
            "host_name": callback.from_user.full_name,
            "alive_players": alive,
            "player_names": players,
            "votes": {},
            "vote_candidates": []
        }

        lobbies.pop(cid, None)
        await callback.message.answer("🎲 Игра началась!", reply_markup=get_lobby_menu(is_host=True))

    except TelegramMigrateToChat as e:
        new_cid = e.migrate_to_chat_id
        lobbies[new_cid] = lobbies.pop(cid)
        await callback.message.answer("🔁 Группа была обновлена до супергруппы. Повторите команду.")

@dp.callback_query(lambda c: c.data == "select_vote_candidates")
async def select_vote_candidates(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    game = ongoing_games.get(cid)

    if not game or game["host_id"] != uid:
        await callback.message.answer("❌ Только ведущий может выбрать кандидатов.")
        return

    keyboard = []
    for pid in game["alive_players"]:
        name = game["player_names"].get(pid, str(pid))
        keyboard.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"toggle_candidate_{pid}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🗳 Начать голосование", callback_data="start_vote")
    ])

    await callback.message.answer("Выберите кандидатов для голосования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data.startswith("toggle_candidate_"))
async def toggle_candidate(callback: CallbackQuery):
    cid = callback.message.chat.id
    game = ongoing_games.get(cid)
    if not game:
        await callback.answer("Нет активной игры.")
        return

    pid = int(callback.data.split("_")[2])
    if "vote_candidates" not in game:
        game["vote_candidates"] = []

    if pid in game["vote_candidates"]:
        game["vote_candidates"].remove(pid)
        await callback.answer("Убран из кандидатов.")
    else:
        game["vote_candidates"].append(pid)
        await callback.answer("Добавлен в кандидаты.")

@dp.callback_query(lambda c: c.data == "start_vote")
async def start_vote(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    game = ongoing_games.get(cid)

    if not game or game["host_id"] != uid:
        await callback.message.answer("❌ Только ведущий может начать голосование.")
        return

    candidates = game.get("vote_candidates", [])
    if not candidates:
        await callback.message.answer("⚠️ Сначала выберите кандидатов.")
        return

    keyboard = []
    for pid in candidates:
        name = game["player_names"].get(pid, str(pid))
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"vote_{pid}")])

    await callback.message.answer("🗳 Голосование! Выберите:",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    game = ongoing_games.get(cid)
    if not game:
        await callback.answer("Нет активной игры.")
        return

    voter = callback.from_user.id
    target = int(callback.data.split("_")[1])

    if voter not in game["alive_players"]:
        await callback.answer("Вы не участвуете.")
        return

    game["votes"][voter] = target
    await callback.answer("Голос учтён ✅")

    if len(game["votes"]) == len(game["alive_players"]):
        tally = {}
        for t in game["votes"].values():
            tally[t] = tally.get(t, 0) + 1
        eliminated = max(tally, key=tally.get)

        await db.mark_dead(game["game_id"], eliminated)
        role = game["alive_players"].pop(eliminated)
        await bot.send_message(cid, f"{game['player_names'].get(eliminated, eliminated)} выбыл. Его роль: {role}")

        mafia_left = [r for r in game["alive_players"].values() if r == "Мафия"]
        citizens_left = [r for r in game["alive_players"].values() if r != "Мафия"]

        winner = None
        if not mafia_left:
            winner = "Мирные"
        elif len(mafia_left) >= len(citizens_left):
            winner = "Мафия"

        if winner:
            await db.finalize_game(game["game_id"], winner)
            await bot.send_message(cid, f"🎉 Победили {winner}!")
            ongoing_games.pop(cid, None)
        else:
            game["votes"].clear()
            await bot.send_message(cid, "🗳 Новый раунд!")

@dp.callback_query(lambda c: c.data == "end_game")
async def end_game(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    # Проверим, есть ли активная игра
    game = ongoing_games.get(cid)
    lobby = lobbies.get(cid)

    if game:
        if game["host_id"] != uid:
            await callback.answer("❌ Только ведущий может завершить игру.", show_alert=True)
            return
        await db.finalize_game(game["game_id"], "Прервано")
        ongoing_games.pop(cid, None)
        await callback.message.reply("🛑 Игра завершена ведущим.")
    elif lobby:
        if lobby["host_id"] != uid:
            await callback.answer("❌ Только ведущий может завершить лобби.", show_alert=True)
            return
        lobbies.pop(cid, None)
        await callback.message.reply("🛑 Лобби закрыто ведущим.")
    else:
        await callback.answer("❌ Нет активной игры или лобби.", show_alert=True)
        return

    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_stats")
async def my_stats(callback: CallbackQuery, db: Database):
    stats = await db.get_player_stats(callback.from_user.id)
    if stats:
        await callback.message.answer(
            f"👤 Ваша статистика:\n"
            f"Игры: {stats['games_played']}\n"
            f"Победы: {stats['games_won']}\n"
            f"Мафия: {stats['mafia_wins']}\n"
            f"Мирные: {stats['citizen_wins']}"
        )
    else:
        await callback.message.answer("Нет статистики.")

@dp.callback_query(lambda c: c.data == "all_stats")
async def all_stats(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    game = ongoing_games.get(cid)

    rows = await db.get_all_player_stats()
    if not rows:
        await callback.message.answer("Нет статистики.")
        return

    text = "📊 Общая статистика:\n"
    for r in rows:
        text += (
            f"{r['username']}: "
            f"Игры={r['games_played']} Победы={r['games_won']} "
            f"Мафия={r['mafia_wins']} Мирные={r['citizen_wins']}\n"
        )
    await callback.message.answer(text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        db = Database(DB_URL)
        await db.connect()

        dp.message.middleware(DBMiddleware(db))
        dp.callback_query.middleware(DBMiddleware(db))

        await dp.start_polling(bot)

    asyncio.run(main())
