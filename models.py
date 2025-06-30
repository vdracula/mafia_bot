# utils.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import Game, Player, Voting, Vote


# ======================
# GAME UTILS
# ======================

async def create_game(session: AsyncSession) -> Game:
    game = Game()
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def get_game(session: AsyncSession, game_id: int) -> Game | None:
    result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    return result.scalar_one_or_none()


async def finish_game(session: AsyncSession, game: Game):
    game.status = "finished"
    await session.commit()


# ======================
# PLAYER UTILS
# ======================

async def add_player(session: AsyncSession, game: Game, telegram_id: str, name: str) -> Player:
    player = Player(
        game_id=game.id,
        telegram_id=telegram_id,
        name=name
    )
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def get_players(session: AsyncSession, game: Game) -> list[Player]:
    result = await session.execute(
        select(Player).where(Player.game_id == game.id)
    )
    return result.scalars().all()


async def get_alive_players(session: AsyncSession, game: Game) -> list[Player]:
    result = await session.execute(
        select(Player).where(
            Player.game_id == game.id,
            Player.alive.is_(True)
        )
    )
    return result.scalars().all()


async def kill_player(session: AsyncSession, player: Player):
    player.alive = False
    await session.commit()


# ======================
# ROLE UTILS
# ======================

async def assign_roles(session: AsyncSession, game: Game):
    """
    Назначает роли всем игрокам. Например, случайно 1 мафия.
    """
    players = await get_players(session, game)
    if not players:
        return

    # Сначала всем "citizen"
    for p in players:
        p.role = "citizen"

    # Одного случайно назначаем мафией
    mafia_player = players[0]
    mafia_player.role = "mafia"

    await session.commit()


# ======================
# VOTING UTILS
# ======================

async def start_voting(session: AsyncSession, game: Game) -> Voting:
    voting = Voting(
        game_id=game.id,
        status="active"
    )
    session.add(voting)
    await session.commit()
    await session.refresh(voting)
    return voting


async def finish_voting(session: AsyncSession, voting: Voting):
    voting.status = "finished"
    await session.commit()


async def get_active_voting(session: AsyncSession, game: Game) -> Voting | None:
    result = await session.execute(
        select(Voting).where(
            Voting.game_id == game.id,
            Voting.status == "active"
        )
    )
    return result.scalar_one_or_none()


async def add_vote(session: AsyncSession, voting: Voting, voter_id: int, target_player_id: int):
    vote = Vote(
        voting_id=voting.id,
        player_id=voter_id,
        target_player_id=target_player_id
    )
    session.add(vote)
    await session.commit()


async def count_votes(session: AsyncSession, voting: Voting) -> dict[int, int]:
    """
    Возвращает словарь:
    { target_player_id: количество голосов }
    """
    result = await session.execute(
        select(
            Vote.target_player_id,
            func.count(Vote.id)
        ).where(
            Vote.voting_id == voting.id
        ).group_by(
            Vote.target_player_id
        )
    )
    return {row[0]: row[1] for row in result.all()}
