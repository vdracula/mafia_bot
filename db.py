import os
import psycopg2
from psycopg2.extras import RealDictCursor


def init_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[INFO] DATABASE_URL не задан. Пропускаю инициализацию.")
        return

    try:
        conn = psycopg2.connect(db_url, sslmode="require", cursor_factory=RealDictCursor)
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
        print("[OK] База данных инициализирована.")
    except Exception as e:
        print(f"[ERROR] Не удалось подключиться к базе: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


def save_game_to_db(room_name, players, roles, winner):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[INFO] DATABASE_URL не задан. Не могу сохранить игру.")
        return

    try:
        conn = psycopg2.connect(db_url, sslmode="require")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO games (room_name, players, roles, winner) VALUES (%s, %s, %s, %s)",
            (room_name, str(players), str(roles), winner)
        )
        conn.commit()
        print("[OK] Игра сохранена в базу.")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить игру: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()