# db.py

import asyncpg
from config import DATABASE_URL

async def create_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (...);
        CREATE TABLE IF NOT EXISTS players (...);
    """)
    await conn.close()