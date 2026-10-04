# ==========================================
# 🪟 Main Menu + Pages (Glass)
# ==========================================

from config import BOT_NAME, BOT_VERSION, SEASON_DAYS
from utils.keyboards import (
    main_menu_kb, profile_kb, rank_kb, back_main_kb, games_kb,
)
from database.users import get_user, get_top_users, get_dashboard_stats
from database.seasons import get_active_season
from database.achievements import get_user_achievements
from database.missions import get_user_missions
from database.pets import get_pet


WELCOME = (
    f"🐱 سلام! به **{BOT_NAME}** خوش اومدی\n"
    f"━━━━━━━━━━━━━━\n"
    f"از دکمه‌های شیشه‌ای زیر استفاده کن ✨\n"
    f"نسخه `{BOT_VERSION}`"
)

ABOUT = (
    f"🐱 **{BOT_NAME}**\n"
    f"━━━━━━━━━━━━━━\n"
    f"ربات اجتماعی و بازی برای بله\n"
    f"ساخته‌شده با ❤️\n"
    f"👨‍💻 @commander04\n"
    f"نسخه `{BOT_VERSION}`"
)

GUIDE = (
    "📖 **راهنما**\n"
    "━━━━━━━━━━━━━━\n"
    "🐱 بنویس **میو** → امتیاز فصل\n"
    "👤 **پروفایل** از منو\n"
    "🐾 **Pet** بساز و مراقبت کن\n"
    "⚔️ **Battle** با بقیه\n"
    "🏦 **بانک** واریز/برداشت/انتقال\n"
    "🎮 **بازی‌ها** و کوین جایزه\n"
    "📅 فصل‌ها ۱۵ روزه‌اند؛ فقط رنکینگ فصل ریست می‌شود\n"
    "💡 راهنمای خودکار هر ساعت در گروه\n"
    "━━━━━━━━━━━━━━\n"
    "تقریباً همه‌چیز با دکمه انجام می‌شود 🪟"
)


async def profile_text(user_id, first_name=""):
    u = await get_user(user_id)
    if not u:
        return "❌ اول یک میو بزن یا از منو شروع کن!", main_menu_kb()
    pet = await get_pet(user_id)
    pet_line = "ندارد"
    if pet and not pet.get("awaiting_name"):
        pet_line = f"{pet.get('pet_name')} (Lv.{pet.get('level',1)})"
    return (
        f"🐱 **پروفایل {first_name or u.get('first_name') or 'کاربر'}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"⭐ Level: `{u.get('level',1)}` | XP: `{u.get('xp',0)}`\n"
        f"🐾 امتیاز فصل: `{u.get('meow_points',0)}`\n"
        f"🪙 Meow Coin: `{u.get('meow_coins',0)}`\n"
        f"🏋️ باشگاه: `{u.get('gym_level',1)}`\n"
        f"⚔️ نبرد: `{u.get('total_battles',0)}` "
        f"(W:`{u.get('total_wins',0)}` L:`{u.get('total_losses',0)}`)\n"
        f"📊 کل میو: `{u.get('total_meows',0)}`\n"
        f"🔥 استریک روزانه: `{u.get('daily_streak',0)}`\n"
        f"🐾 Pet: {pet_line}\n"
        f"━━━━━━━━━━━━━━"
    ), profile_kb()


async def ranking_text(kind="points"):
    if kind == "points":
        top = await get_top_users(limit=10)
        title = "🐾 رنکینگ امتیاز فصل"
        key = "meow_points"
    elif kind == "coins":
        from database.pool import fetch
        rows = await fetch(
            "SELECT user_id, first_name, username, meow_coins AS meow_points FROM users "
            "ORDER BY meow_coins DESC LIMIT 10"
        )
        top = [dict(r) for r in rows]
        title = "🪙 رنکینگ سکه"
        key = "meow_points"
    elif kind == "wins":
        from database.pool import fetch
        rows = await fetch(
            "SELECT user_id, first_name, username, total_wins AS meow_points FROM users "
            "ORDER BY total_wins DESC LIMIT 10"
        )
        top = [dict(r) for r in rows]
        title = "⚔️ رنکینگ برد"
        key = "meow_points"
    else:
        from database.pool import fetch
        rows = await fetch(
            "SELECT user_id, first_name, username, gym_level AS meow_points FROM users "
            "ORDER BY gym_level DESC LIMIT 10"
        )
        top = [dict(r) for r in rows]
        title = "🏋️ رنکینگ باشگاه"
        key = "meow_points"

    if not top:
        return "📭 هنوز کسی نیست. میو کنید!", rank_kb()
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"🏆 **{title}**\n━━━━━━━━━━━━━━"]
    for i, u in enumerate(top):
        m = medals[i] if i < 3 else f"`{i+1}.`"
        name = u.get("first_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{m} {name} — `{u.get(key, 0)}`")
    return "\n".join(lines), rank_kb()


async def season_text():
    s = await get_active_season()
    if not s:
        return f"📅 فصل فعالی نیست.\nمدت هر فصل: `{SEASON_DAYS}` روز", back_main_kb()
    return (
        f"📅 **فصل فعلی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"شماره: `{s.get('season_number')}`\n"
        f"شروع: `{s.get('start_date')}`\n"
        f"پایان: `{s.get('end_date')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚠️ در پایان فصل فقط امتیاز رنکینگ ریست می‌شود."
    ), back_main_kb()


async def missions_text(user_id):
    daily = await get_user_missions(user_id, "daily")
    lines = ["🎯 **مأموریت‌های روزانه**\n━━━━━━━━━━━━━━"]
    if not daily:
        lines.append("فعلاً مأموریتی نیست.")
    for m in daily:
        done = "✅" if m.get("completed") else "▫️"
        lines.append(f"{done} {m.get('name')} (`{m.get('progress',0)}/{m.get('condition_value')}`)")
        lines.append(f"   🎁 {m.get('reward_coins',0)}🪙 + {m.get('reward_xp',0)}XP")
    return "\n".join(lines), back_main_kb()


async def achieve_text(user_id):
    items = await get_user_achievements(user_id)
    lines = ["🏅 **دستاوردها**\n━━━━━━━━━━━━━━"]
    for a in items[:15]:
        icon = a.get("icon") or "🏆"
        done = "✅" if a.get("completed") else "🔒"
        lines.append(f"{done} {icon} {a.get('name')} (`{a.get('progress',0)}/{a.get('condition_value')}`)")
    return "\n".join(lines), back_main_kb()


async def daily_reward(user_id):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from database.users import update_user, add_meow_coins
    from config import DAILY_REWARD_BASE, DAILY_STREAK_BONUS
    TEHRAN = ZoneInfo("Asia/Tehran")
    today = datetime.now(TEHRAN).strftime("%Y-%m-%d")
    u = await get_user(user_id)
    if not u:
        return "❌ اول ثبت‌نام کن (یک میو بزن).", back_main_kb()
    if u.get("last_daily") == today:
        return f"🎁 امروز جایزه گرفتی!\n🔥 استریک: `{u.get('daily_streak',0)}`", back_main_kb()
    streak = int(u.get("daily_streak") or 0) + 1
    reward = DAILY_REWARD_BASE + (streak - 1) * DAILY_STREAK_BONUS
    await add_meow_coins(user_id, reward)
    await update_user(user_id, last_daily=today, daily_streak=streak)
    return (
        f"🎁 **جایزه روزانه**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔥 استریک روز `{streak}`\n"
        f"🪙 +{reward} Meow Coin\n"
        f"━━━━━━━━━━━━━━\n"
        f"فردا دوباره بیا!"
    ), back_main_kb()


async def handle_menu_callback(user_id, data, first_name=""):
    if data == "menu:main":
        return WELCOME, main_menu_kb()
    if data == "menu:close":
        return "🐱 منو بسته شد. هر وقت خواستی /start بزن!", None
    if data == "menu:profile":
        return await profile_text(user_id, first_name)
    if data == "menu:about":
        return ABOUT, back_main_kb()
    if data == "menu:guide":
        return GUIDE, back_main_kb()
    if data == "menu:rank":
        return await ranking_text("points")
    if data == "menu:season":
        return await season_text()
    if data == "menu:missions":
        return await missions_text(user_id)
    if data == "menu:achieve":
        return await achieve_text(user_id)
    if data == "menu:daily":
        return await daily_reward(user_id)
    if data == "act:meow_info":
        return (
            "🐱 برای گرفتن امتیاز، در گروه یا پیوی بنویس:\n"
            "**میو** / meow / میاو\n\n"
            "هر ۵ دقیقه یک بار."
        ), main_menu_kb()
    if data.startswith("rank:"):
        kind = data.split(":")[1]
        return await ranking_text(kind)
    return WELCOME, main_menu_kb()
