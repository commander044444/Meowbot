# ==========================================
# 🐱 MeowBot - Seasons System
# ==========================================
# فصل‌های ۱۵ روزه با جوایز شروع، رنکینگ روزانه،
# هشدار نزدیک پایان و ریست در پایان فصل.
# زمان‌بندی: هر روز ساعت ۰۰:۰۰ به وقت ایران/تهران
# ==========================================

import asyncio
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from config import (
    OWNER_ID,
    SEASON_DAYS,
)

from database import (
    get_active_season,
    create_season,
    close_active_season,
    reset_meow_points,
    add_meow_points_global,
    add_meow_coins_global,
    get_next_season_number,
    get_all_groups,
    get_global_top_users,
    get_top_daily_meowers,
    save_season_result,
)


TEHRAN = ZoneInfo("Asia/Tehran")

# جوایز شروع فصل
START_POINTS = 40
START_COINS = 20

# تعداد نمایش در رنکینگ روزانه / نهایی
TOP_LIMIT = 10


# ==========================================
# Helpers
# ==========================================

def tehran_now():
    return datetime.now(TEHRAN)


def tehran_today_str():
    return tehran_now().strftime("%Y-%m-%d")


def parse_date(date_str):
    """Parse YYYY-MM-DD or ISO datetime to date in Tehran."""
    if not date_str:
        return None
    try:
        if "T" in str(date_str):
            dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TEHRAN)
            else:
                dt = dt.astimezone(TEHRAN)
            return dt.date()
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def season_day_number(season):
    """Current day number of the active season (1-based)."""
    if not season:
        return 0
    start = parse_date(season["start_date"])
    if not start:
        return 0
    today = tehran_now().date()
    delta = (today - start).days + 1
    return max(1, delta)


def format_top_daily(day_date, limit=TOP_LIMIT):
    """متن رنکینگ برترین میوکنندگان یک روز."""
    rows = get_top_daily_meowers(day_date, limit=limit)
    if not rows:
        return (
            "🏆 برترین میوکنندگان امروز:\n\n"
            "هنوز کسی امروز میو نکرده! 🐱"
        )

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 برترین میوکنندگان امروز:", ""]
    for i, row in enumerate(rows, start=1):
        name = (row["first_name"] or "Unknown") if "first_name" in row.keys() else "Unknown"
        username = (row["username"] or "") if "username" in row.keys() else ""
        points = int(row["points_earned"] or 0)
        count = int(row["meow_count"] or 0)
        medal = medals.get(i, f"{i}.")
        label = f"@{username}" if username else name
        lines.append(
            f"{medal} {label}\n"
            f"   🐾 {points} امتیاز امروز | {count} میو"
        )
    return "\n".join(lines)


def format_global_ranking(limit=TOP_LIMIT):
    """متن رنکینگ کلی فصل."""
    users = get_global_top_users(limit=limit)
    if not users:
        return "🏆 رنکینگ فصل:\n\nهنوز کسی امتیاز نگرفته! 🐱"

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 رنکینگ نهایی فصل:", ""]
    for i, u in enumerate(users, start=1):
        name = u["first_name"] or "Unknown"
        username = u["username"] or ""
        points = int(u["meow_points"] or 0)
        level = int(u["gym_level"] or 1)
        medal = medals.get(i, f"{i}.")
        label = f"@{username}" if username else name
        lines.append(
            f"{medal} {label}\n"
            f"   🐾 {points} Meow Point | 🏋️ Lv.{level}"
        )
    return "\n".join(lines)


# ==========================================
# Broadcast
# ==========================================

async def broadcast_to_all(bot, text, also_owner=True):
    """ارسال پیام همگانی به تمام گروه‌های ثبت‌شده (+ مالک)."""
    sent = 0
    failed = 0
    try:
        groups = get_all_groups()
    except Exception as e:
        print(f"❌ seasons: load groups failed: {e}")
        groups = []

    for group in groups:
        group_id = group["chat_id"]
        try:
            await bot.send_message(group_id, text)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ seasons broadcast fail {group_id}: {e}")

    if also_owner:
        try:
            await bot.send_message(OWNER_ID, text)
            sent += 1
        except Exception as e:
            print(f"❌ seasons owner notify fail: {e}")

    return sent, failed


# ==========================================
# Start / End Season
# ==========================================

async def start_new_season(bot, reply_message=None):
    """
    شروع فصل جدید:
    - بستن فصل قبلی در صورت وجود
    - ساخت فصل جدید
    - دادن ۴۰ پوینت + ۲۰ کوین به همه کاربران
    - پیام همگانی روز ۱
    """
    active = get_active_season()
    if active:
        close_active_season()

    season_num = get_next_season_number()
    now = tehran_now()
    start_date = now.strftime("%Y-%m-%d")
    end_dt = now.date() + timedelta(days=SEASON_DAYS - 1)
    end_date = end_dt.strftime("%Y-%m-%d")

    create_season(season_num, start_date, end_date)

    # جوایز شروع به همه
    try:
        pts = add_meow_points_global(START_POINTS)
        cns = add_meow_coins_global(START_COINS)
    except Exception as e:
        print(f"❌ seasons reward fail: {e}")
        pts, cns = 0, 0

    msg = (
        f"🎉🐱 فصل جدید شروع شد!\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 فصل شماره: {season_num}\n"
        f"📆 مدت فصل: {SEASON_DAYS} روز\n"
        f"🗓 امروز: روز ۱ از {SEASON_DAYS}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🎁 به تمام بازیکن‌ها اهدا شد:\n"
        f"🐾 +{START_POINTS} میو پوینت\n"
        f"🪙 +{START_COINS} میو کوین\n\n"
        f"✨ برو میو کن و رنک ۱ شو! 🦦\n"
        f"موفق باشید پیشی‌ها 🎀🐱"
    )

    sent, failed = await broadcast_to_all(bot, msg)

    report = (
        f"✅ فصل {season_num} شروع شد!\n\n"
        f"🎁 کاربران دریافت‌کننده پوینت: {pts}\n"
        f"🎁 کاربران دریافت‌کننده کوین: {cns}\n"
        f"📢 ارسال: ✅{sent} / ❌{failed}"
    )
    if reply_message:
        try:
            await reply_message.reply(report)
        except Exception:
            pass
    else:
        try:
            await bot.send_message(OWNER_ID, report)
        except Exception:
            pass

    print(f"✅ Season {season_num} started. Day 1/{SEASON_DAYS}")
    return True


async def end_season(bot, reason="manual", reply_message=None):
    """
    پایان فصل:
    - نمایش رنکینگ نهایی
    - ذخیره نتایج
    - ریست پوینت‌ها
    - بستن فصل
    - پیام تشکر + تییز فصل بعد
    """
    active = get_active_season()
    if not active:
        text = "❌ هیچ فصل فعالی وجود ندارد."
        if reply_message:
            await reply_message.reply(text)
        return False

    season_id = active["id"]
    season_num = active["season_number"]

    ranking_text = format_global_ranking(limit=TOP_LIMIT)

    # ذخیره نتایج برتر
    tops = get_global_top_users(limit=TOP_LIMIT)
    for i, u in enumerate(tops, start=1):
        try:
            save_season_result(
                season_id=season_id,
                user_id=u["user_id"],
                meow_points=int(u["meow_points"] or 0),
                final_rank=i,
            )
        except Exception as e:
            print(f"❌ save_season_result: {e}")

    close_active_season()
    try:
        reset_meow_points()
    except Exception as e:
        print(f"❌ reset_meow_points: {e}")

    if reason == "manual":
        header = "🏁 این فصل به پایان رسید (پایان دستی توسط ادمین)!"
    else:
        header = "🏁 این فصل به پایان رسید!"

    msg = (
        f"{header}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 فصل شماره: {season_num}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{ranking_text}\n\n"
        f"🙏 از تمام پلیرهای عزیز تشکر می‌کنیم که با میوهای قشنگتون این فصل رو ساختید 🐱💗\n\n"
        f"🔄 همه چیز ریست شد.\n"
        f"🚀 فصل‌های بعدی قراره با کلی آپدیت و قابلیت‌های بیشتر بیاد...\n"
        f"منتظر باشید! 🤓✨"
    )

    sent, failed = await broadcast_to_all(bot, msg)

    report = (
        f"✅ فصل {season_num} تمام شد.\n"
        f"📢 ارسال: ✅{sent} / ❌{failed}"
    )
    if reply_message:
        try:
            await reply_message.reply(report)
        except Exception:
            pass
    else:
        try:
            await bot.send_message(OWNER_ID, report)
        except Exception:
            pass

    print(f"✅ Season {season_num} ended ({reason})")
    return True


# ==========================================
# Daily Tick (00:00 Tehran)
# ==========================================

async def run_daily_tick(bot):
    """
    اجرای منطق روزانه فصل در نیمه‌شب تهران.
    - روزهای بعد: اعلام گذشت روز قبل + برترین‌ها + روز جدید
    - نزدیک پایان: هشدار
    - روز آخر / بعد از آن: پایان فصل
    """
    active = get_active_season()
    if not active:
        print("ℹ️ seasons daily: no active season")
        return

    day = season_day_number(active)
    season_num = active["season_number"]
    yesterday = (tehran_now().date() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"🌙 seasons daily tick | season={season_num} day={day}/{SEASON_DAYS}")

    # اگر از مدت فصل گذشته → پایان
    if day > SEASON_DAYS:
        await end_season(bot, reason="auto")
        return

    top_yesterday = format_top_daily(yesterday, limit=TOP_LIMIT)

    if day == 1:
        msg = (
            f"🌙 روز اول فصل {season_num} در حال اجراست!\n\n"
            f"🗓 روز ۱ از {SEASON_DAYS}\n"
            f"برو میو کن 🐱✨"
        )
        await broadcast_to_all(bot, msg)
        return

    remaining = SEASON_DAYS - day + 1

    warning = ""
    if remaining <= 3 and remaining > 0:
        warning = (
            f"\n\n⚠️ تنها {remaining} روز تا پایان فصل باقی مونده!\n"
            f"ببینم می‌تونی رنک ۱ بشی یا نه 🦦"
        )

    if day == SEASON_DAYS:
        msg = (
            f"🌙 امروز هم گذشت...\n\n"
            f"{top_yesterday}\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 روز جدید شروع شد\n"
            f"🗓 روز {day}/{SEASON_DAYS} — آخرین روز فصل!\n"
            f"━━━━━━━━━━━━━━"
            f"{warning}\n\n"
            f"🔥 آخرین شانس برای رنک ۱! 🐱✨"
        )
    elif day == SEASON_DAYS - 1:
        global_rank = format_global_ranking(limit=TOP_LIMIT)
        msg = (
            f"🌙 امروز هم گذشت...\n\n"
            f"{top_yesterday}\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 روز جدید شروع شد\n"
            f"🗓 روز {day}/{SEASON_DAYS}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{global_rank}\n\n"
            f"⚠️ تنها ۱ روز تا پایان فصل باقی مونده!\n"
            f"ببینم می‌تونی رنک ۱ بشی یا نه 🦦\n\n"
            f"این فصل تموم می‌شه... همه چیز ریست می‌شه و فصل بعد با کلی آپدیت میاد 🤓✨"
        )
    else:
        msg = (
            f"🌙 امروز هم گذشت...\n\n"
            f"{top_yesterday}\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 روز جدید شروع شد\n"
            f"🗓 روز {day}/{SEASON_DAYS}\n"
            f"━━━━━━━━━━━━━━"
            f"{warning}\n\n"
            f"ادامه بده پیشی‌ها! 🐱🎀"
        )

    await broadcast_to_all(bot, msg)


# ==========================================
# Scheduler Loop
# ==========================================

def seconds_until_next_midnight_tehran():
    now = tehran_now()
    tomorrow = now.date() + timedelta(days=1)
    target = datetime.combine(tomorrow, dtime(0, 0, 5), tzinfo=TEHRAN)
    return max(1, (target - now).total_seconds())


async def season_scheduler_loop(bot):
    """حلقه پس‌زمینه: هر شب نیمه‌شب تهران daily tick را اجرا می‌کند."""
    print("🌙 Season scheduler started (Asia/Tehran midnight)")
    while True:
        try:
            wait = seconds_until_next_midnight_tehran()
            print(f"🌙 seasons: sleeping {wait:.0f}s until next Tehran midnight")
            await asyncio.sleep(wait)
            await run_daily_tick(bot)
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            print("🌙 Season scheduler cancelled")
            break
        except Exception as e:
            print(f"❌ Season scheduler error: {e}")
            await asyncio.sleep(60)


_scheduler_task = None


def start_season_scheduler(bot):
    """از on_ready صدا زده می‌شود."""
    global _scheduler_task
    try:
        loop = asyncio.get_event_loop()
        if _scheduler_task is None or _scheduler_task.done():
            _scheduler_task = loop.create_task(season_scheduler_loop(bot))
            print("✅ Season scheduler task created")
    except Exception as e:
        print(f"❌ Could not start season scheduler: {e}")


# ==========================================
# Admin Commands (Private only)
# ==========================================

def is_season_command(text):
    if not text:
        return False
    t = text.strip()
    return t in ("آغاز فصل جدید", "پایان فصل")


async def handle_season_command(bot, message, text, user_id, private_chat):
    """
    هندل دستورات ادمین فصل.
    فقط در پیوی و فقط برای OWNER_ID.
    """
    if not private_chat:
        return False

    if int(user_id) != int(OWNER_ID):
        return False

    t = text.strip()

    if t == "آغاز فصل جدید":
        active = get_active_season()
        if active:
            await message.reply(
                f"⚠️ یک فصل فعال وجود دارد (فصل {active['season_number']}).\n"
                f"ابتدا «پایان فصل» را بزن یا صبر کن تا تموم شود.\n\n"
                f"اگر می‌خوای اجباری فصل جدید شروع شود، اول پایان بده."
            )
            return True

        await message.reply("⏳ در حال شروع فصل جدید...")
        await start_new_season(bot, reply_message=message)
        return True

    if t == "پایان فصل":
        active = get_active_season()
        if not active:
            await message.reply("❌ هیچ فصل فعالی برای پایان دادن وجود ندارد.")
            return True

        await message.reply("⏳ در حال پایان دادن به فصل...")
        await end_season(bot, reason="manual", reply_message=message)
        return True

    return False
