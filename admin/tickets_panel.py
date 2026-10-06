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


async def tickets_home(back_cb: str = "adm:home"):
    """لیست تیکت‌ها. back_cb برای بازگشت (adm:home یا owner:home)."""
    global _tickets_back
    try:
        _tickets_back = back_cb or "adm:home"
    except Exception:
        pass
    n = await count_open_tickets()
    text = (
        f"🎫 **تیکت‌های پشتیبانی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"باز: `{n}`\n"
        f"یک تیکت را انتخاب کن."
    )
    tickets = await list_tickets("open", 20)
    rows = []
    for tk in tickets or []:
        preview = (tk.get("body") or "")[:28].replace("\n", " ")
        rows.append([(f"🟢 #{tk['id']} | {tk['user_id']} {preview}", f"tk:view:{tk['id']}")])
    rows.append([("📋 همه", "tk:list:all"), ("🟢 بازها", "tk:list:open")])
    b = back_cb or "adm:home"
    label = "🔙 داشبورد ادمین" if str(b).startswith("adm:") else "🔙 منوی Owner"
    rows.append([(label, b)])
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
        tid = int(parts[2])
        try:
            await log_action(admin_id, "ticket_view", str(tid))
        except Exception:
            pass
        return await view_ticket(tid)
    if cmd == "close" and len(parts) > 2:
        tid = int(parts[2])
        trow = await get_ticket(tid)
        # اگر قبلاً بسته شده، دوباره XP نده
        already = (trow or {}).get("status") == "closed"
        await close_ticket(tid)
        await log_action(admin_id, "ticket_close", str(tid))
        reward_note = ""
        if not already:
            try:
                from database.admin_system import record_admin_activity, ensure_admin_system_schema
                try:
                    await ensure_admin_system_schema()
                except Exception:
                    pass
                # مطمئن شو تسک تیکت روشن است
                from database.pool import execute as _ex
                await _ex(
                    "UPDATE admin_tasks SET enabled = TRUE WHERE task_key = 'ticket_handle'"
                )
                result = await record_admin_activity(
                    admin_id, "ticket_close",
                    target=str(tid),
                    unique_key=f"ticket_close:{tid}",
                    metadata={"user_id": (trow or {}).get("user_id")},
                )
                xp = (result or {}).get("xp") or 0
                meow = (result or {}).get("meow") or 0
                # progress فعلی تسک
                try:
                    from database.admin_system import list_admin_task_progress
                    items = await list_admin_task_progress(admin_id)
                    for it in items or []:
                        if it.get("task_key") == "ticket_handle" or it.get("activity_type") == "ticket_close":
                            prog = it.get("progress") or 0
                            target = it.get("target") or 1
                            reward_note = f"\n\n📋 تسک تیکت: `{prog}/{target}`"
                            if it.get("completed"):
                                reward_note += " ✅ تکمیل شد!"
                            break
                except Exception:
                    pass
                if xp or meow:
                    reward_note += f"\n🎁 +{xp} Admin XP | +{meow}🪙"
            except Exception as e:
                print(f"activity ticket_close: {e}")
                reward_note = f"\n⚠️ ثبت تسک: `{e}`"
        else:
            reward_note = "\n_(قبلاً بسته شده بود — امتیاز تکراری نیست)_"
        home_text, home_kb = await tickets_home()
        return f"✅ تیکت `#{tid}` بسته/حل شد.{reward_note}\n\n{home_text}", home_kb
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
