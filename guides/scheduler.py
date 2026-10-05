# ==========================================
# Auto Guide Scheduler
# فاصله تصادفی بین ۲ تا ۳ ساعت برای هر گروه
# ==========================================

import asyncio
import random
import time
import logging

from config import GUIDE_INTERVAL_MIN, GUIDE_INTERVAL_MAX
from database.groups import get_groups_for_guide, update_guide_last_sent, set_guide_settings
from database.guides import get_sent_guide_keys, mark_guide_sent, clear_guide_history

logger = logging.getLogger("meowbot.guide")

GUIDES = [
    ("meow", "🐱 می‌دونستی با نوشتن «میو» امتیاز می‌گیری؟"),
    ("pet", "🐾 می‌دونستی می‌تونی برای خودت Pet داشته باشی؟ توی پیوی ربات حرف بزن!"),
    ("battle", "⚔️ می‌دونستی می‌تونی با اعضای گروه Battle کنی؟"),
    ("coin", "💰 Meow Coin رو می‌تونی در Shop و Bank استفاده کنی!"),
    ("profile", "👤 با نوشتن «پروفایل» وضعیت خودت رو ببین."),
    ("rank", "🏆 با «رنکینگ» ببین کی اول فصله!"),
    ("gif", "🎬 روی یک GIF ریپلای کن و بنویس: گیف متن دلخواه"),
    ("bank", "🏦 سیستم Bank داری؛ می‌تونی سپرده بذاری و انتقال بدی."),
    ("season", "📅 هر فصل ۱۵ روزه است. فقط رنکینگ فصل ریست می‌شه، سکه‌هات می‌مونه!"),
    ("daily", "🎁 هر روز Daily Reward بگیر و Streak بساز."),
    ("mission", "🎯 مأموریت‌های روزانه انجام بده و جایزه بگیر."),
    ("achieve", "🏆 Achievementها رو کامل کن و پاداش بگیر."),
    ("fact", "🧠 Fact جالب: گربه‌ها حدود ۱۶ ساعت در روز می‌خوابن 😴"),
    ("fun1", "😹 پیشی‌ها امروز حوصله‌شون سر رفته... یک میو بزن!"),
    ("fun2", "✨ می‌دونستی Responseهای MeowBot تکراری نیستن؟"),
    ("gym", "🏋️ باشگاه میویی رو ارتقا بده تا تو Battle قوی‌تر بشی!"),
    ("transfer", "💸 می‌تونی به دوستات Coin انتقال بدی."),
    ("guide_tip", "💡 پیام‌های راهنما حدود هر ۲ تا ۳ ساعت یک‌بار می‌آن (تصادفی)."),
    ("settings", "⚙️ ادمین گروه می‌تونه از پیوی ربات با دستور «تنظیم گروه» فعالیت ربات رو مدیریت کنه."),
]


def random_guide_interval() -> int:
    """ثانیه — بین ۲ تا ۳ ساعت."""
    lo = int(globals().get("GUIDE_INTERVAL_MIN", 7200))
    hi = int(globals().get("GUIDE_INTERVAL_MAX", 10800))
    try:
        from config import GUIDE_INTERVAL_MIN as A, GUIDE_INTERVAL_MAX as B
        lo, hi = int(A), int(B)
    except Exception:
        pass
    if hi < lo:
        hi = lo
    return random.randint(lo, hi)


async def pick_guide(chat_id: str) -> tuple:
    sent = await get_sent_guide_keys(chat_id)
    available = [g for g in GUIDES if g[0] not in sent]
    if not available:
        await clear_guide_history(chat_id)
        available = list(GUIDES)
    chosen = random.choice(available)
    await mark_guide_sent(chat_id, chosen[0])
    return chosen


async def guide_loop(bot):
    logger.info("💡 Auto Guide loop started (random 2–3h per group)")
    while True:
        try:
            await asyncio.sleep(120)  # هر ۲ دقیقه چک
            now = time.time()
            groups = await get_groups_for_guide()
            for g in groups:
                cid = g["chat_id"]
                interval = int(g.get("guide_interval") or 0)
                if interval <= 0:
                    interval = random_guide_interval()
                last = float(g.get("guide_last_sent") or 0)
                if last > 0 and (now - last) < interval:
                    continue
                # اگر هرگز ارسال نشده، یک تأخیر اولیه تصادفی بگذار (از اسپم در استارت جلوگیری)
                if last <= 0:
                    # اولین ارسال را بین ۳۰ تا ۹۰ دقیقه بعد از دیدن گروه انجام بده
                    await update_guide_last_sent(cid, now - random_guide_interval() + random.randint(1800, 5400))
                    continue
                try:
                    key, text = await pick_guide(cid)
                    msg = f"💡 **راهنمای MeowBot**\n\n{text}"
                    await bot.send_message(cid, msg)
                    # فاصله بعدی تصادفی ۲–۳ ساعت
                    nxt = random_guide_interval()
                    await set_guide_settings(cid, interval=nxt)
                    await update_guide_last_sent(cid, now)
                    logger.info(f"Guide sent to {cid}: {key} (next in {nxt}s)")
                except Exception as e:
                    logger.warning(f"Guide fail {cid}: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Guide loop error: {e}")
            await asyncio.sleep(60)


_task = None

def start_guide_scheduler(bot):
    global _task
    try:
        loop = asyncio.get_event_loop()
        if _task is None or _task.done():
            _task = loop.create_task(guide_loop(bot))
    except Exception as e:
        logger.error(f"start_guide_scheduler: {e}")
