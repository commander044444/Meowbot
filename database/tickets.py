# ==========================================
# Support Tickets
# ==========================================

from .pool import fetch, fetchrow, execute, fetchval


def _d(row):
    return dict(row) if row else None


async def create_ticket(user_id: int, body: str, subject: str = "", tracking_code: str = ""):
    row = await fetchrow(
        """
        INSERT INTO tickets (user_id, subject, body, tracking_code, status)
        VALUES ($1, $2, $3, $4, 'open')
        RETURNING *
        """,
        int(user_id), subject or "پشتیبانی", body[:3000], tracking_code or "",
    )
    return _d(row)


async def list_tickets(status: str = "open", limit: int = 30):
    if status == "all":
        rows = await fetch(
            "SELECT * FROM tickets ORDER BY created_at DESC LIMIT $1", int(limit)
        )
    else:
        rows = await fetch(
            "SELECT * FROM tickets WHERE status = $1 ORDER BY created_at DESC LIMIT $2",
            status, int(limit),
        )
    return [_d(r) for r in rows]


async def get_ticket(ticket_id: int):
    return _d(await fetchrow("SELECT * FROM tickets WHERE id = $1", int(ticket_id)))


async def reply_ticket(ticket_id: int, admin_id: int, reply: str):
    await execute(
        """
        UPDATE tickets SET
            admin_reply = $2,
            replied_by = $3,
            replied_at = NOW(),
            status = 'answered'
        WHERE id = $1
        """,
        int(ticket_id), reply[:3000], int(admin_id),
    )
    return await get_ticket(ticket_id)


async def close_ticket(ticket_id: int):
    await execute(
        "UPDATE tickets SET status = 'closed' WHERE id = $1", int(ticket_id)
    )


async def count_open_tickets() -> int:
    return int(await fetchval("SELECT COUNT(*) FROM tickets WHERE status = 'open'") or 0)


async def user_tickets(user_id: int, limit: int = 10):
    rows = await fetch(
        "SELECT * FROM tickets WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        int(user_id), int(limit),
    )
    return [_d(r) for r in rows]
