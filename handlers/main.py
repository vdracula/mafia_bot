from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для управления игрой Мафия.\n\n"
        "Ведущий может создавать игры, добавлять игроков и управлять процессом.\n"
        "Для начала используйте /newgame"
    )

def register(dp):
    dp.include_router(router)