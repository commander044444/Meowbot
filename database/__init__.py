from .pool import get_pool, close_pool, init_pool, fetch, fetchrow, fetchval, execute
from .schema import init_schema

async def init_database():
    await init_pool()
    await init_schema()

# Re-export commonly used
from . import users, groups, pets, seasons, admins, logs, content, bank, guides
from . import economy, achievements, missions, events, inventory
