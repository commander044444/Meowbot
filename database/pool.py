# ==========================================
# PostgreSQL Connection Pool
# ==========================================

import asyncpg
import logging
from config import DATABASE_URL, DB_POOL_MIN, DB_POOL_MAX

logger = logging.getLogger("meowbot.db")

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    # Railway sometimes gives postgres:// — asyncpg needs postgresql://
    dsn = DATABASE_URL
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)

    try:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=DB_POOL_MIN,
            max_size=DB_POOL_MAX,
            command_timeout=60,
        )
        logger.info("✅ PostgreSQL pool created")
        return _pool
    except Exception as e:
        logger.error(f"❌ Failed to create DB pool: {e}")
        raise


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        return await init_pool()
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


async def fetch(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def executemany(query: str, args_list):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.executemany(query, args_list)
