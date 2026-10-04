# ==========================================
# Season Scheduler (Tehran midnight)
# Season Reset ONLY resets ranking points
# ==========================================

import asyncio
import logging
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from config import OWNER_ID, SEASON_DAYS
from database.seasons import (
    get_active_season, create_season, close_active_season, get_next_season_number,
    save_season_result,
)
from database.users import (
    reset_meow_points, add_meow_points_global, add_meow_coins_global,
    get_global_top_users,
)
from database.groups import get_all_groups

TEHRAN = ZoneInfo("Asia/Tehran")
logger = logging.getLogger("meowbot.season")

START_POINTS = 40
START_COINS = 20


def tehran_now():
    return datetime.now(TEHRAN)


async def broadcast(bot, text):
    groups = await get_all_groups()
    sent = failed = 0
    for g in groups:
        try:
            await bot.send_message(g["chat_id"], text)
            sent += 1
        except Exception:
            failed += 1
    try:
        await bot.send_message(OWNER_ID, text)
    except Exception:
        pass
    return sent, failed


async def start_new_season(bot):
    active = await get_active_season()
    if active:
        await close_active_season()

    num = await get_next_season_number()
    now = tehran_now()
    start = now.strftime("%Y-%m-%d")
    end = (now.date() + timedelta(days=SEASON_DAYS - 1)).strftime("%Y-%m-%d")
    await create_season(num, start, end)

    pts = await add_meow_points_global(START_POINTS)
    cns = await add_meow_coins_global(START_COINS)

    msg = (
        f"🎉🐱 فصل جدید شروع شد!\n\n"
        f"📅 فصل شماره: {num}\n"
        f"📆 مدت: {SEASON_DAYS} روز\n\n"
        f"🎁 به همه:\n"
        f"🐾 +{START_POINTS} میو پوینت\n"
        f"🪙 +{START_COINS} میو کوین\n\n"
        f"✨ برو میو کن و رنک ۱ شو!"
    )
    await broadcast(bot, msg)
    logger.info(f"Season {num} started")


async def end_season(bot):
    """
    پایان فصل:
    - ذخیره رنکینگ
    - ریست فقط meow_points (رنکینگ فصل)
    - سکه‌ها، Pet، Achievement، Level دائمی دست نخورده می‌مانند
    """
    active = await get_active_season()
    if not active:
        return

    top = await get_global_top_users(limit=50)
    for i, u in enumerate(top):
        try:
            await save_season_result(
                active["id"], u["user_id"], u.get("meow_points", 0), i + 1
            )
        except Exception as e:
            logger.warning(f"save result: {e}")

    lines = ["🏁 **پایان فصل!**\n━━━━━━━━━━━━━━", "🏆 رنکینگ نهایی:"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top[:10]):
        m = medals[i] if i < 3 else f"{i+1}."
        name = u.get("first_name") or str(u["user_id"])
        lines.append(f"{m} {name} — {u.get('meow_points', 0)} 🐾")
    lines.append("\n⚠️ فقط امتیاز فصل ریست شد.\nسکه، Pet و Achievementها محفوظ‌اند!")

    await broadcast(bot, "\n".join(lines))
    await reset_meow_points()  # ONLY season points
    await close_active_season()
    logger.info("Season ended, ranking points reset only")


async def season_loop(bot):
    logger.info("🌙 Season scheduler started (Tehran)")
    while True:
        try:
            now = tehran_now()
            # sleep until next midnight Tehran
            tomorrow = (now.date() + timedelta(days=1))
            target = datetime.combine(tomorrow, dtime(0, 0), tzinfo=TEHRAN)
            wait = (target - now).total_seconds()
            wait = max(60, wait)
            await asyncio.sleep(wait)

            active = await get_active_season()
            if not active:
                await start_new_season(bot)
                continue

            end_date = active.get("end_date")
            if hasattr(end_date, "isoformat"):
                end_str = end_date.isoformat()
            else:
                end_str = str(end_date)
            today = tehran_now().strftime("%Y-%m-%d")
            if today > end_str:
                await end_season(bot)
                await start_new_season(bot)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Season loop: {e}")
            await asyncio.sleep(300)


_task = None

def start_season_scheduler(bot):
    global _task
    try:
        loop = asyncio.get_event_loop()
        if _task is None or _task.done():
            _task = loop.create_task(season_loop(bot))
    except Exception as e:
        logger.error(f"start_season_scheduler: {e}")
