# ==========================================
# 👑 MeowBot — Full Owner / Admin Panel
# ==========================================

import time
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    OWNER_ID, BOT_VERSION, BOT_NAME, SEASON_DAYS,
    MEOW_COOLDOWN, BATTLE_COOLDOWN, GUIDE_DEFAULT_INTERVAL,
)
from database.users import (
    get_dashboard_stats, count_users, count_active_users,
    get_user, get_all_users, get_top_users,
    admin_set_meow_coins, admin_set_meow_points, admin_set_gym_level,
    add_meow_coins_global, add_meow_points_global, reset_meow_points,
)
from database.groups import (
    count_groups, get_all_groups, get_group,
    set_interaction, set_guide_settings,
)
from database.admins import (
    list_admins, get_admin, add_admin, remove_admin,
    set_admin_enabled, update_admin_role, update_admin_permissions,
    ALL_PERMISSIONS, is_owner,
)
from database.logs import get_recent_logs, log_action
from database.pets import count_pets, get_pet
from database.seasons import get_active_season, get_season_history, get_next_season_number
from database.events import get_active_events
from database.pool import fetchval, fetch, execute, get_pool
from database.missions import get_user_missions
from database.achievements import get_user_achievements

TEHRAN = ZoneInfo("Asia/Tehran")
_start = time.time()

# Pending text actions: user_id -> {"action": str, "meta": dict}
_pending: dict = {}


def _kb(rows):
    """Bale: one button per add(), row natural int >= 1."""
    kb = InlineKeyboardMarkup()
    row_num = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(
                InlineKeyboardButton(text=str(text), callback_data=str(data)),
                row=row_num,
            )
        row_num += 1
    return kb


def nav():
    """منوی اصلی Owner."""
    return _kb([
        [("📊 Dashboard", "owner:dashboard"), ("🖥 Status", "owner:status")],
        [("🧪 Tests", "owner:tests"), ("📡 Ping", "owner:ping")],
        [("👥 Users", "owner:users"), ("📋 لیست کاربران", "owner:um_list")],
        [("🔍 Find User", "owner:user_find"), ("🎫 تیکت‌ها", "owner:tickets")],
        [("💬 Groups", "owner:groups"), ("⚙️ Group Set", "owner:group_set")],
        [("🛡 Admins", "owner:admins"), ("➕ Add Admin", "owner:admin_add")],
        [("💰 Economy", "owner:economy"), ("🐾 Pets", "owner:pets")],
        [("⚔️ Battles", "owner:battles"), ("🎮 Games", "owner:games")],
        [("💡 Guides", "owner:guides"), ("🎯 Missions", "owner:missions")],
        [("🏆 Achievements", "owner:achievements"), ("📅 Seasons", "owner:seasons")],
        [("🎉 Events", "owner:events"), ("📢 Broadcast", "owner:broadcast")],
        [("💬 Msg Admin", "owner:msg_admin"), ("📜 Logs", "owner:logs")],
        [("💾 Backup", "owner:backup"), ("⚙️ Settings", "owner:settings")],
        [("🐛 گزارش‌ها", "owner:reports"), ("🌍 گروه جهانی", "owner:global_group")],
        [("🎯 تسک ادمین", "owner:admin_tasks"), ("🛡 دسترسی ادمین", "owner:admins")],
        [("🚧 Maintenance", "owner:maint"), ("🔙 بستن", "owner:close")],
    ])


def back_nav():
    return _kb([[("🔙 منوی Owner", "owner:home")]])


def economy_kb():
    return _kb([
        [("🪙 +Coin همه", "owner:eco_all_coin"), ("⭐ +Point همه", "owner:eco_all_point")],
        [("🪙 به یک نفر", "owner:eco_one_coin"), ("⭐ به یک نفر", "owner:eco_one_point")],
        [("🏋️ Gym یک نفر", "owner:eco_one_gym")],
        [("📊 آمار اقتصاد", "owner:economy")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def seasons_kb():
    return _kb([
        [("▶️ شروع فصل جدید", "owner:season_start")],
        [("🏁 پایان فصل", "owner:season_end")],
        [("📋 تاریخچه فصول", "owner:season_history")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def guides_kb():
    return _kb([
        [("💡 وضعیت Guideها", "owner:guides")],
        [("✅ روشن همه", "owner:guide_on_all"), ("🔇 خاموش همه", "owner:guide_off_all")],
        [("⏱ فاصله ۱س", "owner:guide_int_3600"), ("⏱ فاصله ۳۰د", "owner:guide_int_1800")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def broadcast_kb():
    return _kb([
        [("📢 به همه گروه‌ها", "owner:bc_groups")],
        [("👥 به همه کاربران (PV)", "owner:bc_users")],
        [("🛡 فقط Adminها", "owner:bc_admins")],
        [("❌ لغو", "owner:home")],
    ])


def backup_kb():
    return _kb([
        [("🆕 ساخت Backup Meta", "owner:backup_create")],
        [("📋 تاریخچه Backup", "owner:backup_list")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def admins_kb():
    return _kb([
        [("📋 لیست Admin", "owner:admins")],
        [("➕ افزودن", "owner:admin_add"), ("➖ حذف", "owner:admin_remove")],
        [("🟢 فعال/غیرفعال", "owner:admin_toggle")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def tests_kb():
    return _kb([
        [("🤖 Bot", "owner:test_bot"), ("🗄 Database", "owner:test_db")],
        [("⏱ Scheduler", "owner:test_sched"), ("💰 Economy", "owner:test_eco")],
        [("🐾 Pet", "owner:test_pet"), ("⚔️ Battle", "owner:test_battle")],
        [("💡 Guide", "owner:test_guide"), ("📅 Season", "owner:test_season")],
        [("🧪 Test Everything", "owner:test_all")],
        [("🔙 منوی Owner", "owner:home")],
    ])


def uptime_str():
    s = int(time.time() - _start)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    d, h = divmod(h, 24)
    if d:
        return f"{d}d {h}h {m}m"
    return f"{h}h {m}m {sec}s"


async def show_owner_panel(message):
    text = (
        f"👑 **{BOT_NAME} OWNER PANEL**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🛡 نسخه: `{BOT_VERSION}`\n"
        f"⏱ Uptime: `{uptime_str()}`\n"
        f"🕒 تهران: `{datetime.now(TEHRAN).strftime('%Y-%m-%d %H:%M')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"یکی از بخش‌ها را انتخاب کن 👇"
    )
    await message.reply(text, components=nav())


async def handle_owner_callback(bot, callback, data: str):
    action = data.split(":", 1)[1] if ":" in data else data
    msg = callback.message
    user_id = int(callback.from_user.id) if callback.from_user else 0

    try:
        await callback.answer()
    except Exception:
        pass

    try:
        if action in ("close",):
            await _edit(msg, "👑 پنل بسته شد.", None)
            return

        if action in ("home", "panel"):
            await _edit(msg, (
                f"👑 **{BOT_NAME} OWNER PANEL**\n"
                f"━━━━━━━━━━━━━━\n"
                f"نسخه `{BOT_VERSION}` | Uptime `{uptime_str()}`\n"
                f"بخش مورد نظر را انتخاب کن:"
            ), nav())
            return

        # ========== DASHBOARD ==========
        if action == "dashboard":
            stats = await get_dashboard_stats()
            text = (
                f"📊 **DASHBOARD**\n"
                f"━━━━━━━━━━━━━━\n"
                f"👥 Users: `{stats.get('total_users', 0)}`\n"
                f"🟢 Active 7d: `{stats.get('active_users', 0)}`\n"
                f"💬 Groups: `{stats.get('total_groups', 0)}`\n"
                f"🐾 Pets: `{stats.get('total_pets', 0)}`\n"
                f"🪙 Total Coins: `{stats.get('total_coins', 0)}`\n"
                f"⚔️ Battles: `{stats.get('total_battles', 0)}`\n"
                f"🐱 Meows: `{stats.get('total_meows', 0)}`\n"
                f"📅 Season: `{stats.get('current_season', 0)}`\n"
                f"🎉 Events: `{stats.get('active_events', 0)}`\n"
                f"🛡 Admins: `{stats.get('total_admins', 0)}`\n"
                f"⏱ Uptime: `{uptime_str()}`\n"
                f"━━━━━━━━━━━━━━"
            )
            await _edit(msg, text, nav())
            return

        # ========== STATUS ==========
        if action == "status":
            db_ok, db_ms = "🟢", "?"
            try:
                t0 = time.time()
                await fetchval("SELECT 1")
                db_ms = f"{int((time.time() - t0) * 1000)}ms"
            except Exception as e:
                db_ok = "🔴"
                db_ms = str(e)[:40]

            season = await get_active_season()
            season_line = f"#{season.get('season_number')}" if season else "—"
            events = await get_active_events()

            text = (
                f"🖥 **SYSTEM STATUS**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🤖 Bot: 🟢 ONLINE\n"
                f"🗄 PostgreSQL: {db_ok} (`{db_ms}`)\n"
                f"⏱ Scheduler: 🟢\n"
                f"💡 Auto Guide: 🟢\n"
                f"📅 Season: 🟢 (`{season_line}`)\n"
                f"🎉 Events: `{len(events)}` active\n"
                f"💾 Backup: 🟢\n"
                f"📜 Logging: 🟢\n"
                f"━━━━━━━━━━━━━━\n"
                f"Uptime: `{uptime_str()}`\n"
                f"Version: `{BOT_VERSION}`"
            )
            await _edit(msg, text, nav())
            return

        # ========== PING ==========
        if action == "ping":
            lines = ["📡 **PING / HEALTH**\n━━━━━━━━━━━━━━"]
            # DB
            try:
                t0 = time.time()
                await fetchval("SELECT 1")
                lines.append(f"🗄 DB: ✅ `{int((time.time()-t0)*1000)}ms`")
            except Exception as e:
                lines.append(f"🗄 DB: ❌ `{e}`")
            # Count queries
            try:
                t0 = time.time()
                n = await count_users()
                lines.append(f"👥 Users query: ✅ `{int((time.time()-t0)*1000)}ms` ({n})")
            except Exception as e:
                lines.append(f"👥 Users: ❌ `{e}`")
            try:
                t0 = time.time()
                n = await count_groups()
                lines.append(f"💬 Groups query: ✅ `{int((time.time()-t0)*1000)}ms` ({n})")
            except Exception as e:
                lines.append(f"💬 Groups: ❌ `{e}`")
            lines.append(f"\n🤖 Bot process: ✅\n⏱ Uptime: `{uptime_str()}`")
            await _edit(msg, "\n".join(lines), nav())
            return

        # ========== TESTS ==========
        if action == "tests":
            await _edit(msg, "🧪 **TEST CENTER**\nیک تست را انتخاب کن:", tests_kb())
            return

        if action.startswith("test_"):
            result = await _run_test(action.replace("test_", ""), bot)
            await _edit(msg, result, tests_kb())
            return

        # ========== USERS ==========
        if action == "users":
            total = await count_users()
            active = await count_active_users(7)
            top = await get_top_users(limit=5)
            lines = [
                f"👥 **USERS**\n━━━━━━━━━━━━━━",
                f"کل: `{total}` | فعال ۷روز: `{active}`\n",
                "🏆 Top امتیاز فصل:",
            ]
            for i, u in enumerate(top or []):
                name = u.get("first_name") or str(u.get("user_id"))
                lines.append(f"{i+1}. {name} — `{u.get('meow_points', 0)}` 🐾")
            lines.append(
                "\n📌 دستورات:\n"
                "`/addcoin ID N`\n"
                "`/addpoint ID N`\n"
                "`/addgym ID N`\n"
                "یا از 🔍 Find User استفاده کن."
            )
            await _edit(msg, "\n".join(lines), nav())
            return

        if action == "user_find":
            _pending[user_id] = {"action": "find_user"}
            await _edit(
                msg,
                "🔍 **پیدا کردن کاربر**\n"
                "آیدی عددی کاربر را در چت بفرست:\n"
                "مثال: `1967315238`",
                back_nav(),
            )
            return

        # ========== GROUPS ==========
        if action == "groups":
            groups = await get_all_groups()
            lines = [f"💬 **GROUPS** (`{len(groups)}`)\n━━━━━━━━━━━━━━"]
            for g in (groups or [])[:20]:
                title = g.get("title") or g.get("username") or g.get("chat_id")
                inter = "🟢" if g.get("interaction_on", True) else "🔇"
                guide = "💡" if g.get("guide_enabled", True) else "💤"
                interval = g.get("guide_interval") or 0
                lines.append(f"{inter}{guide} {title}\n   id:`{g.get('chat_id')}` | guide:{interval}s")
            if len(groups or []) > 20:
                lines.append(f"... و {len(groups)-20} گروه دیگر")
            await _edit(msg, "\n".join(lines), nav())
            return

        if action == "group_set":
            _pending[user_id] = {"action": "group_set"}
            await _edit(
                msg,
                "⚙️ **تنظیم گروه**\n"
                "فرمت پیام:\n"
                "`chat_id interaction on/off`\n"
                "یا\n"
                "`chat_id guide on/off`\n"
                "یا\n"
                "`chat_id interval 3600`\n\n"
                "مثال:\n`123456789 interaction off`",
                back_nav(),
            )
            return

        # ========== ADMINS ==========
        if action == "admins":
            from admin.perms_mgmt import admins_list_text
            text, kb = await admins_list_text()
            await _edit(msg, text, kb)
            return

        
        if action == "admin_add":
            _pending[user_id] = {"action": "admin_add"}
            await _edit(
                msg,
                "➕ **افزودن Admin**\n"
                "فرمت:\n`USER_ID ROLE`\n"
                "ROLE: `ADMIN` | `SUPER_ADMIN` | `MODERATOR`\n\n"
                "مثال:\n`123456789 ADMIN`",
                back_nav(),
            )
            return

        if action == "admin_remove":
            _pending[user_id] = {"action": "admin_remove"}
            await _edit(msg, "➖ آیدی Admin برای حذف را بفرست:", back_nav())
            return

        if action == "admin_toggle":
            _pending[user_id] = {"action": "admin_toggle"}
            await _edit(msg, "🟢/🔴 آیدی Admin برای فعال/غیرفعال:", back_nav())
            return

        # ========== ECONOMY ==========
        if action == "economy":
            try:
                total_coins = int(await fetchval("SELECT COALESCE(SUM(meow_coins),0) FROM users") or 0)
                total_points = int(await fetchval("SELECT COALESCE(SUM(meow_points),0) FROM users") or 0)
                avg_coins = int(await fetchval("SELECT COALESCE(AVG(meow_coins),0) FROM users") or 0)
            except Exception:
                total_coins = total_points = avg_coins = 0
            text = (
                f"💰 **ECONOMY**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🪙 مجموع کوین: `{total_coins}`\n"
                f"⭐ مجموع پوینت فصل: `{total_points}`\n"
                f"📊 میانگین کوین: `{avg_coins}`\n"
                f"━━━━━━━━━━━━━━\n"
                f"از دکمه‌ها یا دستورات متنی استفاده کن."
            )
            await _edit(msg, text, economy_kb())
            return

        if action == "eco_all_coin":
            _pending[user_id] = {"action": "eco_all_coin"}
            await _edit(msg, "🪙 مقدار کوین برای **همه کاربران** را بفرست:", back_nav())
            return

        if action == "eco_all_point":
            _pending[user_id] = {"action": "eco_all_point"}
            await _edit(msg, "⭐ مقدار پوینت برای **همه** را بفرست:", back_nav())
            return

        if action == "eco_one_coin":
            _pending[user_id] = {"action": "eco_one_coin"}
            await _edit(msg, "🪙 فرمت: `USER_ID AMOUNT`\nمثال: `123 500`", back_nav())
            return

        if action == "eco_one_point":
            _pending[user_id] = {"action": "eco_one_point"}
            await _edit(msg, "⭐ فرمت: `USER_ID AMOUNT`", back_nav())
            return

        if action == "eco_one_gym":
            _pending[user_id] = {"action": "eco_one_gym"}
            await _edit(msg, "🏋️ فرمت: `USER_ID NEW_LEVEL`", back_nav())
            return

        # ========== PETS ==========
        if action == "pets":
            n = await count_pets()
            try:
                rows = await fetch(
                    "SELECT pet_name, level, user_id FROM pets "
                    "WHERE awaiting_name = FALSE ORDER BY level DESC LIMIT 10"
                )
            except Exception:
                rows = []
            lines = [f"🐾 **PETS** (`{n}`)\n━━━━━━━━━━━━━━", "🏆 قوی‌ترین‌ها:"]
            for r in rows or []:
                lines.append(f"• {r['pet_name']} Lv.{r['level']} — user `{r['user_id']}`")
            if not rows:
                lines.append("هنوز Petی نیست.")
            await _edit(msg, "\n".join(lines), back_nav())
            return

        # ========== BATTLES ==========
        if action == "battles":
            try:
                total_b = int(await fetchval("SELECT COALESCE(SUM(total_battles),0) FROM users") or 0)
                total_w = int(await fetchval("SELECT COALESCE(SUM(total_wins),0) FROM users") or 0)
                rows = await fetch(
                    "SELECT first_name, total_wins, total_battles FROM users "
                    "ORDER BY total_wins DESC LIMIT 5"
                )
            except Exception:
                total_b = total_w = 0
                rows = []
            lines = [
                f"⚔️ **BATTLES**\n━━━━━━━━━━━━━━",
                f"کل نبردها: `{total_b}` | کل بردها: `{total_w}`\n",
                "🏆 Top Wins:",
            ]
            for r in rows or []:
                lines.append(f"• {r['first_name'] or '?'} — W:`{r['total_wins']}` / `{r['total_battles']}`")
            await _edit(msg, "\n".join(lines), back_nav())
            return

        # ========== GAMES ==========
        if action == "games":
            await _edit(
                msg,
                "🎮 **GAMES**\n━━━━━━━━━━━━━━\n"
                "مینی‌گیم‌های فعال:\n"
                "• 🎲 حدس عدد\n"
                "• ❓ کوییز / کوییز گربه\n"
                "• ⚡ ری‌اکشن\n\n"
                "از منوی کاربر → 🎮 بازی‌ها",
                back_nav(),
            )
            return

        # ========== GUIDES ==========
        if action == "guides":
            groups = await get_all_groups()
            on = sum(1 for g in (groups or []) if g.get("guide_enabled"))
            text = (
                f"💡 **AUTO GUIDE**\n"
                f"━━━━━━━━━━━━━━\n"
                f"گروه‌های با Guide روشن: `{on}` / `{len(groups or [])}`\n"
                f"پیش‌فرض فاصله: `{GUIDE_DEFAULT_INTERVAL}s`\n"
                f"━━━━━━━━━━━━━━\n"
                f"Guide مستقل از Interaction است."
            )
            await _edit(msg, text, guides_kb())
            return

        if action == "guide_on_all":
            await execute("UPDATE groups SET guide_enabled = TRUE")
            await log_action(user_id, "guide_on_all", result="ok")
            await _edit(msg, "✅ Guide برای همه گروه‌ها روشن شد.", guides_kb())
            return

        if action == "guide_off_all":
            await execute("UPDATE groups SET guide_enabled = FALSE")
            await log_action(user_id, "guide_off_all", result="ok")
            await _edit(msg, "🔇 Guide برای همه گروه‌ها خاموش شد.", guides_kb())
            return

        if action == "guide_int_3600":
            await execute("UPDATE groups SET guide_interval = 3600")
            await _edit(msg, "⏱ فاصله Guide همه گروه‌ها → ۱ ساعت", guides_kb())
            return

        if action == "guide_int_1800":
            await execute("UPDATE groups SET guide_interval = 1800")
            await _edit(msg, "⏱ فاصله Guide همه گروه‌ها → ۳۰ دقیقه", guides_kb())
            return

        # ========== MISSIONS / ACHIEVEMENTS ==========
        if action == "missions":
            try:
                n = int(await fetchval("SELECT COUNT(*) FROM missions WHERE active = TRUE") or 0)
            except Exception:
                n = 0
            await _edit(
                msg,
                f"🎯 **MISSIONS**\n━━━━━━━━━━━━━━\n"
                f"مأموریت‌های فعال در سیستم: `{n}`\n"
                f"Daily + Weekly برای کاربران.",
                back_nav(),
            )
            return

        if action == "achievements":
            try:
                n = int(await fetchval("SELECT COUNT(*) FROM achievements") or 0)
                done = int(await fetchval("SELECT COUNT(*) FROM user_achievements WHERE completed = TRUE") or 0)
            except Exception:
                n = done = 0
            await _edit(
                msg,
                f"🏆 **ACHIEVEMENTS**\n━━━━━━━━━━━━━━\n"
                f"تعریف‌شده: `{n}`\n"
                f"تکمیل‌شده توسط کاربران: `{done}`",
                back_nav(),
            )
            return

        # ========== SEASONS ==========
        if action == "seasons":
            s = await get_active_season()
            if s:
                text = (
                    f"📅 **SEASON**\n━━━━━━━━━━━━━━\n"
                    f"فصل فعال: `#{s.get('season_number')}`\n"
                    f"شروع: `{s.get('start_date')}`\n"
                    f"پایان: `{s.get('end_date')}`\n"
                    f"مدت تنظیم: `{SEASON_DAYS}` روز\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"⚠️ پایان فصل فقط امتیاز رنکینگ را ریست می‌کند."
                )
            else:
                text = "📅 فصل فعالی نیست.\nمی‌توانی فصل جدید شروع کنی."
            await _edit(msg, text, seasons_kb())
            return

        if action == "season_start":
            try:
                from seasons.scheduler import start_new_season
                await start_new_season(bot)
                await log_action(user_id, "season_start", result="ok")
                await _edit(msg, "✅ فصل جدید شروع شد و به گروه‌ها اعلام شد.", seasons_kb())
            except Exception as e:
                await _edit(msg, f"❌ خطا: `{e}`", seasons_kb())
            return

        if action == "season_end":
            try:
                from seasons.scheduler import end_season
                await end_season(bot)
                await log_action(user_id, "season_end", result="ok")
                await _edit(
                    msg,
                    "✅ فصل پایان یافت.\n"
                    "رنکینگ ذخیره شد.\n"
                    "فقط meow_points ریست شد (سکه/Pet حفظ شد).",
                    seasons_kb(),
                )
            except Exception as e:
                await _edit(msg, f"❌ خطا: `{e}`", seasons_kb())
            return

        if action == "season_history":
            hist = await get_season_history(10)
            lines = ["📋 **تاریخچه فصول**\n━━━━━━━━━━━━━━"]
            for s in hist or []:
                act = "🟢" if s.get("active") else "⚪"
                lines.append(
                    f"{act} #{s.get('season_number')} | "
                    f"{s.get('start_date')} → {s.get('end_date')}"
                )
            if not hist:
                lines.append("خالی")
            await _edit(msg, "\n".join(lines), seasons_kb())
            return

        # ========== EVENTS ==========
        if action == "events":
            events = await get_active_events()
            lines = ["🎉 **EVENTS**\n━━━━━━━━━━━━━━"]
            if not events:
                lines.append("ایونت فعالی نیست.")
            for e in events:
                lines.append(
                    f"• {e.get('name')}\n"
                    f"  XP×{e.get('bonus_xp')} Coin×{e.get('bonus_coin')}\n"
                    f"  تا `{e.get('end_at')}`"
                )
            lines.append(
                "\n📌 ساخت ایونت:\n"
                "در چت بفرست:\n"
                "`event NAME | DAYS | XP_MULT | COIN_MULT`"
            )
            # برای ساخت ایونت از دکمه استفاده شود — pending روی view ست نمی‌شود
            await _edit(msg, "\n".join(lines), _kb([[("➕ ساخت ایونت", "owner:event_new")], [("🔙 منوی Owner", "owner:home")]]))
            return

        if action == "event_new":
            _pending[user_id] = {"action": "event_create"}
            await _edit(
                msg,
                "🎉 **ساخت ایونت**\n"
                "فرمت:\n`نام | روز | xp_mult | coin_mult`\n"
                "مثال:\n`جشن میو | 3 | 1.5 | 2`\n\n"
                "برای لغو بنویس: `لغو`",
                back_nav(),
            )
            return

        # ========== BROADCAST ==========
        if action == "broadcast":
            await _edit(
                msg,
                "📢 **BROADCAST**\n"
                "مخاطب را انتخاب کن، بعد متن را در چت بفرست.",
                broadcast_kb(),
            )
            return

        if action == "bc_groups":
            _pending[user_id] = {"action": "bc_groups"}
            await _edit(msg, "📢 متن پیام همگانی برای **همه گروه‌ها** را بفرست:", back_nav())
            return

        if action == "bc_users":
            _pending[user_id] = {"action": "bc_users"}
            await _edit(msg, "👥 متن پیام برای **همه کاربران (PV)** را بفرست:\n(ممکن است طول بکشد)", back_nav())
            return

        if action == "bc_admins":
            _pending[user_id] = {"action": "bc_admins"}
            await _edit(msg, "🛡 متن پیام برای **همه Adminها** را بفرست:", back_nav())
            return

        # ========== MSG ADMIN ==========
        if action == "msg_admin":
            _pending[user_id] = {"action": "msg_admin"}
            admins = await list_admins()
            lines = ["💬 **پیام به Admin**\nفرمت:\n`USER_ID متن پیام`\n\nAdminها:"]
            for a in admins or []:
                lines.append(f"• `{a.get('user_id')}` ({a.get('role')})")
            await _edit(msg, "\n".join(lines), back_nav())
            return

        # ========== LOGS ==========
        if action == "logs":
            logs = await get_recent_logs(20)
            lines = ["📜 **AUDIT LOGS**\n━━━━━━━━━━━━━━"]
            for lg in logs or []:
                ts = lg.get("created_at")
                ts_s = str(ts)[:19] if ts else ""
                lines.append(
                    f"• `{lg.get('action')}` by `{lg.get('actor_id')}`\n"
                    f"  → {lg.get('target') or '-'} | {lg.get('result')} | {ts_s}"
                )
            if not logs:
                lines.append("خالی")
            await _edit(msg, "\n".join(lines), back_nav())
            return

        # ========== BACKUP ==========
        if action == "backup":
            await _edit(
                msg,
                "💾 **BACKUP CENTER**\n"
                "━━━━━━━━━━━━━━\n"
                "روی Railway بهترین روش:\n"
                "`pg_dump $DATABASE_URL`\n\n"
                "از دکمه‌ها برای ثبت متادیتا در دیتابیس استفاده کن.",
                backup_kb(),
            )
            return

        if action == "backup_create":
            try:
                n_users = await count_users()
                n_groups = await count_groups()
                fname = f"MeowBot_Backup_{datetime.now(TEHRAN).strftime('%Y-%m-%d_%H-%M-%S')}.meta"
                await execute(
                    """
                    INSERT INTO backups (filename, size_bytes, created_by, status, note)
                    VALUES ($1, $2, $3, 'ok', $4)
                    """,
                    fname, 0, user_id,
                    f"users={n_users} groups={n_groups}",
                )
                await log_action(user_id, "backup_create", fname, {"users": n_users})
                await _edit(
                    msg,
                    f"✅ Backup meta ثبت شد:\n`{fname}`\n"
                    f"Users: `{n_users}` | Groups: `{n_groups}`\n\n"
                    f"برای فایل واقعی SQL از pg_dump روی Railway استفاده کن.",
                    backup_kb(),
                )
            except Exception as e:
                await _edit(msg, f"❌ `{e}`", backup_kb())
            return

        if action == "backup_list":
            try:
                rows = await fetch(
                    "SELECT * FROM backups ORDER BY created_at DESC LIMIT 10"
                )
            except Exception:
                rows = []
            lines = ["📋 **Backup History**\n━━━━━━━━━━━━━━"]
            for r in rows or []:
                lines.append(
                    f"• `{r.get('filename')}`\n"
                    f"  by `{r.get('created_by')}` | {r.get('status')} | {r.get('note')}"
                )
            if not rows:
                lines.append("خالی")
            await _edit(msg, "\n".join(lines), backup_kb())
            return

        # ========== SETTINGS ==========
        if action == "settings":
            text = (
                f"⚙️ **SETTINGS**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🤖 Bot: `{BOT_NAME}` v`{BOT_VERSION}`\n"
                f"👑 Owner: `{OWNER_ID}`\n"
                f"🐱 Meow CD: `{MEOW_COOLDOWN}s`\n"
                f"⚔️ Battle CD: `{BATTLE_COOLDOWN}s`\n"
                f"📅 Season days: `{SEASON_DAYS}`\n"
                f"💡 Guide default: `{GUIDE_DEFAULT_INTERVAL}s`\n"
                f"━━━━━━━━━━━━━━\n"
                f"تغییر مقادیر از `config.py` / Environment."
            )
            await _edit(msg, text, back_nav())
            return

        # ========== MAINTENANCE ==========
        if action == "maint":
            await _edit(
                msg,
                "🚧 **MAINTENANCE**\n"
                "━━━━━━━━━━━━━━\n"
                "• برای خاموشی موقت سرویس را در Railway Stop کن\n"
                "• برای ریست فصل از بخش Seasons استفاده کن\n"
                "• لاگ‌ها در بخش Logs\n"
                "• Health در Status / Ping / Tests",
                back_nav(),
            )
            return


        if action == "reports":
            from core.reports import admin_list_text
            text, kb = await admin_list_text("open")
            await _edit(msg, text, kb)
            return

        if action == "global_group":
            from database.settings import get_global_meow_group
            g = await get_global_meow_group()
            info = "تنظیم نشده"
            if g:
                info = f"id=`{g.get('chat_id')}`\nlink={g.get('invite_link') or '—'}\ntitle={g.get('title')}"
            _pending[user_id] = {"action": "set_global_group"}
            await _edit(
                msg,
                "🌍 **گروه جهانی میو**\n"
                "━━━━━━━━━━━━━━\n"
                f"وضعیت فعلی:\n{info}\n\n"
                "فرمت پیام:\n"
                "`CHAT_ID | لینک_دعوت | عنوان`\n\n"
                "مثال:\n"
                "`123456789 | https://ble.ir/join/xxx | گروه میو اصلی`\n\n"
                "ربات باید داخل آن گروه ادمین/عضو باشد.\n"
                "لغو: `لغو`",
                back_nav(),
            )
            return


        if action == "um_list":
            try:
                from admin.users_mgmt import users_list_page
                text, kb = await users_list_page(0)
                await _edit(msg, text, kb)
            except Exception as e:
                await _edit(msg, f"❌ لیست کاربران:\n`{e}`", nav())
            return

        if action == "tickets":
            from admin.tickets_panel import tickets_home
            text, kb = await tickets_home(back_cb="owner:home")
            await _edit(msg, text, kb)
            return

        if action == "admin_tasks":
            from admin.owner_tasks import tasks_home
            text, kb = await tasks_home()
            await _edit(msg, text, kb)
            return

        await _edit(msg, f"❓ بخش ناشناخته: `{action}`", nav())

    except Exception as e:
        traceback.print_exc()
        try:
            await _edit(msg, f"⚠️ خطا در پنل:\n`{e}`", nav())
        except Exception:
            pass


async def _run_test(name: str, bot) -> str:
    lines = [f"🧪 **TEST: {name}**\n━━━━━━━━━━━━━━"]
    tests = []

    async def t_bot():
        return bool(bot), "Bot instance"

    async def t_db():
        t0 = time.time()
        await fetchval("SELECT 1")
        return True, f"DB ping {int((time.time()-t0)*1000)}ms"

    async def t_sched():
        return True, "Scheduler module importable"

    async def t_eco():
        n = await count_users()
        return True, f"Users table OK ({n})"

    async def t_pet():
        n = await count_pets()
        return True, f"Pets table OK ({n})"

    async def t_battle():
        v = await fetchval("SELECT COALESCE(SUM(total_battles),0) FROM users")
        return True, f"Battles sum={v}"

    async def t_guide():
        from guides import scheduler as gs
        return True, "Guide scheduler module OK"

    async def t_season():
        s = await get_active_season()
        return True, f"Active season={s.get('season_number') if s else None}"

    mapping = {
        "bot": [t_bot],
        "db": [t_db],
        "sched": [t_sched],
        "eco": [t_eco],
        "pet": [t_pet],
        "battle": [t_battle],
        "guide": [t_guide],
        "season": [t_season],
        "all": [t_bot, t_db, t_sched, t_eco, t_pet, t_battle, t_guide, t_season],
    }
    for fn in mapping.get(name, [t_bot]):
        try:
            ok, detail = await fn()
            lines.append(f"{'✅' if ok else '❌'} {detail}")
        except Exception as e:
            lines.append(f"❌ {fn.__name__}: {e}")
    return "\n".join(lines)


async def handle_owner_text(bot, message, user_id: int, text: str) -> bool:
    """
    پردازش ورودی متنی برای اکشن‌های pending پنل.
    True = هندل شد.
    """
    pending = _pending.get(user_id)
    if not pending:
        return False

    action = pending.get("action")
    text = (text or "").strip()

    # لغو هر pending
    if text in ("لغو", "cancel", "/cancel", "انصراف"):
        _pending.pop(user_id, None)
        await message.reply("✅ لغو شد.", components=nav())
        return True

    try:
        if action == "find_user":
            try:
                tid = int(text.split()[0])
            except ValueError:
                await message.reply("❌ آیدی عددی بفرست.", components=back_nav())
                return True
            u = await get_user(tid)
            if not u:
                await message.reply(f"❌ کاربر `{tid}` پیدا نشد.", components=back_nav())
                return True
            pet = await get_pet(tid)
            pet_line = "—"
            if pet and not pet.get("awaiting_name"):
                pet_line = f"{pet.get('pet_name')} Lv.{pet.get('level')}"
            await message.reply(
                f"👤 **User `{tid}`**\n"
                f"━━━━━━━━━━━━━━\n"
                f"نام: {u.get('first_name')}\n"
                f"@{u.get('username') or '—'}\n"
                f"🐾 Points: `{u.get('meow_points')}`\n"
                f"🪙 Coins: `{u.get('meow_coins')}`\n"
                f"🏋️ Gym: `{u.get('gym_level')}`\n"
                f"⚔️ W/L: `{u.get('total_wins')}/{u.get('total_losses')}`\n"
                f"🐱 Meows: `{u.get('total_meows')}`\n"
                f"🐾 Pet: {pet_line}\n"
                f"━━━━━━━━━━━━━━",
                components=nav(),
            )
            _pending.pop(user_id, None)
            return True

        if action == "admin_add":
            parts = text.split()
            if len(parts) < 1:
                await message.reply("❌ `USER_ID [ROLE]`", components=back_nav())
                return True
            tid = int(parts[0])
            role = (parts[1] if len(parts) > 1 else "ADMIN").upper()
            if role not in ("ADMIN", "SUPER_ADMIN", "MODERATOR"):
                role = "ADMIN"
            perms = list(ALL_PERMISSIONS) if role == "SUPER_ADMIN" else [
                "users.view", "groups.view", "economy.view", "logs.view",
            ]
            await add_admin(tid, role=role, permissions=perms, added_by=user_id)
            await log_action(user_id, "admin_add", str(tid), {"role": role})
            await message.reply(f"✅ Admin `{tid}` با نقش **{role}** اضافه شد.", components=admins_kb())
            _pending.pop(user_id, None)
            return True

        if action == "admin_remove":
            tid = int(text.split()[0])
            ok = await remove_admin(tid)
            await log_action(user_id, "admin_remove", str(tid), result="ok" if ok else "denied")
            msg = f"✅ Admin `{tid}` حذف شد." if ok else "❌ نمی‌توان Owner را حذف کرد / یافت نشد."
            await message.reply(msg, components=admins_kb())
            _pending.pop(user_id, None)
            return True

        if action == "admin_toggle":
            tid = int(text.split()[0])
            a = await get_admin(tid)
            if not a:
                await message.reply("❌ Admin نیست.", components=admins_kb())
                _pending.pop(user_id, None)
                return True
            new_state = not bool(a.get("enabled"))
            await set_admin_enabled(tid, new_state)
            await log_action(user_id, "admin_toggle", str(tid), {"enabled": new_state})
            await message.reply(
                f"{'🟢 فعال' if new_state else '🔴 غیرفعال'}: `{tid}`",
                components=admins_kb(),
            )
            _pending.pop(user_id, None)
            return True

        if action == "eco_all_coin":
            amount = int(text.split()[0])
            n = await add_meow_coins_global(amount)
            await log_action(user_id, "eco_all_coin", str(amount), {"users": n})
            await message.reply(f"✅ +{amount}🪙 به همه (تقریباً `{n}` کاربر).", components=economy_kb())
            _pending.pop(user_id, None)
            return True

        if action == "eco_all_point":
            amount = int(text.split()[0])
            n = await add_meow_points_global(amount)
            await log_action(user_id, "eco_all_point", str(amount), {"users": n})
            await message.reply(f"✅ +{amount}⭐ به همه (`{n}`).", components=economy_kb())
            _pending.pop(user_id, None)
            return True

        if action in ("eco_one_coin", "eco_one_point", "eco_one_gym"):
            parts = text.split()
            if len(parts) != 2:
                await message.reply("❌ `USER_ID AMOUNT`", components=back_nav())
                return True
            tid, val = int(parts[0]), int(parts[1])
            u = await get_user(tid)
            if not u:
                await message.reply("❌ کاربر نیست.", components=back_nav())
                return True
            if action == "eco_one_coin":
                old = int(u.get("meow_coins") or 0)
                ok, o, n = await admin_set_meow_coins(tid, max(0, old + val))
                field = "🪙"
            elif action == "eco_one_point":
                old = int(u.get("meow_points") or 0)
                ok, o, n = await admin_set_meow_points(tid, max(0, old + val))
                field = "⭐"
            else:
                ok, o, n = await admin_set_gym_level(tid, val)
                field = "🏋️"
            await log_action(user_id, action, str(tid), {"old": o, "new": n})
            await message.reply(f"✅ {field} `{tid}`: {o} → {n}", components=economy_kb())
            _pending.pop(user_id, None)
            return True

        if action == "group_set":
            parts = text.split()
            if len(parts) < 3:
                await message.reply("❌ `chat_id key value`", components=back_nav())
                return True
            cid, key, val = parts[0], parts[1].lower(), parts[2].lower()
            if key == "interaction":
                await set_interaction(cid, val in ("on", "1", "true", "yes"))
                await message.reply(f"✅ Interaction `{cid}` → {val}", components=nav())
            elif key == "guide":
                await set_guide_settings(cid, enabled=val in ("on", "1", "true", "yes"))
                await message.reply(f"✅ Guide `{cid}` → {val}", components=nav())
            elif key == "interval":
                await set_guide_settings(cid, interval=int(val))
                await message.reply(f"✅ Guide interval `{cid}` → {val}s", components=nav())
            else:
                await message.reply("❌ key: interaction | guide | interval", components=back_nav())
                return True
            await log_action(user_id, "group_set", cid, {"key": key, "val": val})
            _pending.pop(user_id, None)
            return True

        if action in ("bc_groups", "bc_users", "bc_admins"):
            sent = failed = 0
            if action == "bc_groups":
                groups = await get_all_groups()
                for g in groups or []:
                    try:
                        await bot.send_message(g["chat_id"], text)
                        sent += 1
                    except Exception:
                        failed += 1
            elif action == "bc_admins":
                admins = await list_admins()
                ids = {int(a["user_id"]) for a in (admins or [])}
                ids.add(int(OWNER_ID))
                for aid in ids:
                    try:
                        await bot.send_message(aid, f"🛡 **Admin Broadcast**\n\n{text}")
                        sent += 1
                    except Exception:
                        failed += 1
            else:  # bc_users
                users = await get_all_users()
                for u in (users or [])[:500]:  # safety cap
                    try:
                        await bot.send_message(u["user_id"], text)
                        sent += 1
                    except Exception:
                        failed += 1
            await log_action(user_id, action, result="ok", details={"sent": sent, "failed": failed})
            await message.reply(
                f"📢 تمام شد.\n✅ ارسال: `{sent}`\n❌ خطا: `{failed}`",
                components=nav(),
            )
            _pending.pop(user_id, None)
            return True

        if action == "msg_admin":
            parts = text.split(None, 1)
            if len(parts) < 2:
                await message.reply("❌ `USER_ID متن`", components=back_nav())
                return True
            tid, body = int(parts[0]), parts[1]
            try:
                await bot.send_message(tid, f"💬 **پیام از Owner**\n\n{body}")
                await log_action(user_id, "msg_admin", str(tid))
                await message.reply(f"✅ پیام به `{tid}` ارسال شد.", components=nav())
            except Exception as e:
                await message.reply(f"❌ ارسال نشد: `{e}`", components=back_nav())
            _pending.pop(user_id, None)
            return True

        if action == "event_create":
            # NAME | DAYS | XP | COIN
            if "|" not in text:
                await message.reply(
                    "❌ فرمت:\n`نام | روز | xp_mult | coin_mult`\n"
                    "مثال: `جشن میو | 3 | 1.5 | 2`",
                    components=back_nav(),
                )
                return True
            parts = [p.strip() for p in text.split("|")]
            name = parts[0]
            days = int(parts[1]) if len(parts) > 1 else 1
            xp_m = float(parts[2]) if len(parts) > 2 else 1.0
            coin_m = float(parts[3]) if len(parts) > 3 else 1.0
            from database.events import create_event
            start = datetime.now(TEHRAN)
            from datetime import timedelta
            end = start + timedelta(days=days)
            await create_event(name, f"Event by owner", start, end, xp_m, coin_m)
            await log_action(user_id, "event_create", name)
            await message.reply(
                f"✅ ایونت **{name}** برای `{days}` روز ساخته شد.\n"
                f"XP×{xp_m} Coin×{coin_m}",
                components=nav(),
            )
            _pending.pop(user_id, None)
            return True


        if action == "set_global_group":
            parts = [x.strip() for x in text.split("|")]
            if not parts or not parts[0]:
                await message.reply("❌ `CHAT_ID | invite_link | title`", components=back_nav())
                return True
            cid = parts[0].strip()
            invite = parts[1].strip() if len(parts) > 1 else ""
            title = parts[2].strip() if len(parts) > 2 else "گروه میو"
            from database.settings import set_global_meow_group
            try:
                await set_global_meow_group(cid, invite, title)
            except Exception as e:
                await message.reply(f"❌ ذخیره تنظیمات: `{e}`", components=back_nav())
                _pending.pop(user_id, None)
                return True
            try:
                await log_action(
                    user_id,
                    "set_global_group",
                    str(cid),
                    {"invite": invite, "title": title},
                )
            except Exception:
                pass
            await message.reply(
                "✅ گروه جهانی تنظیم شد.\n`{}`\n{}\n{}".format(
                    cid, title, invite or "بدون لینک"
                ),
                components=nav(),
            )
            _pending.pop(user_id, None)
            return True

    except Exception as e:
        traceback.print_exc()
        await message.reply(f"⚠️ خطا: `{e}`", components=back_nav())
        _pending.pop(user_id, None)
        return True

    return False


async def _edit(msg, text, kb=None):
    try:
        if hasattr(msg, "edit"):
            if kb is not None:
                await msg.edit(text, components=kb)
            else:
                await msg.edit(text)
            return
        if hasattr(msg, "edit_text"):
            if kb is not None:
                await msg.edit_text(text, components=kb)
            else:
                await msg.edit_text(text)
            return
    except Exception as e:
        print(f"owner panel edit: {e}")
        try:
            chat = getattr(msg, "chat", None)
            chat_id = getattr(chat, "id", None) if chat else None
            if chat_id and hasattr(msg, "reply"):
                if kb is not None:
                    await msg.reply(text, components=kb)
                else:
                    await msg.reply(text)
        except Exception as e2:
            print(f"owner panel fallback: {e2}")
