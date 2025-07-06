import asyncpg
from datetime import datetime
import random

class Database:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)
        await self.setup()

    async def close(self):
        await self.pool.close()

    async def setup(self):
        async with self.pool.acquire() as conn:
            # Игроки
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id BIGINT PRIMARY KEY,
                    username TEXT,
                    games_played INTEGER DEFAULT 0,
                    games_won INTEGER DEFAULT 0,
                    mafia_wins INTEGER DEFAULT 0,
                    citizen_wins INTEGER DEFAULT 0
                );
            """)
            # Игры
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    winner_side TEXT
                );
            """)
            # Участники игры
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS game_participants (
                    game_id INTEGER REFERENCES games(id),
                    user_id BIGINT REFERENCES players(id),
                    role TEXT,
                    alive BOOLEAN
                );
            """)
            # Картинки ролей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS role_images (
                    id SERIAL PRIMARY KEY,
                    role TEXT,
                    image BYTEA
                );
            """)

    async def create_game(self, chat_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO games(chat_id, start_time)
                VALUES($1, $2)
                RETURNING id;
            """, chat_id, datetime.utcnow())
            return row["id"]

    async def add_player(self, user_id, username):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO players(id, username)
                VALUES($1, $2)
                ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username;
            """, user_id, username)

    async def add_participant(self, game_id, user_id, role):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO game_participants(game_id, user_id, role, alive)
                VALUES($1, $2, $3, TRUE);
            """, game_id, user_id, role)

    async def get_role_image(self, role):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT image FROM role_images WHERE role=$1;
            """, role)
            if rows:
                return random.choice(rows)["image"]
            return None

    async def mark_dead(self, game_id, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE game_participants
                SET alive=FALSE
                WHERE game_id=$1 AND user_id=$2;
            """, game_id, user_id)

    async def get_alive_players(self, game_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, role FROM game_participants
                WHERE game_id=$1 AND alive=TRUE;
            """, game_id)
            return {r["user_id"]: r["role"] for r in rows}

    async def finalize_game(self, game_id, winner):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE games
                SET end_time=$1, winner_side=$2
                WHERE id=$3;
            """, datetime.utcnow(), winner, game_id)

            participants = await conn.fetch("""
                SELECT user_id, role, alive FROM game_participants
                WHERE game_id=$1;
            """, game_id)

            for p in participants:
                await conn.execute("""
                    UPDATE players
                    SET games_played = games_played + 1,
                        games_won = games_won + CASE WHEN
                            ($1='Мафия' AND role='Мафия') OR
                            ($1='Мирные' AND role!='Мафия')
                        THEN 1 ELSE 0 END,
                        mafia_wins = mafia_wins + CASE WHEN ($1='Мафия' AND role='Мафия') THEN 1 ELSE 0 END,
                        citizen_wins = citizen_wins + CASE WHEN ($1='Мирные' AND role!='Мафия') THEN 1 ELSE 0 END
                    WHERE id=$2;
                """, winner, p["user_id"])

    async def get_player_stats(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("""
                SELECT games_played, games_won, mafia_wins, citizen_wins
                FROM players
                WHERE id=$1;
            """, user_id)
