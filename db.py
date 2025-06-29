import asyncpg
from config import DATABASE_URL

async def create_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def init_db():
    pool = await create_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                host_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                started BOOLEAN DEFAULT FALSE,
                stage TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                room_id INTEGER REFERENCES rooms(id),
                role TEXT,
                alive BOOLEAN DEFAULT TRUE,
                UNIQUE(user_id, room_id)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS room_roles (
                room_id INTEGER REFERENCES rooms(id),
                role TEXT,
                count INTEGER,
                PRIMARY KEY (room_id, role)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                room_id INTEGER REFERENCES rooms(id),
                voter_id BIGINT,
                target_id BIGINT,
                PRIMARY KEY (room_id, voter_id)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                id SERIAL PRIMARY KEY,
                room_id INTEGER REFERENCES rooms(id),
                winner TEXT,
                total_players INTEGER,
                duration INTERVAL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        ''')
    return pool
