# ==========================================
# Audit Logs
# ==========================================

from .pool import execute, fetch
import json


def _to_jsonb(details) -> str:
    """همیشه JSON معتبر برای ستون jsonb بساز."""
    if details is None:
        return "{}"
    if isinstance(details, (dict, list)):
        return json.dumps(details, ensure_ascii=False)
    if isinstance(details, str):
        # اگر قبلاً JSON است همان را بگذار؛ وگرنه در object بپیچ
        s = details.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                json.loads(s)
                return s
            except Exception:
                pass
        return json.dumps({"value": details}, ensure_ascii=False)
    return json.dumps({"value": str(details)}, ensure_ascii=False)


async def log_action(actor_id: int, action: str, target: str = None, details=None, result: str = "ok"):
    try:
        await execute(
            """
            INSERT INTO audit_logs (actor_id, action, target, details, result)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            int(actor_id),
            str(action),
            str(target) if target is not None else None,
            _to_jsonb(details),
            str(result or "ok"),
        )
    except Exception as e:
        # لاگ نباید کل عملیات را خراب کند
        print(f"log_action failed: {e}")


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
