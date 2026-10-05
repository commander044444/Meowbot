# ==========================================
# Bug / Problem Reports
# ==========================================

from .pool import fetch, fetchrow, execute, fetchval
import json


async def create_report(user_id: int, text: str, username: str = "", first_name: str = "") -> int:
    row = await fetchrow(
        """
        INSERT INTO bug_reports (user_id, username, first_name, body, status)
        VALUES ($1, $2, $3, $4, 'open')
        RETURNING id
        """,
        int(user_id), username or "", first_name or "", text[:2000],
    )
    return int(row["id"]) if row else 0


async def list_reports(status: str = "open", limit: int = 20):
    if status == "all":
        rows = await fetch(
            "SELECT * FROM bug_reports ORDER BY created_at DESC LIMIT $1",
            int(limit),
        )
    else:
        rows = await fetch(
            "SELECT * FROM bug_reports WHERE status = $1 ORDER BY created_at DESC LIMIT $2",
            status, int(limit),
        )
    return [dict(r) for r in rows]


async def get_report(report_id: int):
    row = await fetchrow("SELECT * FROM bug_reports WHERE id = $1", int(report_id))
    return dict(row) if row else None


async def resolve_report(report_id: int, resolver_id: int) -> bool:
    result = await execute(
        """
        UPDATE bug_reports
        SET status = 'resolved', resolved_by = $2, resolved_at = NOW()
        WHERE id = $1 AND status = 'open'
        """,
        int(report_id), int(resolver_id),
    )
    return True


async def count_open_reports() -> int:
    return int(await fetchval("SELECT COUNT(*) FROM bug_reports WHERE status = 'open'") or 0)
