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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    chat_title TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    winner_side TEXT
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS game_participants (
                    game_id INTEGER REFERENCES games(id),
                    user_id BIGINT REFERENCES players(id),
                    role TEXT,
                    alive BOOLEAN
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS role_images (
                    id SERIAL PRIMARY KEY,
                    role TEXT,
                    image BYTEA
                );
            """)

    async def create_game(self, chat_id, chat_title):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO games(chat_id, chat_title, start_time)
                VALUES($1, $2, $3) RETURNING id;
            """, chat_id, chat_title, datetime.utcnow())
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
            return random.choice(rows)["image"] if rows else None

    async def mark_dead(self, game_id, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE game_participants SET alive=FALSE
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
            UPDATE games SET end_time=$1, winner_side=$2
            WHERE id=$3;
        """, datetime.utcnow(), winner, game_id)

        participants = await conn.fetch("""
            SELECT user_id, role FROM game_participants
            WHERE game_id=$1;
        """, game_id)

        for p in participants:
            user_id = p["user_id"]
            role = p["role"]

            games_won_inc = 1 if (winner == "Мафия" and role == "Мафия") or (winner == "Мирные" and role != "Мафия") else 0
            mafia_wins_inc = 1 if winner == "Мафия" and role == "Мафия" else 0
            citizen_wins_inc = 1 if winner == "Мирные" and role != "Мафия" else 0

            await conn.execute("""
                UPDATE players
                SET games_played = games_played + 1,
                    games_won = games_won + $1,
                    mafia_wins = mafia_wins + $2,
                    citizen_wins = citizen_wins + $3
                WHERE id = $4;
            """, games_won_inc, mafia_wins_inc, citizen_wins_inc, user_id)

    async def get_player_stats(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("""
                SELECT games_played, games_won, mafia_wins, citizen_wins
                FROM players WHERE id=$1;
            """, user_id)

    async def get_all_player_stats(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT username, games_played, games_won, mafia_wins, citizen_wins
                FROM players ORDER BY games_played DESC;
            """)
