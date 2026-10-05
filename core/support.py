# ==========================================
# پشتیبانی کاربر (به‌ویژه هنگام بن)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.tickets import create_ticket, user_tickets
from database.bans import get_active_ban
from database.admins import list_admins
from config import OWNER_ID

_pending = {}


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


def support_kb():
    return _kb([
        [("🎫 ارسال تیکت پشتیبانی", "sup:new")],
        [("📋 تیکت‌های من", "sup:mine")],
        [("ℹ️ وضعیت بن من", "sup:ban_status")],
    ])


def support_home_text(ban=None):
    lines = [
        "🎫 **پشتیبانی و مدیریت**",
        "━━━━━━━━━━━━━━",
        "از این بخش می‌توانی برای مدیریت تیکت بفرستی.",
    ]
    if ban:
        lines.append(
            f"\n🚫 شما بن هستید.\nکد پیگیری: `{ban.get('tracking_code')}`\n"
            f"دلیل: {ban.get('reason') or '—'}"
        )
    return "\n".join(lines)


async def handle_sup_callback(bot, user_id, data):
    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "home"
    ban = await get_active_ban(user_id)
    if cmd == "home":
        return support_home_text(ban), support_kb()
    if cmd == "ban_status":
        if not ban:
            return "✅ در حال حاضر بن نیستید.", support_kb()
        dur = "دائمی" if ban.get("is_permanent") else f"{ban.get('duration_days')} روز"
        return (
            f"🚫 وضعیت بن\nکد: `{ban.get('tracking_code')}`\n"
            f"دلیل: {ban.get('reason')}\nمدت: {dur}\n"
            f"{ban.get('description') or ''}",
            support_kb(),
        )
    if cmd == "mine":
        tks = await user_tickets(user_id, 10)
        lines = ["📋 **تیکت‌های شما**\n━━━━━━━━━━━━━━"]
        if not tks:
            lines.append("تیکتی ندارید.")
        for t in tks:
            lines.append(
                f"• #{t['id']} `{t.get('status')}`\n  {(t.get('body') or '')[:40]}\n"
                f"  پاسخ: {(t.get('admin_reply') or '—')[:40]}"
            )
        return "\n".join(lines), support_kb()
    if cmd == "new":
        _pending[user_id] = True
        return (
            "🎫 متن تیکت خود را بنویس (مشکل / درخواست):\n"
            "لغو: `لغو`",
            _kb([[("❌ لغو", "sup:home")]]),
        )
    return support_home_text(ban), support_kb()


async def handle_sup_text(bot, message, user_id, text) -> bool:
    if not _pending.get(user_id):
        return False
    if text.strip() in ("لغو", "cancel"):
        _pending.pop(user_id, None)
        await message.reply("لغو شد.", components=support_kb())
        return True
    ban = await get_active_ban(user_id)
    code = (ban or {}).get("tracking_code") or ""
    t = await create_ticket(user_id, text, subject="پشتیبانی کاربر", tracking_code=code)
    _pending.pop(user_id, None)
    # notify admins
    notify = (
        f"🎫 **تیکت جدید #{t['id']}**\n"
        f"از کاربر `{user_id}`\n"
        f"کد بن: `{code or '—'}`\n"
        f"━━━━━━━━━━━━━━\n{text[:800]}"
    )
    targets = {int(OWNER_ID)}
    try:
        for a in await list_admins() or []:
            if a.get("enabled"):
                targets.add(int(a["user_id"]))
    except Exception:
        pass
    for aid in targets:
        try:
            await bot.send_message(
                aid,
                notify,
                components=_kb([[("🎫 باز کردن", f"tk:view:{t['id']}")]]),
            )
        except Exception:
            pass
    await message.reply(
        f"✅ تیکت **#{t['id']}** ثبت شد.\nمدیریت پاسخ خواهد داد.",
        components=support_kb(),
    )
    return True


def is_sup_pending(user_id: int) -> bool:
    return bool(_pending.get(user_id))
