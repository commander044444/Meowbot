# ==========================================
# Guide History (per group anti-repetition)
# ==========================================

from .pool import fetch, execute, fetchval


async def get_sent_guide_keys(chat_id: str) -> set:
    rows = await fetch(
        "SELECT guide_key FROM guide_history WHERE chat_id = $1",
        str(chat_id),
    )
    return {r["guide_key"] for r in rows}


async def mark_guide_sent(chat_id: str, guide_key: str):
    await execute(
        """
        INSERT INTO guide_history (chat_id, guide_key)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        str(chat_id), guide_key,
    )


async def clear_guide_history(chat_id: str):
    await execute("DELETE FROM guide_history WHERE chat_id = $1", str(chat_id))


async def count_guide_history(chat_id: str) -> int:
    return int(await fetchval(
        "SELECT COUNT(*) FROM guide_history WHERE chat_id = $1", str(chat_id)
    ) or 0)
