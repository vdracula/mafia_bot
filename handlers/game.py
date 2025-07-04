from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils import create_game, add_player, start_game, kill_player
from keyboards import join_game_keyboard

router = Router()

@router.message(Command("create"))
async def handle_create(message: Message):
    game = await create_game(message.chat.id)
    await message.answer(
        f"🎲 Игра #{game.id} создана!\n"
        "Игроки, присоединяйтесь с помощью кнопки ниже.",
        reply_markup=join_game_keyboard(game.id)
    )

@router.message(Command("newgame"))
async def handle_newgame(message: Message):
    game = await create_game(message.chat.id)
    await message.answer(
        f"🎲 Игра #{game.id} создана!\n"
        "Игроки, присоединяйтесь с помощью кнопки ниже.",
        reply_markup=join_game_keyboard(game.id)
    )
