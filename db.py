import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL")

def init_db():
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require",
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            room_name TEXT,
            players TEXT,
            roles TEXT,
            winner TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_game_to_db(room_name, players, roles, winner):
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO games (room_name, players, roles, winner) VALUES (%s, %s, %s, %s)",
        (room_name, str(players), str(roles), winner)
    )
    conn.commit()
    cur.close()
    conn.close()