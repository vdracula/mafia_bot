import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
from database import DATABASE_URL

async def init_models():
    """
    Создаёт все таблицы в базе данных по описанным моделям.
    Если таблицы уже есть, новые колонки НЕ добавляются автоматически.
    """
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Создаю таблицы...")
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Таблицы успешно созданы или уже существуют.")

if __name__ == "__main__":
    asyncio.run(init_models())
