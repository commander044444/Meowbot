from .pool import fetch, fetchrow, execute


async def get_active_events():
    rows = await fetch(
        "SELECT * FROM events WHERE active = TRUE AND end_at > NOW() ORDER BY start_at"
    )
    return [dict(r) for r in rows]


async def create_event(name, description, start_at, end_at, bonus_xp=1.0, bonus_coin=1.0, special_item=None):
    await execute(
        """
        INSERT INTO events (name, description, start_at, end_at, bonus_xp, bonus_coin, special_item, active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
        """,
        name, description, start_at, end_at, bonus_xp, bonus_coin, special_item,
    )


async def end_event(event_id: int):
    await execute("UPDATE events SET active = FALSE WHERE id = $1", int(event_id))
