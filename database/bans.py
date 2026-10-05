# ==========================================
# Ban system
# ==========================================

from datetime import datetime, timedelta, timezone
from .pool import fetch, fetchrow, execute, fetchval


def _d(row):
    return dict(row) if row else None


async def next_tracking_code() -> str:
    """کد پیگیری غیررندوم بر اساس sequence."""
    n = await fetchval("SELECT COALESCE(MAX(id), 0) + 1 FROM bans")
    return f"#{int(n or 1) + 5400}"  # مثلاً از #5401 به بالا


async def ban_user(
    user_id: int,
    banned_by: int,
    reason: str = "",
    description: str = "",
    duration_days: int = None,
    permanent: bool = False,
):
    # deactivate old bans
    await execute(
        "UPDATE bans SET active = FALSE WHERE user_id = $1 AND active = TRUE",
        int(user_id),
    )
    code = await next_tracking_code()
    ends_at = None
    if not permanent and duration_days:
        ends_at = datetime.now(timezone.utc) + timedelta(days=int(duration_days))
    row = await fetchrow(
        """
        INSERT INTO bans (
            user_id, tracking_code, reason, description,
            duration_days, is_permanent, banned_by, ends_at, active
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8, TRUE)
        RETURNING *
        """,
        int(user_id), code, reason or "", description or "",
        None if permanent else int(duration_days or 0),
        bool(permanent), int(banned_by), ends_at,
    )
    return _d(row)


async def unban_user(user_id: int, by_admin: int = None) -> bool:
    await execute(
        "UPDATE bans SET active = FALSE WHERE user_id = $1 AND active = TRUE",
        int(user_id),
    )
    return True


async def get_active_ban(user_id: int):
    row = await fetchrow(
        """
        SELECT * FROM bans
        WHERE user_id = $1 AND active = TRUE
        ORDER BY created_at DESC LIMIT 1
        """,
        int(user_id),
    )
    if not row:
        return None
    b = _d(row)
    # expire check
    if not b.get("is_permanent") and b.get("ends_at"):
        ends = b["ends_at"]
        now = datetime.now(timezone.utc)
        if hasattr(ends, "tzinfo") and ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        if ends < now:
            await execute("UPDATE bans SET active = FALSE WHERE id = $1", b["id"])
            return None
    return b


async def is_banned(user_id: int) -> bool:
    return (await get_active_ban(user_id)) is not None


async def ban_message_text(ban: dict, user_name: str = "") -> str:
    name = user_name or str(ban.get("user_id"))
    if ban.get("is_permanent"):
        dur = "بدون پایان (دائمی)"
    else:
        days = ban.get("duration_days") or 0
        dur = f"{days} روز"
    return (
        f"🚫 **اعلان بن**\n"
        f"━━━━━━━━━━━━━━\n"
        f"کاربر **{name}** شما متأسفانه به دلیل **{ban.get('reason') or 'تخلف'}** "
        f"توسط مدیریت بن شده‌اید.\n\n"
        f"⏱ مدت: **{dur}**\n"
        f"📝 توضیحات: {ban.get('description') or '—'}\n"
        f"🔖 کد پیگیری: `{ban.get('tracking_code')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"در این مدت فقط و فقط به بخش **🎫 تیکت پشتیبانی** دسترسی دارید."
    )
