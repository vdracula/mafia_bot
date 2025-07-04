from sqlalchemy import select, func
from database import async_session
from models import Game, Player, Voting, Vote

# Создание игры
async def create_game(chat_id: int):
    async with async_session() as session:
        game = Game(chat_id=chat_id, status="active")
        session.add(game)
        await session.commit()
        await session.refresh(game)
        return game

# Добавление игрока
async def add_player(game_id: int, user_id: int, username: str):
    async with async_session() as session:
        player = Player(
            game_id=game_id,
            telegram_id=str(user_id),
            name=username,
            alive=True
        )
        session.add(player)
        await session.commit()
        await session.refresh(player)
        return player

# Убить игрока
async def kill_player(player_id: int):
    async with async_session() as session:
        result = await session.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        player.alive = False
        await session.commit()

# Запустить игру и раздать роли
async def start_game(game_id: int):
    async with async_session() as session:
        result = await session.execute(select(Player).where(Player.game_id == game_id))
        players = result.scalars().all()

        for p in players:
            p.role = "citizen"

        if players:
            players[0].role = "mafia"

        await session.commit()
        return players

# Получить живых игроков
async def get_alive_players(game_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Player).where(Player.game_id == game_id, Player.alive == True)
        )
        return result.scalars().all()
