# ==========================================
# تیکت‌های پشتیبانی (ادمین)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.tickets import (
    list_tickets, get_ticket, reply_ticket, close_ticket, count_open_tickets,
)
from database.logs import log_action
from database.users import get_user

_pending = {}
_tickets_back = "adm:home"  # default back target


def _kb(rows):
    kb = InlineKeyboardMarkup()
    rn = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(InlineKeyboardButton(text=str(text), callback_data=str(data)), row=rn)
        rn += 1
    return kb


async def tickets_home():
    n = await count_open_tickets()
    text = (
        f"🎫 **تیکت‌های پشتیبانی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"باز: `{n}`\n"
        f"یک تیکت را انتخاب کن."
    )
    tickets = await list_tickets("open", 20)
    rows = []
    for t in tickets or []:
        preview = (t.get("body") or "")[:28].replace("\n", " ")
        rows.append([(f"🟢 #{t['id']} | `{t['user_id']}` {preview}", f"tk:view:{t['id']}")])
    rows.append([("📋 همه", "tk:list:all"), ("🟢 بازها", "tk:list:open")])
    rows.append([("🔙 منوی Owner", "owner:home")])
    return text, _kb(rows)


async def view_ticket(ticket_id: int):
    t = await get_ticket(ticket_id)
    if not t:
        return "❌ تیکت پیدا نشد.", _kb([[("🔙", "tk:home")]])
    u = await get_user(t["user_id"])
    name = (u or {}).get("first_name") or ""
    text = (
        f"🎫 **تیکت #{t['id']}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"وضعیت: `{t.get('status')}`\n"
        f"👤 کاربر: {name} (`{t['user_id']}`)\n"
        f"@{ (u or {}).get('username') or '—' }\n"
        f"کد بن: `{t.get('tracking_code') or '—'}`\n"
        f"موضوع: {t.get('subject')}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{t.get('body')}\n"
        f"━━━━━━━━━━━━━━\n"
        f"پاسخ ادمین: {t.get('admin_reply') or '—'}"
    )
    kb = _kb([
        [("💬 پاسخ", f"tk:reply:{ticket_id}"), ("✅ بستن", f"tk:close:{ticket_id}")],
        [("🔙 لیست", "tk:home")],
    ])
    return text, kb


async def handle_tk_callback(bot, data: str, admin_id: int):
    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "home"
    if cmd == "home":
        return await tickets_home()
    if cmd == "list":
        st = parts[2] if len(parts) > 2 else "open"
        tickets = await list_tickets(st, 25)
        lines = [f"🎫 تیکت‌ها ({st})\n━━━━━━━━━━━━━━"]
        rows = []
        for t in tickets or []:
            rows.append([(f"#{t['id']} `{t['user_id']}` {t.get('status')}", f"tk:view:{t['id']}")])
        if not tickets:
            lines.append("خالی")
        rows.append([("🔙", "tk:home")])
        # keep back
        return "\n".join(lines), _kb(rows)
    if cmd == "view" and len(parts) > 2:
        return await view_ticket(int(parts[2]))
    if cmd == "close" and len(parts) > 2:
        tid = int(parts[2])
        trow = await get_ticket(tid)
        await close_ticket(tid)
        await log_action(admin_id, "ticket_close", str(tid))
        try:
            from database.admin_system import record_admin_activity
            await record_admin_activity(
                admin_id, "ticket_close",
                target=str(tid),
                unique_key=f"ticket_close:{tid}",
                metadata={"user_id": (trow or {}).get("user_id")},
            )
        except Exception as e:
            print(f"activity ticket_close: {e}")
        return await tickets_home()
    if cmd == "reply" and len(parts) > 2:
        _pending[admin_id] = {"action": "reply", "ticket_id": int(parts[2])}
        return "متن پاسخ به کاربر را بفرست:\nلغو: `لغو`", _kb([[("❌ لغو", "tk:home")]])
    return await tickets_home()


async def handle_tk_text(bot, message, admin_id: int, text: str) -> bool:
    p = _pending.get(admin_id)
    if not p:
        return False
    if text.strip() in ("لغو", "cancel"):
        _pending.pop(admin_id, None)
        await message.reply("لغو شد.")
        return True
    if p.get("action") == "reply":
        tid = int(p["ticket_id"])
        t = await reply_ticket(tid, admin_id, text)
        await log_action(admin_id, "ticket_reply", str(tid))
        try:
            from database.admin_system import record_admin_activity
            await record_admin_activity(
                admin_id, "ticket_close",
                target=str(tid),
                unique_key=f"ticket_reply:{tid}:{hash(text) % 10**8}",
                metadata={"reply": True},
            )
        except Exception as e:
            print(f"activity ticket_reply: {e}")
        try:
            await bot.send_message(
                int(t["user_id"]),
                f"🎫 **پاسخ پشتیبانی به تیکت #{tid}**\n"
                f"━━━━━━━━━━━━━━\n"
                f"{text}",
            )
        except Exception:
            pass
        _pending.pop(admin_id, None)
        await message.reply(f"✅ پاسخ تیکت #{tid} ارسال شد.")
        return True
    return False


def has_tk_pending(admin_id: int) -> bool:
    return admin_id in _pending
