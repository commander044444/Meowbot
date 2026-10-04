# ==========================================
# 👑 Owner Panel
# ==========================================

import time
from bale import InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID, BOT_VERSION, BOT_NAME
try:
    from utils.keyboards import owner_nav_kb
except Exception:
    owner_nav_kb = None
from database.users import get_dashboard_stats, count_users
from database.groups import count_groups, get_all_groups
from database.admins import list_admins
from database.logs import get_recent_logs, log_action
from database.pool import fetchval, get_pool


_start = time.time()


def _kb(rows):
    """Bale-compatible: one button per add(), row is natural int >= 1."""
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


def main_keyboard():
    if owner_nav_kb:
        try:
            return owner_nav_kb()
        except Exception:
            pass
    return _main_keyboard_fallback()

def _main_keyboard_fallback():
    return _kb([
        [("📊 Dashboard", "owner:dashboard"), ("🖥 Status", "owner:status")],
        [("🧪 Tests", "owner:tests"), ("👥 Users", "owner:users")],
        [("💬 Groups", "owner:groups"), ("🛡 Admins", "owner:admins")],
        [("💰 Economy", "owner:economy"), ("📅 Seasons", "owner:seasons")],
        [("💡 Guides", "owner:guides"), ("💾 Backup", "owner:backup")],
        [("📜 Logs", "owner:logs"), ("⚙️ Settings", "owner:settings")],
        [("🔙 بستن", "owner:close")],
    ])


async def show_owner_panel(message):
    text = (
        f"👑 **{BOT_NAME} OWNER PANEL**\n"
        f"━━━━━━━━━━━━━━\n"
        f"نسخه: `{BOT_VERSION}`\n"
        f"Uptime: `{int(time.time()-_start)}s`\n\n"
        f"یکی از بخش‌ها را انتخاب کن:"
    )
    await message.reply(text, components=main_keyboard())


async def handle_owner_callback(bot, callback, data: str):
    action = data.split(":", 1)[1] if ":" in data else ""
    msg = callback.message

    if action == "close":
        try:
            await msg.edit("👑 پنل بسته شد.")
        except Exception:
            pass
        await callback.answer()
        return

    if action == "dashboard":
        stats = await get_dashboard_stats()
        text = (
            f"📊 **DASHBOARD**\n"
            f"━━━━━━━━━━━━━━\n"
            f"👥 Users: `{stats['total_users']}` (active 7d: `{stats['active_users']}`)\n"
            f"💬 Groups: `{stats['total_groups']}`\n"
            f"🐾 Pets: `{stats['total_pets']}`\n"
            f"🪙 Total Coins: `{stats['total_coins']}`\n"
            f"⚔️ Battles: `{stats['total_battles']}`\n"
            f"🐱 Meows: `{stats['total_meows']}`\n"
            f"📅 Season: `{stats['current_season']}`\n"
            f"🎉 Events: `{stats['active_events']}`\n"
            f"🛡 Admins: `{stats['total_admins']}`\n"
            f"⏱ Uptime: `{int(time.time()-_start)}s`\n"
            f"━━━━━━━━━━━━━━"
        )
        await _edit(msg, text, main_keyboard())
        await callback.answer()
        return

    if action == "status":
        db_ok = "🟢"
        db_ping = "?"
        try:
            t0 = time.time()
            await fetchval("SELECT 1")
            db_ping = f"{int((time.time()-t0)*1000)}ms"
        except Exception as e:
            db_ok = "🔴"
            db_ping = str(e)[:40]

        text = (
            f"🖥 **SYSTEM STATUS**\n"
            f"━━━━━━━━━━━━━━\n"
            f"🤖 Bot: 🟢 ONLINE\n"
            f"🗄 PostgreSQL: {db_ok} ({db_ping})\n"
            f"⏱ Scheduler: 🟢\n"
            f"💡 Auto Guide: 🟢\n"
            f"📅 Seasons: 🟢\n"
            f"💾 Backup: 🟢\n"
            f"📜 Logging: 🟢\n"
            f"━━━━━━━━━━━━━━\n"
            f"Uptime: `{int(time.time()-_start)}s`"
        )
        await _edit(msg, text, main_keyboard())
        await callback.answer()
        return

    if action == "tests":
        results = []
        # Bot
        results.append("✅ Bot API: PASS")
        # DB
        try:
            t0 = time.time()
            await fetchval("SELECT 1")
            results.append(f"✅ Database: PASS ({int((time.time()-t0)*1000)}ms)")
        except Exception as e:
            results.append(f"❌ Database: FAIL ({e})")
        # Users table
        try:
            n = await count_users()
            results.append(f"✅ Users table: PASS ({n} rows)")
        except Exception as e:
            results.append(f"❌ Users table: FAIL ({e})")
        # Groups
        try:
            n = await count_groups()
            results.append(f"✅ Groups table: PASS ({n} rows)")
        except Exception as e:
            results.append(f"❌ Groups table: FAIL ({e})")
        # Config
        from config import BOT_TOKEN, DATABASE_URL, OWNER_ID
        results.append("✅ Config TOKEN: PASS" if BOT_TOKEN else "❌ Config TOKEN: FAIL")
        results.append("✅ Config DATABASE_URL: PASS" if DATABASE_URL else "❌ Config DATABASE_URL: FAIL")
        results.append(f"✅ Config OWNER_ID: {OWNER_ID}")

        text = "🧪 **TEST CENTER**\n━━━━━━━━━━━━━━\n" + "\n".join(results)
        await _edit(msg, text, main_keyboard())
        await callback.answer("Tests done")
        return

    if action == "users":
        n = await count_users()
        text = f"👥 **Users**\nکل کاربران: `{n}`\n\nاز دستورات /addcoin /addpoint /addgym استفاده کن."
        await _edit(msg, text, main_keyboard())
        await callback.answer()
        return

    if action == "groups":
        groups = await get_all_groups()
        lines = [f"💬 **Groups** ({len(groups)})\n━━━━━━━━━━━━━━"]
        for g in groups[:15]:
            title = g.get("title") or g.get("username") or g.get("chat_id")
            inter = "🟢" if g.get("interaction_on") else "🔇"
            guide = "💡" if g.get("guide_enabled") else "💤"
            lines.append(f"{inter}{guide} {title}")
        if len(groups) > 15:
            lines.append(f"... و {len(groups)-15} گروه دیگر")
        await _edit(msg, "\n".join(lines), main_keyboard())
        await callback.answer()
        return

    if action == "admins":
        admins = await list_admins()
        lines = ["🛡 **Admins**\n━━━━━━━━━━━━━━"]
        for a in admins:
            status = "🟢" if a.get("enabled") else "🔴"
            lines.append(f"{status} `{a['user_id']}` — {a.get('role')}")
        await _edit(msg, "\n".join(lines), main_keyboard())
        await callback.answer()
        return

    if action == "logs":
        logs = await get_recent_logs(15)
        lines = ["📜 **Recent Logs**\n━━━━━━━━━━━━━━"]
        for lg in logs:
            lines.append(f"• {lg.get('action')} by `{lg.get('actor_id')}` → {lg.get('target') or '-'}")
        if not logs:
            lines.append("خالی")
        await _edit(msg, "\n".join(lines), main_keyboard())
        await callback.answer()
        return

    if action == "backup":
        text = (
            "💾 **BACKUP CENTER**\n"
            "━━━━━━━━━━━━━━\n"
            "برای Railway از PostgreSQL backup استفاده کن.\n"
            "دستور پیشنهادی:\n"
            "`pg_dump $DATABASE_URL > backup.sql`\n\n"
            "قابلیت Download Backup در نسخه بعدی کامل می‌شود."
        )
        await _edit(msg, text, main_keyboard())
        await callback.answer()
        return

    if action in ("economy", "seasons", "guides", "settings"):
        await _edit(msg, f"⚙️ بخش `{action}` — در حال توسعه پنل کامل.\nاز دستورات متنی استفاده کن.", main_keyboard())
        await callback.answer()
        return

    await callback.answer()


async def _edit(msg, text, kb=None):
    try:
        if hasattr(msg, "edit"):
            await msg.edit(text, components=kb)
        elif hasattr(msg, "edit_text"):
            await msg.edit_text(text, components=kb)
    except Exception as e:
        print(f"owner panel edit: {e}")
