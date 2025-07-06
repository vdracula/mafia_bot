import asyncpg
import asyncio

DATABASE_URL = "postgresql://postgres:CbJlyIOfThlbNFbAnjsCVllWKhfFzMOH@centerbeam.proxy.rlwy.net:10819/railway"

ROLE_IMAGES = {
    "Мафия": [
        "images/mafia1.jpg",
        "images/mafia2.jpg",
        "images/mafia3.jpg",
        "images/mafia4.jpg"
    ],
    "Мирный": [
        "images/citizen1.jpg",
        "images/citizen2.jpg"
    ],
    "Доктор": ["images/doctor.jpg"],
    "Комиссар": ["images/commissar.jpg"]
}

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    # Сначала очищаем таблицу
    await conn.execute("DELETE FROM role_images;")
    for role, paths in ROLE_IMAGES.items():
        for path in paths:
            with open(path, "rb") as f:
                data = f.read()
            await conn.execute("""
                INSERT INTO role_images(role, image) VALUES($1, $2);
            """, role, data)
    await conn.close()
    print("✅ Все картинки загружены.")

asyncio.run(main())
