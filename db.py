import asyncpg
from config import DATABASE_URL
from typing import Dict, Any
import os

async def create_pool():
    return await asyncpg.create_pool(os.getenv('DATABASE_URL'))

# Временное хранилище комнат (если нужно для миграции)
rooms: Dict[str, Any] = {}

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
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                room_id INTEGER REFERENCES rooms(id),
                role TEXT,
                alive BOOLEAN DEFAULT TRUE,
                UNIQUE(user_id, room_id)
            )
        ''')
    return pool