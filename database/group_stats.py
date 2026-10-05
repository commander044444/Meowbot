# ==========================================
# Per-group ranking stats
# اقتصاد (سکه و ...) سراسری است؛ فقط امتیاز رنکینگ گروه جداست
# ==========================================

from .pool import fetch, fetchrow, execute, fetchval


async def add_group_points(user_id: int, chat_id, amount: int = 1):
    if chat_id is None:
        return
    cid = str(chat_id)
    await execute(
        """
        INSERT INTO group_stats (chat_id, user_id, meow_points, total_meows, last_meow)
        VALUES ($1, $2, $3, 1, NOW())
        ON CONFLICT (chat_id, user_id) DO UPDATE SET
            meow_points = group_stats.meow_points + $3,
            total_meows = group_stats.total_meows + 1,
            last_meow = NOW()
        """,
        cid, int(user_id), int(amount),
    )


async def get_group_top(chat_id, limit: int = 10, kind: str = "points"):
    cid = str(chat_id)
    if kind == "meows":
        order = "gs.total_meows DESC"
        col = "total_meows"
    else:
        order = "gs.meow_points DESC"
        col = "meow_points"
    rows = await fetch(
        f"""
        SELECT gs.user_id, gs.meow_points, gs.total_meows,
               u.first_name, u.username
        FROM group_stats gs
        LEFT JOIN users u ON u.user_id = gs.user_id
        WHERE gs.chat_id = $1
        ORDER BY {order}
        LIMIT $2
        """,
        cid, int(limit),
    )
    return [dict(r) for r in rows]


async def reset_group_season_points():
    """فقط امتیاز فصل گروهی (همراه فصل سراسری)."""
    await execute("UPDATE group_stats SET meow_points = 0")


async def get_user_group_points(user_id: int, chat_id) -> int:
    val = await fetchval(
        "SELECT meow_points FROM group_stats WHERE chat_id = $1 AND user_id = $2",
        str(chat_id), int(user_id),
    )
    return int(val or 0)
