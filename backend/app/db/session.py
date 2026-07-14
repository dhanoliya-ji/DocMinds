from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Create asynchronous engine.
# Using NullPool is critical when running Celery background tasks that spin up separate 
# asyncio event loops inside the worker thread to prevent "Event loop is closed" errors.
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.ENV == "development",
    future=True,
    poolclass=NullPool
)

# AsyncSession factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for FastAPI endpoints to acquire a scoped database session.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
