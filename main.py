# ==========================================
# 🐱 MeowBot v2.0 - Main (PostgreSQL + Modular)
# ==========================================
# Bale Bot | Railway-ready | Production
# ==========================================

import asyncio
import logging
import time
import traceback
from datetime import datetime

from bale import Bot, Message, CallbackQuery

from config import BOT_TOKEN, OWNER_ID, BOT_NAME, BOT_VERSION

from database import init_database
from database.users import (
    create_user, get_user, get_dashboard_stats,
    admin_set_meow_coins, admin_set_meow_points, admin_set_gym_level,
)
from database.groups import register_group, get_interaction, set_interaction
from database.admins import is_owner, has_permission, list_admins
from database.logs import log_action
from database.achievements import seed_achievements
from database.missions import seed_missions
from database.inventory import seed_shop

from core.meow import is_meow, is_allowed_group, register_meow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("meowbot")

bot = Bot(token=BOT_TOKEN)
_start_time = time.time()


def uptime_str() -> str:
    s = int(time.time() - _start_time)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m}m {sec}s"


# ==========================================
# Startup
# ==========================================

@bot.event
async def on_ready():
    print("=" * 55)
    print(f"🐱 {BOT_NAME} v{BOT_VERSION} ONLINE")
    print("=" * 55)
    try:
        await init_database()
        await seed_achievements()
        await seed_missions()
        await seed_shop()
        print("✅ Database + seeds ready")
    except Exception as e:
        print(f"❌ Database init failed: {e}")
        traceback.print_exc()

    # Start background schedulers
    try:
        from guides.scheduler import start_guide_scheduler
        start_guide_scheduler(bot)
        print("✅ Auto Guide scheduler started")
    except Exception as e:
        print(f"⚠️ Guide scheduler: {e}")

    try:
        from seasons.scheduler import start_season_scheduler
        start_season_scheduler(bot)
        print("✅ Season scheduler started")
    except Exception as e:
        print(f"⚠️ Season scheduler: {e}")

    print(f"👑 Owner ID: {OWNER_ID}")
    print("=" * 55)


# ==========================================
# Messages
# ==========================================

@bot.event
async def on_message(message: Message):
    try:
        text = message.text
        if not text:
            return
        text = text.strip()

        chat = message.chat
        chat_id = getattr(chat, "id", None)
        chat_username = getattr(chat, "username", None)
        chat_title = getattr(chat, "title", None) or ""
        author = message.author
        if not author:
            return

        user_id = author.id
        first_name = getattr(author, "first_name", None) or "Unknown"
        username = getattr(author, "username", None) or ""
        private = not (chat_title or chat_username)

        # Register group
        if chat_id and (chat_title or chat_username):
            try:
                await register_group(chat_id, chat_title, chat_username or "")
            except Exception as e:
                logger.warning(f"group register: {e}")

        # Ensure user exists
        try:
            await create_user(user_id, first_name=first_name, username=username, chat_id=chat_id)
        except Exception:
            pass

        # ---------- Start / Menu ----------
        if text in ("/start", "start", "منو", "شروع"):
            welcome = (
                f"🐱 سلام {first_name}!\n\n"
                f"به **{BOT_NAME}** خوش اومدی 🎀\n\n"
                f"✨ می‌تونی:\n"
                f"• میو کنی و امتیاز بگیری\n"
                f"• Pet داشته باشی\n"
                f"• Battle کنی\n"
                f"• کوین جمع کنی و Bank داشته باشی\n"
                f"• در فصل شرکت کنی\n\n"
                f"📖 راهنما رو از منو ببین!\n"
                f"نسخه: {BOT_VERSION}"
            )
            await message.reply(welcome)
            return

        # ---------- Owner Panel ----------
        if text in ("/owner", "owner", "پنل مالک", "👑") and await is_owner(user_id):
            from admin.panel import show_owner_panel
            await show_owner_panel(message)
            return

        # ---------- Admin economy commands ----------
        admin_prefixes = ("/addcoin", "/addpoint", "/addgym", "addcoin", "addpoint", "addgym")
        lower = text.lower()
        for p in admin_prefixes:
            if lower.startswith(p + " ") or lower == p:
                if not await is_owner(user_id):
                    await message.reply("⛔ فقط Owner می‌تواند از این دستور استفاده کند.")
                    return
                parts = text[len(p):].strip().split()
                if len(parts) != 2:
                    await message.reply("❌ فرمت: /addcoin USER_ID AMOUNT")
                    return
                try:
                    tid, delta = int(parts[0]), int(parts[1])
                except ValueError:
                    await message.reply("❌ ID و مقدار باید عدد باشند.")
                    return
                target = await get_user(tid)
                if not target:
                    await message.reply(f"❌ کاربر `{tid}` پیدا نشد.")
                    return
                cmd = p.lstrip("/").lower()
                if cmd == "addcoin":
                    old = int(target.get("meow_coins") or 0)
                    ok, o, n = await admin_set_meow_coins(tid, max(0, old + delta))
                    field = "🪙 Meow Coin"
                elif cmd == "addpoint":
                    old = int(target.get("meow_points") or 0)
                    ok, o, n = await admin_set_meow_points(tid, max(0, old + delta))
                    field = "⭐ Meow Point"
                else:
                    from config import MAX_GYM_LEVEL
                    old = int(target.get("gym_level") or 1)
                    ok, o, n = await admin_set_gym_level(tid, max(1, min(MAX_GYM_LEVEL, old + delta)))
                    field = "🏋️ Gym Level"
                await log_action(user_id, cmd, str(tid), {"delta": delta, "old": o, "new": n})
                await message.reply(
                    f"✅ {field}\n👤 `{tid}`\n📌 قبل: {o}\n📌 بعد: {n}"
                )
                return

        # ---------- Meow ----------
        if is_meow(text):
            if not private and not is_allowed_group(chat_id, chat_username):
                return
            ok, msg, pts = await register_meow(user_id, first_name, username, chat_id)
            await message.reply(msg)
            return

        # ---------- Profile ----------
        if text in ("پروفایل", "profile", "/profile", "پرفایل"):
            u = await get_user(user_id)
            if not u:
                await message.reply("❌ اول یک میو بزن تا ثبت بشی!")
                return
            profile = (
                f"🐱 **پروفایل {first_name}**\n"
                f"━━━━━━━━━━━━━━\n"
                f"⭐ Level: {u.get('level', 1)}\n"
                f"✨ XP: {u.get('xp', 0)}\n"
                f"🐾 Meow Points: {u.get('meow_points', 0)}\n"
                f"🪙 Meow Coins: {u.get('meow_coins', 0)}\n"
                f"🏋️ Gym: {u.get('gym_level', 1)}\n"
                f"⚔️ Battles: {u.get('total_battles', 0)} "
                f"(W:{u.get('total_wins', 0)} L:{u.get('total_losses', 0)})\n"
                f"📊 Total Meows: {u.get('total_meows', 0)}\n"
                f"🔥 Daily Streak: {u.get('daily_streak', 0)}\n"
                f"━━━━━━━━━━━━━━"
            )
            await message.reply(profile)
            return

        # ---------- Ranking ----------
        if text in ("رنکینگ", "رتبه", "ranking", "/rank", "رنک"):
            from database.users import get_top_users
            top = await get_top_users(limit=10)
            if not top:
                await message.reply("📭 هنوز کسی در رنکینگ نیست. میو کنید!")
                return
            lines = ["🏆 **رنکینگ فصل فعلی**\n━━━━━━━━━━━━━━"]
            medals = ["🥇", "🥈", "🥉"]
            for i, u in enumerate(top):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = u.get("first_name") or u.get("username") or str(u["user_id"])
                lines.append(f"{medal} {name} — {u.get('meow_points', 0)} 🐾")
            await message.reply("\n".join(lines))
            return

        # ---------- Interaction toggle (admin in group) ----------
        if text in ("interaction on", "اینترکشن روشن", "/interaction_on"):
            if await has_permission(user_id, "groups.edit") or await is_owner(user_id):
                await set_interaction(chat_id, True)
                await message.reply("✅ Interaction روشن شد.")
            return
        if text in ("interaction off", "اینترکشن خاموش", "/interaction_off"):
            if await has_permission(user_id, "groups.edit") or await is_owner(user_id):
                await set_interaction(chat_id, False)
                await message.reply("🔇 Interaction خاموش شد. (Auto Guide مستقل است)")
            return

        # ---------- Help ----------
        if text in ("راهنما", "help", "/help", "کمک"):
            help_text = (
                "📖 **راهنمای MeowBot**\n"
                "━━━━━━━━━━━━━━\n"
                "🐱 `میو` — امتیاز بگیر\n"
                "👤 `پروفایل` — وضعیت تو\n"
                "🏆 `رنکینگ` — رتبه فصل\n"
                "🐾 Pet — در PV با ربات حرف بزن\n"
                "⚔️ Battle — به‌زودی در منو\n"
                "🏦 Bank — به‌زودی در منو\n"
                "💡 Auto Guide هر ساعت نکته یاد می‌ده\n"
                "━━━━━━━━━━━━━━\n"
                f"نسخه {BOT_VERSION}"
            )
            await message.reply(help_text)
            return

    except Exception as e:
        logger.error(f"on_message error: {e}")
        traceback.print_exc()
        try:
            if int(getattr(message.author, "id", 0)) == int(OWNER_ID):
                await message.reply(f"⚠️ Error: {e}")
        except Exception:
            pass


# ==========================================
# Callbacks
# ==========================================

@bot.event
async def on_callback(callback: CallbackQuery):
    try:
        data = callback.data or ""
        user = callback.from_user
        if not user:
            return
        user_id = user.id

        if data.startswith("owner:"):
            if not await is_owner(user_id):
                await callback.answer("⛔ فقط Owner", show_alert=True)
                return
            from admin.panel import handle_owner_callback
            await handle_owner_callback(bot, callback, data)
            return

        await callback.answer()
    except Exception as e:
        logger.error(f"callback error: {e}")
        traceback.print_exc()


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":
    print(f"Starting {BOT_NAME} v{BOT_VERSION}...")
    bot.run()
