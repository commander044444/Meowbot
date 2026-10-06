# ==========================================
# Owner: مدیریت کامل ایونت‌ها
# ==========================================

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.events import (
    get_active_events, list_all_events, get_event, create_event,
    end_event, activate_event, delete_event, update_event,
    get_combined_multipliers, events_status_text,
)
from database.logs import log_action

TEHRAN = ZoneInfo("Asia/Tehran")
_pending = {}


def _kb(rows):
    kb = InlineKeyboardMarkup()
    rn = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(InlineKeyboardButton(text=str(text)[:64], callback_data=str(data)[:64]), row=rn)
        rn += 1
    return kb


async def events_home():
    m = await get_combined_multipliers()
    lines = [
        "🎉 **مدیریت ایونت‌ها**",
        "━━━━━━━━━━━━━━",
        "ایونت = رویداد موقت با ضریب بیشتر روی XP و سکه.",
        "",
    ]
    if m["active"]:
        lines.append(f"🟢 فعال: {', '.join(m['names']) or '—'}")
        lines.append(f"📊 ضریب کل: XP ×`{m['xp']:g}` | سکه ×`{m['coin']:g}`")
    else:
        lines.append("⚪ الان ایونت فعالی نیست.")
    lines.append("")
    lines.append("لیست:")
    all_e = await list_all_events(15)
    rows = []
    for e in all_e or []:
        st = "🟢" if e.get("active") else "⏸"
        rows.append([(
            f"{st} {e.get('name')} ×{e.get('bonus_xp')}/×{e.get('bonus_coin')}",
            f"ev:view:{e['id']}",
        )])
    if not all_e:
        lines.append("هنوز ایونتی ساخته نشده.")
    rows.append([("➕ ساخت ایونت", "ev:new")])
    rows.append([("📢 وضعیت برای کاربران", "ev:status")])
    rows.append([("🔙 Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def view_event(eid: int):
    e = await get_event(eid)
    if not e:
        return "❌ ایونت پیدا نشد.", await events_home()
    text = (
        f"🎉 **{e.get('name')}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"ID: `{e.get('id')}`\n"
        f"توضیح: {e.get('description') or '—'}\n"
        f"XP × `{e.get('bonus_xp')}`\n"
        f"سکه × `{e.get('bonus_coin')}`\n"
        f"شروع: `{e.get('start_at')}`\n"
        f"پایان: `{e.get('end_at')}`\n"
        f"وضعیت: {'🟢 فعال' if e.get('active') else '⏸ خاموش'}\n\n"
        f"این ضرایب روی میو، بازی و نبرد اعمال می‌شوند."
    )
    rows = []
    if e.get("active"):
        rows.append([("⏸ پایان ایونت", f"ev:end:{eid}")])
    else:
        rows.append([("▶️ فعال‌سازی", f"ev:on:{eid}")])
    rows.append([
        ("✏️ XP", f"ev:set:{eid}:xp"),
        ("✏️ سکه", f"ev:set:{eid}:coin"),
    ])
    rows.append([("🗑 حذف", f"ev:delask:{eid}")])
    rows.append([("🔙 لیست", "ev:home")])
    return text, _kb(rows)


async def handle_ev_callback(data: str, owner_id: int):
    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "home"

    if cmd == "home":
        return await events_home()
    if cmd == "status":
        text = await events_status_text()
        return text, _kb([[("🔙", "ev:home")]])
    if cmd == "view" and len(parts) > 2:
        return await view_event(int(parts[2]))
    if cmd == "end" and len(parts) > 2:
        await end_event(int(parts[2]))
        await log_action(owner_id, "event_end", parts[2])
        return "✅ ایونت پایان یافت.", await view_event(int(parts[2]))
    if cmd == "on" and len(parts) > 2:
        await activate_event(int(parts[2]))
        await log_action(owner_id, "event_on", parts[2])
        return "✅ ایونت فعال شد.", await view_event(int(parts[2]))
    if cmd == "delask" and len(parts) > 2:
        eid = int(parts[2])
        return (
            "⚠️ حذف دائمی این ایونت؟",
            _kb([[("🗑 بله حذف", f"ev:del:{eid}"), ("❌ لغو", f"ev:view:{eid}")]]),
        )
    if cmd == "del" and len(parts) > 2:
        await delete_event(int(parts[2]))
        await log_action(owner_id, "event_delete", parts[2])
        return "✅ حذف شد.", await events_home()
    if cmd == "set" and len(parts) > 3:
        eid, field = int(parts[2]), parts[3]
        _pending[owner_id] = {"action": "ev_set", "id": eid, "field": field}
        hint = "ضریب XP جدید (مثلاً 1.5):" if field == "xp" else "ضریب سکه جدید (مثلاً 2):"
        return hint, _kb([[("❌ لغو", f"ev:view:{eid}")]])
    if cmd == "new":
        _pending[owner_id] = {"action": "ev_create"}
        return (
            "➕ **ساخت ایونت**\n"
            "فرمت:\n"
            "`نام | روز | xp_mult | coin_mult`\n\n"
            "مثال:\n"
            "`جشن میو | 3 | 1.5 | 2`\n\n"
            "یعنی ۳ روز، XP یک‌ونیم‌برابر، سکه دوبرابر.",
            _kb([[("❌ لغو", "ev:home")]]),
        )
    return await events_home()


async def handle_ev_text(message, owner_id: int, text: str) -> bool:
    p = _pending.get(owner_id)
    if not p:
        return False
    text = (text or "").strip()
    if text in ("لغو", "cancel", "/cancel"):
        _pending.pop(owner_id, None)
        await message.reply("لغو شد.")
        return True

    if p.get("action") == "ev_set":
        eid, field = p["id"], p["field"]
        try:
            val = float(text.replace(",", "."))
            if val < 0.1 or val > 20:
                await message.reply("❌ ضریب باید بین 0.1 تا 20 باشد.")
                return True
            if field == "xp":
                await update_event(eid, bonus_xp=val)
            else:
                await update_event(eid, bonus_coin=val)
            _pending.pop(owner_id, None)
            card, kb = await view_event(eid)
            await message.reply(f"✅ ذخیره شد.\n\n{card}", components=kb)
        except Exception as e:
            await message.reply(f"❌ `{e}`")
        return True

    if p.get("action") == "ev_create":
        parts = [x.strip() for x in text.split("|")]
        if len(parts) < 1 or not parts[0]:
            await message.reply("❌ نام را بنویس.")
            return True
        name = parts[0]
        try:
            days = int(parts[1]) if len(parts) > 1 else 1
        except Exception:
            days = 1
        try:
            xp_m = float(parts[2].replace(",", ".")) if len(parts) > 2 else 1.5
        except Exception:
            xp_m = 1.5
        try:
            coin_m = float(parts[3].replace(",", ".")) if len(parts) > 3 else 2.0
        except Exception:
            coin_m = 2.0
        days = max(1, min(days, 90))
        xp_m = max(0.1, min(xp_m, 20))
        coin_m = max(0.1, min(coin_m, 20))
        start = datetime.now(TEHRAN)
        end = start + timedelta(days=days)
        e = await create_event(
            name,
            f"ایونت {days} روزه | XP×{xp_m} سکه×{coin_m}",
            start, end, xp_m, coin_m,
        )
        await log_action(owner_id, "event_create", name, {"xp": xp_m, "coin": coin_m, "days": days})
        _pending.pop(owner_id, None)
        await message.reply(
            f"✅ ایونت **{name}** ساخته و فعال شد.\n"
            f"⏱ {days} روز\n"
            f"⭐ XP ×`{xp_m}`\n"
            f"🪙 سکه ×`{coin_m}`\n\n"
            f"از الان روی میو / بازی / نبرد اعمال می‌شود."
        )
        return True
    return False


def has_ev_pending(owner_id: int) -> bool:
    return owner_id in _pending
