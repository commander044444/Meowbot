# ==========================================
# مدیریت کامل کاربران (لیست + بن + اقتصاد + لاگ)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.users import (
    get_user, get_all_users, count_users,
    admin_set_meow_coins, admin_set_meow_points, admin_set_gym_level,
)
from database.bans import ban_user, unban_user, get_active_ban, ban_message_text, is_banned
from database.logs import get_recent_logs, log_action
from database.pool import fetch, fetchval
from database.pets import get_pet

_pending = {}  # admin_id -> {action, target_id, ...}


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


def back_users():
    return _kb([[("🔙 لیست کاربران", "um:list:0")], [("🔙 منوی Owner", "owner:home")]])


async def users_list_page(page: int = 0, per_page: int = 8):
    total = await count_users()
    offset = page * per_page
    rows = await fetch(
        "SELECT user_id, first_name, username, meow_coins, meow_points "
        "FROM users ORDER BY user_id DESC LIMIT $1 OFFSET $2",
        per_page, offset,
    )
    lines = [
        f"👥 **لیست کاربران** (`{total}`)",
        "━━━━━━━━━━━━━━",
        "یک کاربر را انتخاب کن:",
    ]
    btn_rows = []
    for r in rows or []:
        name = (r["first_name"] or str(r["user_id"]))[:16]
        ban = "🚫" if await is_banned(r["user_id"]) else ""
        btn_rows.append([(f"{ban}{name} `{r['user_id']}`", f"um:user:{r['user_id']}")])
    nav = []
    if page > 0:
        nav.append(("◀️ قبل", f"um:list:{page-1}"))
    if offset + per_page < total:
        nav.append(("بعد ▶️", f"um:list:{page+1}"))
    if nav:
        btn_rows.append(nav)
    btn_rows.append([("🔙 منوی Owner", "owner:home")])
    return "\n".join(lines), _kb(btn_rows)


async def user_card(target_id: int):
    u = await get_user(target_id)
    if not u:
        return "❌ کاربر پیدا نشد.", back_users()
    ban = await get_active_ban(target_id)
    pet = await get_pet(target_id)
    # daily meows today
    from datetime import datetime
    from zoneinfo import ZoneInfo
    day = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d")
    daily = await fetchval(
        "SELECT meow_count FROM daily_meow_stats WHERE user_id = $1 AND day_date = $2",
        int(target_id), day,
    )
    ban_line = "—"
    if ban:
        dur = "دائمی" if ban.get("is_permanent") else f"{ban.get('duration_days')} روز"
        ban_line = f"🚫 بن | {ban.get('tracking_code')} | {dur} | {ban.get('reason')}"
    pet_line = "ندارد"
    if pet and not pet.get("awaiting_name"):
        pet_line = f"{pet.get('pet_name')} Lv.{pet.get('level')}"
    text = (
        f"👤 **کاربر `{target_id}`**\n"
        f"━━━━━━━━━━━━━━\n"
        f"نام: {u.get('first_name')}\n"
        f"@{u.get('username') or '—'}\n"
        f"🪙 سکه: `{u.get('meow_coins')}`\n"
        f"⭐ امتیاز فصل: `{u.get('meow_points')}`\n"
        f"🏋️ باشگاه: `{u.get('gym_level')}`\n"
        f"🐱 کل میو: `{u.get('total_meows')}`\n"
        f"📅 میو امروز: `{int(daily or 0)}`\n"
        f"⚔️ W/L: `{u.get('total_wins')}/{u.get('total_losses')}`\n"
        f"🐾 Pet: {pet_line}\n"
        f"🚫 وضعیت بن: {ban_line}\n"
        f"━━━━━━━━━━━━━━"
    )
    kb = _kb([
        [("🪙 +سکه", f"um:coin_add:{target_id}"), ("🪙 −سکه", f"um:coin_sub:{target_id}")],
        [("⭐ +امتیاز", f"um:pt_add:{target_id}"), ("⭐ −امتیاز", f"um:pt_sub:{target_id}")],
        [("🏋️ Gym", f"um:gym:{target_id}"), ("📜 لاگ", f"um:logs:{target_id}")],
        [("💬 پیام شخصی", f"um:msg:{target_id}")],
        [("🚫 بن", f"um:ban:{target_id}"), ("✅ آنبن", f"um:unban:{target_id}")],
        [("🔙 لیست", "um:list:0"), ("🔙 Owner", "owner:home")],
    ])
    return text, kb


async def handle_um_callback(bot, callback, data: str, admin_id: int):
    parts = data.split(":")
    # um:list:0 | um:user:ID | um:coin_add:ID | um:ban:ID | ...
    cmd = parts[1] if len(parts) > 1 else ""

    if cmd == "list":
        page = int(parts[2]) if len(parts) > 2 else 0
        text, kb = await users_list_page(page)
        return text, kb

    if cmd == "user" and len(parts) > 2:
        return await user_card(int(parts[2]))

    if cmd == "unban" and len(parts) > 2:
        tid = int(parts[2])
        await unban_user(tid, admin_id)
        await log_action(admin_id, "unban", str(tid))
        try:
            await bot.send_message(
                tid,
                "✅ بن شما توسط مدیریت برداشته شد.\nاکنون به تمام بخش‌های ربات دسترسی دارید.",
            )
        except Exception:
            pass
        return await user_card(tid)

    if cmd == "logs" and len(parts) > 2:
        tid = int(parts[2])
        logs = await get_recent_logs(15, actor_id=None)
        # filter related
        lines = [f"📜 لاگ مرتبط با `{tid}`\n━━━━━━━━━━━━━━"]
        found = 0
        for lg in logs or []:
            if str(lg.get("target")) == str(tid) or str(lg.get("actor_id")) == str(tid):
                lines.append(f"• {lg.get('action')} by `{lg.get('actor_id')}` → {lg.get('result')}")
                found += 1
        if not found:
            lines.append("موردی در لاگ‌های اخیر نیست.")
        return "\n".join(lines), _kb([[("🔙 کاربر", f"um:user:{tid}")]])

    # actions that need text input
    need_input = {
        "coin_add": "مقدار سکه برای **اضافه** را بفرست:",
        "coin_sub": "مقدار سکه برای **کم** را بفرست:",
        "pt_add": "مقدار امتیاز برای **اضافه** را بفرست:",
        "pt_sub": "مقدار امتیاز برای **کم** را بفرست:",
        "gym": "سطح جدید باشگاه را بفرست (عدد):",
        "msg": "متن پیام شخصی به کاربر را بفرست:",
        "ban": None,  # multi-step
    }
    if cmd in need_input and len(parts) > 2:
        tid = int(parts[2])
        if cmd == "ban":
            _pending[admin_id] = {"action": "ban_days", "target_id": tid}
            return (
                f"🚫 **بن کاربر `{tid}`**\n"
                f"مدت را انتخاب کن یا عدد روز را بفرست:\n"
                f"(یا دکمه بدون‌پایان)",
                _kb([
                    [("۱ روز", f"um:ban_d:{tid}:1"), ("۳ روز", f"um:ban_d:{tid}:3")],
                    [("۷ روز", f"um:ban_d:{tid}:7"), ("۳۰ روز", f"um:ban_d:{tid}:30")],
                    [("♾ بدون پایان", f"um:ban_d:{tid}:0")],
                    [("❌ لغو", f"um:user:{tid}")],
                ]),
            )
        _pending[admin_id] = {"action": cmd, "target_id": tid}
        return need_input[cmd] + "\n\nلغو: `لغو`", back_users()

    if cmd == "ban_d" and len(parts) > 3:
        tid = int(parts[2])
        days = int(parts[3])
        permanent = days == 0
        _pending[admin_id] = {
            "action": "ban_reason",
            "target_id": tid,
            "days": days,
            "permanent": permanent,
        }
        return (
            f"دلیل بن را بفرست (کوتاه):\nمثال: اسپم / توهین / تقلب\n\nلغو: `لغو`",
            back_users(),
        )

    return "❓", back_users()


async def handle_um_text(bot, message, admin_id: int, text: str) -> bool:
    p = _pending.get(admin_id)
    if not p:
        return False
    text = (text or "").strip()
    if text in ("لغو", "cancel", "/cancel"):
        _pending.pop(admin_id, None)
        await message.reply("✅ لغو شد.")
        return True

    action = p.get("action")
    tid = int(p.get("target_id"))

    try:
        if action in ("coin_add", "coin_sub", "pt_add", "pt_sub", "gym"):
            val = int(text.split()[0])
            u = await get_user(tid)
            if not u:
                await message.reply("❌ کاربر نیست.")
                _pending.pop(admin_id, None)
                return True
            if action == "coin_add":
                old = int(u.get("meow_coins") or 0)
                await admin_set_meow_coins(tid, old + val)
                field = f"🪙 {old} → {old+val}"
            elif action == "coin_sub":
                old = int(u.get("meow_coins") or 0)
                await admin_set_meow_coins(tid, max(0, old - val))
                field = f"🪙 {old} → {max(0, old-val)}"
            elif action == "pt_add":
                old = int(u.get("meow_points") or 0)
                await admin_set_meow_points(tid, old + val)
                field = f"⭐ {old} → {old+val}"
            elif action == "pt_sub":
                old = int(u.get("meow_points") or 0)
                await admin_set_meow_points(tid, max(0, old - val))
                field = f"⭐ {old} → {max(0, old-val)}"
            else:
                ok, o, n = await admin_set_gym_level(tid, val)
                field = f"🏋️ {o} → {n}"
            await log_action(admin_id, action, str(tid), {"value": val})
            _pending.pop(admin_id, None)
            card, kb = await user_card(tid)
            await message.reply(f"✅ {field}\n\n{card}", components=kb)
            return True

        if action == "msg":
            body = (
                "📨 **این یک پیام شخصی از طرف مدیریت به شماست**\n"
                "━━━━━━━━━━━━━━\n"
                f"{text}"
            )
            try:
                await bot.send_message(tid, body)
                await log_action(admin_id, "admin_msg", str(tid))
                await message.reply(f"✅ پیام به `{tid}` ارسال شد.")
            except Exception as e:
                await message.reply(f"❌ ارسال نشد: `{e}`")
            _pending.pop(admin_id, None)
            return True

        if action == "ban_reason":
            p["reason"] = text
            p["action"] = "ban_desc"
            _pending[admin_id] = p
            await message.reply("توضیحات کامل‌تر را بفرست (یا `-` برای خالی):")
            return True

        if action == "ban_desc":
            desc = "" if text == "-" else text
            permanent = bool(p.get("permanent"))
            days = p.get("days") or 0
            ban = await ban_user(
                tid,
                banned_by=admin_id,
                reason=p.get("reason") or "تخلف",
                description=desc,
                duration_days=None if permanent else days,
                permanent=permanent,
            )
            await log_action(admin_id, "ban", str(tid), {
                "code": ban.get("tracking_code"),
                "days": days,
                "permanent": permanent,
            })
            u = await get_user(tid)
            name = (u or {}).get("first_name") or str(tid)
            msg = await ban_message_text(ban, name)
            try:
                await bot.send_message(tid, msg)
            except Exception:
                pass
            _pending.pop(admin_id, None)
            card, kb = await user_card(tid)
            await message.reply(
                f"✅ کاربر بن شد.\nکد: `{ban.get('tracking_code')}`\n\n{card}",
                components=kb,
            )
            return True

    except Exception as e:
        await message.reply(f"⚠️ `{e}`")
        _pending.pop(admin_id, None)
        return True

    return False


def has_um_pending(admin_id: int) -> bool:
    return admin_id in _pending
