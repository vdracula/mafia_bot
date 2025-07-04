import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
from database import DATABASE_URL

async def init_models():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Полностью пересоздаём все таблицы
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ Все таблицы пересозданы.")

if __name__ == "__main__":
    asyncio.run(init_models())
