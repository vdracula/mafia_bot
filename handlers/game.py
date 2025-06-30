from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from database import async_session
from models import Game, Player

router = Router()

@router.message(Command("newgame"))
async def new_game(message: types.Message):
    async with async_session() as session:
        # Создаём игру
        game = Game()
        session.add(game)
        await session.commit()
        await session.refresh(game)

    await message.answer(f"🎲 Новая игра создана! ID игры: <b>{game.id}</b>\nДобавьте игроков с помощью /addplayer")

@router.message(Command("addplayer"))
async def add_player(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Используйте формат:\n<code>/addplayer [ID игры] [Имя игрока]</code>")
        return

    try:
        game_id = int(args[1])
    except ValueError:
        await message.answer("⚠️ ID игры должен быть числом.")
        return

    player_name = args[2]

    async with async_session() as session:
        # Проверяем, есть ли игра
        result = await session.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if not game:
            await message.answer("❌ Игра с таким ID не найдена.")
            return

        # Добавляем игрока
        player = Player(game_id=game.id, name=player_name)
        session.add(player)
        await session.commit()

    await message.answer(f"✅ Игрок <b>{player_name}</b> добавлен в игру {game.id}.")

@router.message(Command("listplayers"))
async def list_players(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Используйте формат:\n<code>/listplayers [ID игры]</code>")
        return

    try:
        game_id = int(args[1])
    except ValueError:
        await message.answer("⚠️ ID игры должен быть числом.")
        return

    async with async_session() as session:
        result = await session.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if not game:
            await message.answer("❌ Игра с таким ID не найдена.")
            return

        players = game.players
        if not players:
            await message.answer("🙁 В этой игре пока нет игроков.")
            return

        text = "\n".join(
            [f"{idx+1}. {p.name} (ID {p.id})" for idx, p in enumerate(players)]
        )
        await message.answer(f"👥 Игроки игры {game.id}:\n\n{text}")

def register(dp):
    dp.include_router(router)
