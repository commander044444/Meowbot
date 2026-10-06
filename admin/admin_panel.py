# ==========================================
# ADMIN PANEL — کاملاً مستقل از Owner Panel
# Personal Workspace برای ادمین‌ها
# دکمه‌ها فقط بر اساس Permission واقعی ساخته می‌شوند
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.admins import is_owner, is_admin, has_permission, get_admin
from database.admin_system import (
    ensure_admin_profile, get_admin_profile, list_admin_task_progress,
    list_notifications, mark_notifications_read, admin_leaderboard,
    recent_admin_activity, list_role_defs, ensure_admin_system_schema,
    get_role_history,
)
from database.tickets import count_open_tickets, list_tickets
from database.reports import count_open_reports
from database.bans import is_banned
from database.users import get_user, count_users


def _kb(rows):
    kb = InlineKeyboardMarkup()
    rn = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(
                InlineKeyboardButton(text=str(text)[:64], callback_data=str(data)[:64]),
                row=rn,
            )
        rn += 1
    return kb


async def _can(uid: int, perm: str) -> bool:
    if await is_owner(uid):
        return True
    return await has_permission(uid, perm)


async def show_admin_panel(message):
    """ورود /admin — فقط Admin Workspace (هرگز Owner Panel)."""
    author = getattr(message, "author", None) or getattr(message, "from_user", None)
    uid = int(getattr(author, "id", 0) or 0)
    if not uid:
        await message.reply("⚠️ کاربر نامشخص.")
        return
    try:
        await ensure_admin_system_schema()
    except Exception as e:
        print(f"admin schema: {e}")
    try:
        owner_ok = await is_owner(uid)
        admin_ok = await is_admin(uid)
    except Exception as e:
        await message.reply(f"⚠️ بررسی دسترسی: `{e}`")
        return
    if not (owner_ok or admin_ok):
        await message.reply(
            "⛔ فقط ادمین‌ها.\n"
            f"آیدی شما: `{uid}`\n"
            "از Owner بخواهید شما را اضافه کند."
        )
        return
    try:
        text, kb = await dashboard(uid)
        await message.reply(text, components=kb)
    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.reply(
            f"⚠️ خطا در داشبورد ادمین:\n`{type(e).__name__}: {e}`"
        )



async def dashboard(uid: int):
    await ensure_admin_profile(uid)
    prof = await get_admin_profile(uid) or {}
    u = await get_user(uid) or {}
    role = prof.get("role_key") or "candidate"
    roles = {r["role_key"]: r for r in await list_role_defs()}
    role_title = (roles.get(role) or {}).get("title") or role
    next_role = None
    for r in await list_role_defs():
        if int(r.get("sort_order") or 0) > int((roles.get(role) or {}).get("sort_order") or 0):
            next_role = r
            break

    lines = [
        "🛡️ **پنل ادمین (Workspace)** — نسخه مستقل",
        "━━━━━━━━━━━━━━",
        f"👤 {u.get('first_name') or uid}",
        f"🎖️ نقش: **{role_title}**",
        f"⭐ Admin XP: `{prof.get('admin_xp') or 0}`",
        f"✅ تسک تکمیل‌شده: `{prof.get('completed_tasks') or 0}`",
        f"📊 فعالیت: `{prof.get('activity_count') or 0}`",
    ]
    if next_role:
        lines.append(
            f"🎯 تا **{next_role.get('title')}**: "
            f"XP `{next_role.get('required_xp')}` | "
            f"تسک `{next_role.get('required_tasks')}`"
        )
    lines.append("━━━━━━━━━━━━━━")
    lines.append("بخش موردنظر را انتخاب کن:")

    rows = []
    # فقط دکمه‌هایی که permission دارند
    rows.append([("📋 تسک‌های من", "adm:tasks"), ("🏆 پیشرفت من", "adm:progress")])
    rows.append([("📊 فعالیت من", "adm:myact"), ("👤 پروفایل ادمین", "adm:profile")])

    row = []
    if await _can(uid, "tickets.manage") or await _can(uid, "tickets.view"):
        n = 0
        try:
            n = await count_open_tickets()
        except Exception:
            pass
        row.append((f"🎫 تیکت‌ها ({n})", "adm:tickets"))
    if await _can(uid, "users.view"):
        row.append(("👥 کاربران", "adm:users"))
    if row:
        rows.append(row)

    row = []
    if await _can(uid, "reports.view") or await _can(uid, "reports.manage"):
        try:
            rn = await count_open_reports()
        except Exception:
            rn = 0
        row.append((f"🚨 گزارش‌ها ({rn})", "adm:reports"))
    if await _can(uid, "groups.view") or await _can(uid, "groups.edit"):
        row.append(("💬 گروه‌ها", "adm:groups"))
    if row:
        rows.append(row)

    if await _can(uid, "broadcast.send"):
        rows.append([("📢 ارسال همگانی", "adm:broadcast")])

    rows.append([("🏅 لیدربورد ادمین", "adm:lb"), ("🔔 اعلان‌ها", "adm:notifs")])
    rows.append([("⚙️ تنظیمات من", "adm:settings"), ("❌ بستن", "adm:close")])
    return "\n".join(lines), _kb(rows)


async def handle_admin_callback(bot, callback, data: str, user_id: int):
    """callbackهای adm: — فقط ادمین."""
    if not (await is_owner(user_id) or await is_admin(user_id)):
        return "⛔ فقط ادمین.", None

    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "home"

    if cmd in ("home", "dash"):
        return await dashboard(user_id)
    if cmd == "close":
        return "👋 پنل ادمین بسته شد.\nبرای بازگشت: `/admin`", None

    if cmd == "tasks":
        return await view_tasks(user_id)
    if cmd == "progress":
        return await view_progress(user_id)
    if cmd == "profile":
        return await view_profile(user_id)
    if cmd == "myact":
        return await view_my_activity(user_id)
    if cmd == "lb":
        period = parts[2] if len(parts) > 2 else "all"
        return await view_leaderboard(period)
    if cmd == "notifs":
        return await view_notifs(user_id)
    if cmd == "settings":
        return (
            "⚙️ **تنظیمات ادمین**\n"
            "نقش و XP از فعالیت واقعی سیستم محاسبه می‌شود.\n"
            "برای تغییر Permission با Owner هماهنگ کن.",
            _kb([[("🔙 داشبورد", "adm:home")]]),
        )

    # gated sections
    if cmd == "tickets":
        if not (await _can(user_id, "tickets.manage") or await _can(user_id, "tickets.view")):
            return "⛔ این بخش برای شما فعال نیست.", await _back_only()
        from admin.tickets_panel import tickets_home
        return await tickets_home(back_cb="adm:home")

    if cmd == "users":
        if not await _can(user_id, "users.view"):
            return "⛔ این بخش برای شما فعال نیست.", await _back_only()
        from admin.users_mgmt import users_list_page
        return await users_list_page(0, back_cb="adm:home")

    if cmd == "reports":
        if not (await _can(user_id, "reports.view") or await _can(user_id, "reports.manage")):
            return "⛔ این بخش برای شما فعال نیست.", await _back_only()
        from core.reports import admin_list_text
        return await admin_list_text("open")

    if cmd == "groups":
        if not (await _can(user_id, "groups.view") or await _can(user_id, "groups.edit")):
            return "⛔ این بخش برای شما فعال نیست.", await _back_only()
        from database.groups import get_all_groups
        groups = await get_all_groups()
        lines = ["💬 **گروه‌ها**\n━━━━━━━━━━━━━━"]
        for g in (groups or [])[:20]:
            lines.append(f"• {g.get('title') or g.get('chat_id')} (`{g.get('chat_id')}`)")
        if not groups:
            lines.append("گروهی ثبت نشده.")
        return "\n".join(lines), _kb([[("🔙 داشبورد", "adm:home")]])

    if cmd == "broadcast":
        if not await _can(user_id, "broadcast.send"):
            return "⛔ این بخش برای شما فعال نیست.", await _back_only()
        return (
            "📢 برای همگانی از پنل Owner استفاده می‌شود اگر مجوز کامل دارید.\n"
            "یا به Owner بگویید Broadcast را برایتان باز کند.\n"
            "(ارسال همگانی سراسری فقط با هماهنگی Owner توصیه می‌شود.)",
            _kb([[("🔙 داشبورد", "adm:home")]]),
        )

    return await dashboard(user_id)


async def _back_only():
    return _kb([[("🔙 داشبورد", "adm:home")]])


async def view_tasks(uid: int):
    items = await list_admin_task_progress(uid)
    lines = ["📋 **تسک‌های فعال من**", "━━━━━━━━━━━━━━"]
    if not items:
        lines.append("تسک فعالی برای شما نیست.\nOwner می‌تواند Built-in Taskها را روشن کند.")
    for t in items:
        target = max(1, int(t.get("target") or 1))
        prog = min(int(t.get("progress") or 0), target)
        pct = int(100 * prog / target)
        filled = pct // 10
        bar = "█" * filled + "░" * (10 - filled)
        st = "✅" if t.get("completed") else "🎯"
        lines.append(
            f"{st} **{t.get('name')}**\n"
            f"`{prog} / {target}` {bar} {pct}%\n"
            f"🎁 +{t.get('xp_reward')} XP | +{t.get('meow_reward')}🪙"
        )
    return "\n".join(lines), _kb([[("🔄 بروزرسانی", "adm:tasks"), ("🔙 داشبورد", "adm:home")]])


async def view_progress(uid: int):
    prof = await ensure_admin_profile(uid)
    roles = await list_role_defs()
    lines = [
        "🏆 **پیشرفت نقش**",
        "━━━━━━━━━━━━━━",
        f"نقش فعلی: `{prof.get('role_key')}`",
        f"XP: `{prof.get('admin_xp')}`",
        f"تسک: `{prof.get('completed_tasks')}`",
        f"فعالیت: `{prof.get('activity_count')}`",
        "",
        "نردبان نقش‌ها:",
    ]
    for r in roles:
        mark = "👉" if r["role_key"] == prof.get("role_key") else "•"
        lines.append(
            f"{mark} **{r.get('title')}** — XP `{r.get('required_xp')}` | "
            f"تسک `{r.get('required_tasks')}` | فعالیت `{r.get('required_activity')}`"
        )
    return "\n".join(lines), _kb([[("🔙 داشبورد", "adm:home")]])


async def view_profile(uid: int):
    prof = await ensure_admin_profile(uid)
    u = await get_user(uid) or {}
    a = await get_admin(uid) or {}
    lines = [
        "👤 **پروفایل ادمین**",
        "━━━━━━━━━━━━━━",
        f"نام: {u.get('first_name')}",
        f"آیدی: `{uid}`",
        f"نقش سیستم: `{a.get('role') or 'ADMIN'}`",
        f"نقش Progression: `{prof.get('role_key')}`",
        f"Admin XP: `{prof.get('admin_xp')}`",
        f"تسک کامل: `{prof.get('completed_tasks')}`",
        f"فعالیت: `{prof.get('activity_count')}`",
        f"عضویت ادمین پروفایل: `{prof.get('joined_at')}`",
        f"آخرین فعالیت: `{prof.get('last_activity') or '—'}`",
        f"Status: `{(prof or {}).get('status') or 'active'}`",
        "",
        "📜 Role History:",
    ]
    try:
        hist = await get_role_history(uid, 8)
        if not hist:
            lines.append("—")
        for h in hist:
            lines.append(f"• {h.get('old_role')} → {h.get('new_role')} (`{h.get('change_type')}`)")
    except Exception:
        lines.append("—")
    return "\n".join(lines), _kb([[("🔙 داشبورد", "adm:home")]])


async def view_my_activity(uid: int):
    acts = await recent_admin_activity(uid, 15)
    lines = ["📊 **فعالیت‌های اخیر من**", "━━━━━━━━━━━━━━"]
    if not acts:
        lines.append("هنوز فعالیتی ثبت نشده.")
    for a in acts:
        lines.append(
            f"• `{a.get('action')}` → {a.get('target') or '—'} "
            f"| +{a.get('xp_earned')}XP | {a.get('created_at')}"
        )
    return "\n".join(lines), _kb([[("🔙 داشبورد", "adm:home")]])


async def view_leaderboard(period: str = "all"):
    rows = await admin_leaderboard(15, period)
    title = {"all": "همه زمان", "today": "امروز", "week": "هفته", "month": "ماه"}.get(period, period)
    lines = [f"🏅 **لیدربورد ادمین** ({title})", "━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    if not rows:
        lines.append("خالی است.")
    for i, r in enumerate(rows):
        m = medals[i] if i < 3 else f"{i+1}."
        name = r.get("first_name") or r.get("user_id")
        lines.append(
            f"{m} {name} — XP `{r.get('admin_xp')}` | "
            f"تسک `{r.get('completed_tasks') or 0}` | نقش `{r.get('role_key') or '—'}`"
        )
    kb = _kb([
        [("امروز", "adm:lb:today"), ("هفته", "adm:lb:week"), ("ماه", "adm:lb:month")],
        [("همه", "adm:lb:all"), ("🔙 داشبورد", "adm:home")],
    ])
    return "\n".join(lines), kb


async def view_notifs(uid: int):
    items = await list_notifications(uid, 15)
    await mark_notifications_read(uid)
    lines = ["🔔 **اعلان‌ها**", "━━━━━━━━━━━━━━"]
    if not items:
        lines.append("اعلانی نیست.")
    for n in items:
        read = "·" if n.get("is_read") else "●"
        lines.append(f"{read} **{n.get('title')}**\n  {n.get('body') or ''}")
    return "\n".join(lines), _kb([[("🔙 داشبورد", "adm:home")]])
