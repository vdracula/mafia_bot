import random
from typing import Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.exceptions import TelegramMigrateToChat

from db import Database
from core import bot  # см. ниже, в bot.py нужно инициализировать bot в core

router = Router()

# В памяти — лобби, активные игры и чёрный список
lobbies: Dict[int, Dict[str, Any]] = {}
ongoing_games: Dict[int, Dict[str, Any]] = {}
blacklist: Dict[int, set[int]] = {}


def get_lobby_menu(is_host: bool = False) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🙋 Присоединиться", callback_data="join_lobby")]
    ]
    if is_host:
        buttons += [
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="lobby_settings")],
            [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_lobby")],
            [InlineKeyboardButton(text="🛑 Завершить игру", callback_data="end_game")],
            [
                InlineKeyboardButton(
                    text="👤 Выбрать кандидатов",
                    callback_data="select_vote_candidates",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗳 Начать голосование",
                    callback_data="start_vote",
                )
            ],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_settings_keyboard(config: dict) -> InlineKeyboardMarkup:
    mafia_count = config.get("mafia_count", 1)
    has_commissar = config.get("has_commissar", True)
    has_doctor = config.get("has_doctor", True)

    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"Мафия: {mafia_count}",
                callback_data="set_mafia_count",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Комиссар: {'✅' if has_commissar else '❌'}",
                callback_data="toggle_commissar",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Доктор: {'✅' if has_doctor else '❌'}",
                callback_data="toggle_doctor",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    buttons = [
        [InlineKeyboardButton(text="🎮 Создать игру", callback_data="create_lobby")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📊 Статистика игр", callback_data="all_stats")],
    ]
    await message.answer(
        "👋 Привет! Что хотите сделать?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "create_lobby")
async def create_lobby(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await callback.message.answer("❌ Игру можно создавать только в группе.")
        return

    cid = callback.message.chat.id
    uid = callback.from_user.id
    name = callback.from_user.full_name

    lobbies[cid] = {
        "host_id": uid,
        "players": {uid: name},
        "config": {
            "mafia_count": 2,
            "has_commissar": True,
            "has_doctor": True,
        },
    }

    await callback.message.answer(
        f"🎮 Игра создана ведущим {name}. Игроки могут присоединяться.",
        reply_markup=get_lobby_menu(is_host=True),
    )
    await callback.answer()


@router.callback_query(F.data == "lobby_settings")
async def lobby_settings(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    lobby = lobbies.get(cid)
    if not lobby or lobby["host_id"] != uid:
        await callback.answer("❌ Только ведущий может менять настройки.", show_alert=True)
        return

    config = lobby.get("config", {})
    await callback.message.answer(
        "⚙️ Настройки лобби",
        reply_markup=build_settings_keyboard(config),
    )
    await callback.answer()


@router.callback_query(F.data == "set_mafia_count")
async def set_mafia_count(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    lobby = lobbies.get(cid)
    if not lobby or lobby["host_id"] != uid:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    config = lobby.setdefault("config", {})
    mafia_count = config.get("mafia_count", 1)
    mafia_count = mafia_count + 1
    if mafia_count > 3:
        mafia_count = 1
    config["mafia_count"] = mafia_count

    await callback.message.edit_reply_markup(
        reply_markup=build_settings_keyboard(config)
    )
    await callback.answer(f"Мафии: {mafia_count}")


@router.callback_query(F.data == "toggle_commissar")
async def toggle_commissar(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    lobby = lobbies.get(cid)
    if not lobby or lobby["host_id"] != uid:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    config = lobby.setdefault("config", {})
    config["has_commissar"] = not config.get("has_commissar", True)

    await callback.message.edit_reply_markup(
        reply_markup=build_settings_keyboard(config)
    )
    await callback.answer("Комиссар переключён.")


@router.callback_query(F.data == "toggle_doctor")
async def toggle_doctor(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    lobby = lobbies.get(cid)
    if not lobby or lobby["host_id"] != uid:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    config = lobby.setdefault("config", {})
    config["has_doctor"] = not config.get("has_doctor", True)

    await callback.message.edit_reply_markup(
        reply_markup=build_settings_keyboard(config)
    )
    await callback.answer("Доктор переключён.")


@router.callback_query(F.data == "join_lobby")
async def join_lobby(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id
    name = callback.from_user.full_name

    if cid in blacklist and uid in blacklist[cid]:
        await callback.answer("Вы заблокированы в этой игре.", show_alert=True)
        return

    if cid not in lobbies:
        await callback.message.answer("Нет активной лобби.")
        return

    lobbies[cid]["players"][uid] = name
    await db.add_player(uid, name)

    await callback.message.answer(f"{name} присоединился к игре.")
    await callback.answer()


@router.callback_query(F.data == "start_lobby")
async def start_lobby(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    lobby = lobbies.get(cid)
    if not lobby or lobby["host_id"] != uid:
        await callback.message.answer("❌ Только ведущий может начать игру.")
        return

    players: dict[int, str] = lobby["players"]
    if len(players) < 4:
        await callback.message.answer("Нужно минимум 4 игрока.")
        return

    try:
        gid = await db.create_game(cid, callback.message.chat.title)

        player_ids = list(players.keys())
        random.shuffle(player_ids)

        config = lobby.get("config", {})
        mafia_count = config.get("mafia_count", 1)
        mafia_count = min(mafia_count, max(1, len(players) // 3))

        mafia_ids = set(player_ids[:mafia_count])
        remaining = [pid for pid in player_ids if pid not in mafia_ids]

        has_commissar = config.get("has_commissar", True)
        has_doctor = config.get("has_doctor", True)

        commissioner_id = remaining[0] if has_commissar and len(remaining) >= 1 else None
        doctor_id = remaining[1] if has_doctor and len(remaining) >= 2 else None

        alive: dict[int, str] = {}

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
                    caption=f"🕵 Ваша роль: {role}",
                )
            else:
                await bot.send_message(pid, f"🕵 Ваша роль: {role}")

            alive[pid] = role

        ongoing_games[cid] = {
            "game_id": gid,
            "host_id": uid,
            "host_name": callback.from_user.full_name,
            "phase": "day",
            "alive_players": alive,
            "player_names": players,
            "votes": {},
            "vote_candidates": [],
            "night_actions": {
                "mafia_target": None,
                "doctor_target": None,
                "commissar_target": None,
                "mafia_votes": {},
            },
        }

        lobbies.pop(cid, None)

        await callback.message.answer(
            "🎲 Игра началась!",
            reply_markup=get_lobby_menu(is_host=True),
        )
    except TelegramMigrateToChat as e:
        new_cid = e.migrate_to_chat_id
        lobbies[new_cid] = lobbies.pop(cid)
        await callback.message.answer(
            "🔁 Группа была обновлена до супергруппы. Повторите команду."
        )
    finally:
        await callback.answer()


@router.callback_query(F.data == "select_vote_candidates")
async def select_vote_candidates(callback: CallbackQuery):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    game = ongoing_games.get(cid)
    if not game or game["host_id"] != uid:
        await callback.message.answer("❌ Только ведущий может выбрать кандидатов.")
        return

    keyboard: list[list[InlineKeyboardButton]] = []

    for pid in game["alive_players"]:
        name = game["player_names"].get(pid, str(pid))
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"toggle_candidate_{pid}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="🗳 Начать голосование",
                callback_data="start_vote",
            )
        ]
    )

    await callback.message.answer(
        "Выберите кандидатов для голосования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_candidate_"))
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


@router.callback_query(F.data == "start_vote")
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

    keyboard: list[list[InlineKeyboardButton]] = []
    for pid in candidates:
        name = game["player_names"].get(pid, str(pid))
        keyboard.append(
            [InlineKeyboardButton(text=name, callback_data=f"vote_{pid}")]
        )

    await callback.message.answer(
        "🗳 Голосование! Выберите:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vote_"))
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
        tally: dict[int, int] = {}
        for t in game["votes"].values():
            tally[t] = tally.get(t, 0) + 1

        eliminated = max(tally, key=tally.get)

        await db.mark_dead(game["game_id"], eliminated)
        role = game["alive_players"].pop(eliminated)

        await bot.send_message(
            cid,
            f"{game['player_names'].get(eliminated, eliminated)} выбыл. Его роль: {role}",
        )

        mafia_left = [r for r in game["alive_players"].values() if r == "Мафия"]
        citizens_left = [r for r in game["alive_players"].values() if r != "Мафия"]

        winner: str | None = None
        if not mafia_left:
            winner = "Мирные"
        elif len(mafia_left) >= len(citizens_left):
            winner = "Мафия"

        if winner:
            await db.finalize_game(game["game_id"], winner)
            await bot.send_message(cid, f"🎉 Победили {winner}!")
            ongoing_games.pop(cid, None)
        else:
            # Переход к ночи
            game["votes"].clear()
            game["phase"] = "night"
            game["night_actions"] = {
                "mafia_target": None,
                "doctor_target": None,
                "commissar_target": None,
                "mafia_votes": {},
            }
            await bot.send_message(cid, "🌙 Наступает ночь...")
            await start_night_phase(cid)
    # если ещё не все проголосовали — просто ждём


@router.callback_query(F.data == "end_game")
async def end_game(callback: CallbackQuery, db: Database):
    cid = callback.message.chat.id
    uid = callback.from_user.id

    game = ongoing_games.get(cid)
    lobby = lobbies.get(cid)

    if game:
        if game["host_id"] != uid:
            await callback.answer(
                "❌ Только ведущий может завершить игру.", show_alert=True
            )
            return

        await db.finalize_game(game["game_id"], "Прервано")
        ongoing_games.pop(cid, None)
        await callback.message.reply("🛑 Игра завершена ведущим.")

    elif lobby:
        if lobby["host_id"] != uid:
            await callback.answer(
                "❌ Только ведущий может завершить лобби.", show_alert=True
            )
            return

        lobbies.pop(cid, None)
        await callback.message.reply("🛑 Лобби закрыто ведущим.")
    else:
        await callback.answer(
            "❌ Нет активной игры или лобби.", show_alert=True
        )
        return

    await callback.answer()


@router.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery, db: Database):
    stats = await db.get_player_stats(callback.from_user.id)

    if stats:
        await callback.message.answer(
            "👤 Ваша статистика:\n"
            f"Игры: {stats['games_played']}\n"
            f"Победы: {stats['games_won']}\n"
            f"Мафия: {stats['mafia_wins']}\n"
            f"Мирные: {stats['citizen_wins']}"
        )
    else:
        await callback.message.answer("Нет статистики.")
    await callback.answer()


@router.callback_query(F.data == "all_stats")
async def all_stats(callback: CallbackQuery, db: Database):
    rows = await db.get_all_player_stats()

    if not rows:
        await callback.message.answer("Нет статистики.")
        await callback.answer()
        return

    text_lines = ["📊 Общая статистика:"]
    for r in rows:
        text_lines.append(
            f"{r['username']}: "
            f"Игры={r['games_played']} Победы={r['games_won']} "
            f"Мафия={r['mafia_wins']} Мирные={r['citizen_wins']}"
        )

    await callback.message.answer("\n".join(text_lines))
    await callback.answer()


@router.message(Command("ban_player"))
async def ban_player(message: Message):
    if message.chat.type == "private" or not message.reply_to_message:
        await message.answer("Используйте /ban_player в ответ на сообщение игрока в группе.")
        return

    cid = message.chat.id
    host_id = (
        lobbies.get(cid, {}).get("host_id")
        or ongoing_games.get(cid, {}).get("host_id")
    )
    if host_id != message.from_user.id:
        await message.answer("❌ Только ведущий может банить игроков.")
        return

    target = message.reply_to_message.from_user.id
    blacklist.setdefault(cid, set()).add(target)
    await message.answer("Игрок добавлен в чёрный список для этой комнаты.")
async def start_night_phase(chat_id: int):
    game = ongoing_games.get(chat_id)
    if not game:
        return

    # Мафия
    for pid, role in game["alive_players"].items():
        if role == "Мафия":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=game["player_names"].get(target_id, str(target_id)),
                            callback_data=f"night_mafia_{target_id}",
                        )
                    ]
                    for target_id in game["alive_players"]
                    if target_id != pid
                ]
            )
            await bot.send_message(
                pid,
                "🌙 Ночь. Кого убить?",
                reply_markup=keyboard,
            )

    # Доктор
    for pid, role in game["alive_players"].items():
        if role == "Доктор":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=game["player_names"].get(target_id, str(target_id)),
                            callback_data=f"night_doctor_{target_id}",
                        )
                    ]
                    for target_id in game["alive_players"]
                ]
            )
            await bot.send_message(
                pid,
                "🌙 Ночь. Кого лечить?",
                reply_markup=keyboard,
            )

    # Комиссар
    for pid, role in game["alive_players"].items():
        if role == "Комиссар":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=game["player_names"].get(target_id, str(target_id)),
                            callback_data=f"night_commissar_{target_id}",
                        )
                    ]
                    for target_id in game["alive_players"]
                    if target_id != pid
                ]
            )
            await bot.send_message(
                pid,
                "🌙 Ночь. Кого проверить?",
                reply_markup=keyboard,
            )


async def try_finish_night(chat_id: int | None, db: Database):
    if chat_id is None:
        return

    game = ongoing_games.get(chat_id)
    if not game or game["phase"] != "night":
        return

    actions = game["night_actions"]
    mafia_target = actions["mafia_target"]
    doctor_target = actions["doctor_target"]

    mafia_done = mafia_target is not None
    doctor_needed = any(r == "Доктор" for r in game["alive_players"].values())
    commissar_needed = any(r == "Комиссар" for r in game["alive_players"].values())

    doctor_done = (not doctor_needed) or (doctor_target is not None)
    commissar_done = (not commissar_needed) or (
        actions["commissar_target"] is not None
    )

    if not (mafia_done and doctor_done and commissar_done):
        return

    killed_player: int | None = None
    if (
        mafia_target is not None
        and mafia_target != doctor_target
        and mafia_target in game["alive_players"]
    ):
        killed_player = mafia_target

    if killed_player is not None:
        role = game["alive_players"].pop(killed_player)
        await db.mark_dead(game["game_id"], killed_player)
        text = (
            "🌙 Ночь закончилась.\n"
            f"Сегодня убит {game['player_names'].get(killed_player, killed_player)}. "
            f"Его роль: {role}"
        )
    else:
        text = "🌙 Ночь закончилась. Никто не погиб."

    mafia_left = [r for r in game["alive_players"].values() if r == "Мафия"]
    citizens_left = [r for r in game["alive_players"].values() if r != "Мафия"]

    winner: str | None = None
    if not mafia_left:
        winner = "Мирные"
    elif len(mafia_left) >= len(citizens_left):
        winner = "Мафия"

    if winner:
        await db.finalize_game(game["game_id"], winner)
        await bot.send_message(chat_id, text + f"\n\n🎉 Победили {winner}!")
        ongoing_games.pop(chat_id, None)
        return

    game["phase"] = "day"
    game["votes"].clear()
    game["vote_candidates"] = []
    game["night_actions"] = {
        "mafia_target": None,
        "doctor_target": None,
        "commissar_target": None,
        "mafia_votes": {},
    }

    await bot.send_message(chat_id, text + "\n\nНаступает новый день. Обсуждение!")
@router.callback_query(F.data.startswith("night_mafia_"))
async def night_mafia_move(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    target = int(callback.data.split("_")[2])

    game_chat_id = None
    game_obj = None
    for chat_id, game in ongoing_games.items():
        if (
            game["phase"] == "night"
            and game["alive_players"].get(user_id) == "Мафия"
        ):
            game_chat_id = chat_id
            game_obj = game
            break

    if not game_obj:
        await callback.answer("Ночь не активна или вы не мафия.", show_alert=True)
        return

    game_obj["night_actions"]["mafia_votes"][user_id] = target
    await callback.answer("Цель выбрана.")

    mafia_ids = [
        pid
        for pid, role in game_obj["alive_players"].items()
        if role == "Мафия"
    ]
    if len(game_obj["night_actions"]["mafia_votes"]) == len(mafia_ids):
        tally: dict[int, int] = {}
        for t in game_obj["night_actions"]["mafia_votes"].values():
            tally[t] = tally.get(t, 0) + 1
        mafia_target = max(tally, key=tally.get)
        game_obj["night_actions"]["mafia_target"] = mafia_target

        await try_finish_night(game_chat_id, db)


@router.callback_query(F.data.startswith("night_doctor_"))
async def night_doctor_move(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    target = int(callback.data.split("_")[2])

    game_chat_id = None
    game_obj = None
    for chat_id, game in ongoing_games.items():
        if (
            game["phase"] == "night"
            and game["alive_players"].get(user_id) == "Доктор"
        ):
            game_chat_id = chat_id
            game_obj = game
            break

    if not game_obj:
        await callback.answer("Ночь не активна или вы не доктор.", show_alert=True)
        return

    game_obj["night_actions"]["doctor_target"] = target
    await callback.answer("Цель лечения выбрана.")
    await try_finish_night(game_chat_id, db)


@router.callback_query(F.data.startswith("night_commissar_"))
async def night_commissar_move(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    target = int(callback.data.split("_")[2])

    game_chat_id = None
    game_obj = None
    for chat_id, game in ongoing_games.items():
        if (
            game["phase"] == "night"
            and game["alive_players"].get(user_id) == "Комиссар"
        ):
            game_chat_id = chat_id
            game_obj = game
            break

    if not game_obj:
        await callback.answer("Ночь не активна или вы не комиссар.", show_alert=True)
        return

    game_obj["night_actions"]["commissar_target"] = target

    role = game_obj["alive_players"].get(target)
    text = (
        f"{game_obj['player_names'].get(target, target)} — Мафия."
        if role == "Мафия"
        else f"{game_obj['player_names'].get(target, target)} — не мафия."
    )
    await callback.answer("Цель проверки выбрана.")
    await callback.message.answer(text)

    await try_finish_night(game_chat_id, db)
