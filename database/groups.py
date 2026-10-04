# ==========================================
# Groups Repository
# ==========================================

from .pool import fetchrow, fetch, execute, fetchval


def _d(row):
    return dict(row) if row else None


async def register_group(chat_id, title="", username=""):
    cid = str(chat_id)
    await execute(
        """
        INSERT INTO groups (chat_id, title, username, last_seen)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (chat_id) DO UPDATE SET
            title = COALESCE(NULLIF($2, ''), groups.title),
            username = COALESCE(NULLIF($3, ''), groups.username),
            last_seen = NOW()
        """,
        cid, title or "", username or "",
    )


async def register_group_user(user_id, chat_id):
    await execute(
        """
        INSERT INTO group_users (user_id, chat_id, last_seen)
        VALUES ($1, $2, NOW())
        ON CONFLICT (user_id, chat_id) DO UPDATE SET last_seen = NOW()
        """,
        int(user_id), str(chat_id),
    )


async def get_group(chat_id):
    return _d(await fetchrow("SELECT * FROM groups WHERE chat_id = $1", str(chat_id)))


async def get_all_groups():
    rows = await fetch("SELECT * FROM groups ORDER BY last_seen DESC")
    return [_d(r) for r in rows]


async def set_interaction(chat_id, enabled: bool):
    await execute(
        "UPDATE groups SET interaction_on = $2 WHERE chat_id = $1",
        str(chat_id), bool(enabled),
    )


async def get_interaction(chat_id) -> bool:
    val = await fetchval("SELECT interaction_on FROM groups WHERE chat_id = $1", str(chat_id))
    return True if val is None else bool(val)


async def set_guide_settings(chat_id, enabled=None, interval=None, category=None):
    g = await get_group(chat_id)
    if not g:
        await register_group(chat_id)
    sets, args, i = [], [str(chat_id)], 2
    if enabled is not None:
        sets.append(f"guide_enabled = ${i}")
        args.append(bool(enabled))
        i += 1
    if interval is not None:
        sets.append(f"guide_interval = ${i}")
        args.append(int(interval))
        i += 1
    if category is not None:
        sets.append(f"guide_category = ${i}")
        args.append(str(category))
        i += 1
    if sets:
        await execute(f"UPDATE groups SET {', '.join(sets)} WHERE chat_id = $1", *args)


async def update_guide_last_sent(chat_id, ts: float):
    await execute(
        "UPDATE groups SET guide_last_sent = $2 WHERE chat_id = $1",
        str(chat_id), float(ts),
    )


async def get_groups_for_guide():
    """Groups where guide is enabled and interval > 0."""
    rows = await fetch(
        """
        SELECT * FROM groups
        WHERE guide_enabled = TRUE AND guide_interval > 0
        """
    )
    return [_d(r) for r in rows]


async def count_groups() -> int:
    return int(await fetchval("SELECT COUNT(*) FROM groups") or 0)
