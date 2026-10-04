# ==========================================
# Economy / Transactions
# ==========================================

from .pool import execute, fetch
import json


async def record_transaction(user_id: int, tx_type: str, amount: int, balance_after: int = None, meta: dict = None):
    await execute(
        """
        INSERT INTO transactions (user_id, type, amount, balance_after, meta)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        int(user_id), tx_type, int(amount), balance_after, json.dumps(meta or {}),
    )


async def get_user_transactions(user_id: int, limit: int = 20):
    rows = await fetch(
        "SELECT * FROM transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        int(user_id), int(limit),
    )
    return [dict(r) for r in rows]
