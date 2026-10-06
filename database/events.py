# ==========================================
# Events — ایونت‌های موقت با ضریب XP / سکه
# ==========================================

from datetime import datetime, timezone, timedelta
from .pool import fetch, fetchrow, execute, fetchval
import json


def _d(row):
    return dict(row) if row else None


async def get_active_events():
    rows = await fetch(
        """
        SELECT * FROM events
        WHERE active = TRUE
          AND (end_at IS NULL OR end_at > NOW())
          AND (start_at IS NULL OR start_at <= NOW())
        ORDER BY start_at DESC NULLS LAST
        """
    )
    return [_d(r) for r in rows]


async def list_all_events(limit: int = 30):
    rows = await fetch(
        "SELECT * FROM events ORDER BY id DESC LIMIT $1", int(limit)
    )
    return [_d(r) for r in rows]


async def get_event(event_id: int):
    return _d(await fetchrow("SELECT * FROM events WHERE id = $1", int(event_id)))


async def create_event(
    name,
    description,
    start_at,
    end_at,
    bonus_xp=1.0,
    bonus_coin=1.0,
    special_item=None,
    created_by=None,
):
    row = await fetchrow(
        """
        INSERT INTO events (
            name, description, start_at, end_at,
            bonus_xp, bonus_coin, special_item, active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
        RETURNING *
        """,
        name,
        description or "",
        start_at,
        end_at,
        float(bonus_xp),
        float(bonus_coin),
        special_item,
    )
    return _d(row)


async def end_event(event_id: int):
    await execute(
        "UPDATE events SET active = FALSE WHERE id = $1",
        int(event_id),
    )
    return await get_event(event_id)


async def activate_event(event_id: int):
    await execute(
        "UPDATE events SET active = TRUE WHERE id = $1",
        int(event_id),
    )
    return await get_event(event_id)


async def delete_event(event_id: int):
    await execute("DELETE FROM events WHERE id = $1", int(event_id))


async def update_event(event_id: int, **fields):
    allowed = {
        "name", "description", "bonus_xp", "bonus_coin",
        "special_item", "active", "start_at", "end_at",
    }
    sets, args, i = [], [int(event_id)], 2
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ${i}")
            args.append(v)
            i += 1
    if not sets:
        return await get_event(event_id)
    await execute(
        f"UPDATE events SET {', '.join(sets)} WHERE id = $1",
        *args,
    )
    return await get_event(event_id)


async def get_combined_multipliers() -> dict:
    """
    ضرب‌کننده‌های تجمیعی همه ایونت‌های فعال.
    اگر چند ایونت هم‌زمان باشد، ضرایب در هم ضرب می‌شوند.
    """
    events = await get_active_events()
    xp = 1.0
    coin = 1.0
    names = []
    for e in events or []:
        try:
            xp *= float(e.get("bonus_xp") or 1.0)
        except Exception:
            pass
        try:
            coin *= float(e.get("bonus_coin") or 1.0)
        except Exception:
            pass
        if e.get("name"):
            names.append(str(e["name"]))
    return {
        "xp": max(0.1, float(xp)),
        "coin": max(0.1, float(coin)),
        "events": events or [],
        "names": names,
        "active": bool(events),
    }


async def apply_xp_bonus(base_amount: int) -> tuple:
    """برمی‌گرداند (مقدار_نهایی, ضریب, توضیح)"""
    m = await get_combined_multipliers()
    base = int(base_amount or 0)
    if base <= 0:
        return 0, m["xp"], ""
    final = max(1, int(round(base * m["xp"]))) if m["active"] and m["xp"] != 1.0 else base
    if m["active"] and m["xp"] != 1.0:
        note = f"🎉 ایونت ×{m['xp']:g}"
        if m["names"]:
            note += f" ({', '.join(m['names'][:2])})"
        return final, m["xp"], note
    return base, 1.0, ""


async def apply_coin_bonus(base_amount: int) -> tuple:
    m = await get_combined_multipliers()
    base = int(base_amount or 0)
    if base <= 0:
        return 0, m["coin"], ""
    final = max(1, int(round(base * m["coin"]))) if m["active"] and m["coin"] != 1.0 else base
    if m["active"] and m["coin"] != 1.0:
        note = f"🎉 ایونت ×{m['coin']:g}"
        if m["names"]:
            note += f" ({', '.join(m['names'][:2])})"
        return final, m["coin"], note
    return base, 1.0, ""


async def events_status_text() -> str:
    m = await get_combined_multipliers()
    if not m["active"]:
        return "🎉 ایونت فعالی نیست."
    lines = ["🎉 **ایونت‌های فعال**", "━━━━━━━━━━━━━━"]
    for e in m["events"]:
        lines.append(
            f"• **{e.get('name')}**\n"
            f"  XP ×`{e.get('bonus_xp')}` | سکه ×`{e.get('bonus_coin')}`\n"
            f"  تا: `{e.get('end_at')}`"
        )
    lines.append(
        f"\n📊 ضریب کل: XP ×`{m['xp']:g}` | سکه ×`{m['coin']:g}`"
    )
    return "\n".join(lines)
