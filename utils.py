from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import NoResultFound
from database import async_session
from models import Game, Player, Vote


# Создать новую игру
async def create_game(chat_id: int):
    async with async_session() as session:
        game = Game(
            chat_id=chat_id,
            is_active=True
        )
        session.add(game)
        await session.commit()
        return game


# Завершить игру
async def finish_game(chat_id: int):
    async with async_session() as session:
        await session.execute(
            update(Game)
            .where(Game.chat_id == chat_id, Game.is_active == True)
            .values(is_active=False)
        )
        await session.commit()


# Получить активную игру
async def get_active_game(chat_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Game)
            .where(Game.chat_id == chat_id, Game.is_active == True)
        )
        game = result.scalar_one_or_none()
        return game


# Добавить игрока в игру
async def add_player(game_id: int, user_id: int, username: str):
    async with async_session() as session:
        player = Player(
            game_id=game_id,
            user_id=user_id,
            username=username,
            is_alive=True
        )
        session.add(player)
        await session.commit()
        return player


# Получить всех игроков игры
async def get_players(game_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Player)
            .where(Player.game_id == game_id)
        )
        return result.scalars().all()


# Получить живых игроков игры
async def get_alive_players(game_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Player)
            .where(Player.game_id == game_id, Player.is_alive == True)
        )
        return result.scalars().all()


# Установить роль игрока
async def set_player_role(player_id: int, role: str):
    async with async_session() as session:
        await session.execute(
            update(Player)
            .where(Player.id == player_id)
            .values(role=role)
        )
        await session.commit()


# Убить игрока
async def kill_player(player_id: int):
    async with async_session() as session:
        await session.execute(
            update(Player)
            .where(Player.id == player_id)
            .values(is_alive=False)
        )
        await session.commit()


# Сохранить голос
async def save_vote(voter_id: int, voted_player_id: int):
    async with async_session() as session:
        vote = Vote(
            voter_id=voter_id,
            voted_player_id=voted_player_id
        )
        session.add(vote)
        await session.commit()


# Посчитать результаты голосования
async def finish_voting():
    """
    Возвращает словарь {voted_player_id: count}
    """
    async with async_session() as session:
        result = await session.execute(
            select(Vote.voted_player_id, func.count(Vote.id))
            .group_by(Vote.voted_player_id)
        )
        votes = result.all()

        # Очистим таблицу после подсчета
        await session.execute(delete(Vote))
        await session.commit()

        return {player_id: count for player_id, count in votes}


# Очистить голоса (если нужно вручную сбросить)
async def clear_votes():
    async with async_session() as session:
        await session.execute(delete(Vote))
        await session.commit()

# Запустить игру и раздать роли
async def start_game(game_id: int):
    async with async_session() as session:
        # Получим всех игроков
        result = await session.execute(
            select(Player)
            .where(Player.game_id == game_id)
        )
        players = result.scalars().all()

        # Сначала всем граждан
        for p in players:
            p.role = "citizen"

        # Первому - мафию (для примера)
        if players:
            players[0].role = "mafia"

        await session.commit()
        return players