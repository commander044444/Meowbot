# ==========================================
# Content History (Anti-Repetition)
# ==========================================

from .pool import fetch, execute, fetchval


async def get_seen_content_indices(user_id: int, content_type: str) -> set:
    rows = await fetch(
        "SELECT item_index FROM content_history WHERE user_id = $1 AND content_type = $2",
        int(user_id), content_type,
    )
    return {int(r["item_index"]) for r in rows}


async def mark_content_seen(user_id: int, content_type: str, item_index: int):
    await execute(
        """
        INSERT INTO content_history (user_id, content_type, item_index)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        int(user_id), content_type, int(item_index),
    )


async def count_seen_content(user_id: int, content_type: str) -> int:
    return int(await fetchval(
        "SELECT COUNT(*) FROM content_history WHERE user_id = $1 AND content_type = $2",
        int(user_id), content_type,
    ) or 0)


async def clear_content_history(user_id: int, content_type: str):
    """When all items seen, reset so they can cycle again."""
    await execute(
        "DELETE FROM content_history WHERE user_id = $1 AND content_type = $2",
        int(user_id), content_type,
    )


async def pick_unseen_index(user_id: int, content_type: str, total: int) -> int:
    """Pick a random unseen index; reset history if all seen."""
    import random
    if total <= 0:
        return 0
    seen = await get_seen_content_indices(user_id, content_type)
    available = [i for i in range(total) if i not in seen]
    if not available:
        await clear_content_history(user_id, content_type)
        available = list(range(total))
    idx = random.choice(available)
    await mark_content_seen(user_id, content_type, idx)
    return idx
