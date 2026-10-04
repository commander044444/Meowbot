# ==========================================
# Audit Logs
# ==========================================

from .pool import execute, fetch
import json


async def log_action(actor_id: int, action: str, target: str = None, details: dict = None, result: str = "ok"):
    await execute(
        """
        INSERT INTO audit_logs (actor_id, action, target, details, result)
        VALUES ($1, $2, $3, $4::jsonb, $5)
        """,
        int(actor_id), action, target, json.dumps(details or {}), result,
    )


async def get_recent_logs(limit: int = 50, actor_id: int = None):
    if actor_id:
        rows = await fetch(
            "SELECT * FROM audit_logs WHERE actor_id = $1 ORDER BY created_at DESC LIMIT $2",
            int(actor_id), int(limit),
        )
    else:
        rows = await fetch(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT $1",
            int(limit),
        )
    return [dict(r) for r in rows]
