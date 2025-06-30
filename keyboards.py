from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def join_game_keyboard(game_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🟢 Присоединиться",
                callback_data=f"join_{game_id}"
            )
        ]
    ])


def start_game_keyboard(game_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚀 Начать игру",
                callback_data=f"start_{game_id}"
            )
        ]
    ])


def kill_player_keyboard(players: list) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"💀 {name}",
                callback_data=f"kill_{player_id}"
            )
        ] for player_id, name in players
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def voting_keyboard(players: list) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🗳️ {name}",
                callback_data=f"vote_{player_id}"
            )
        ] for player_id, name in players
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
