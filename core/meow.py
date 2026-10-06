# ==========================================
# 🐱 MeowBot - Meow System (Async + Anti-Repetition)
# ==========================================

import random
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from config import MEOW_COOLDOWN
from database.users import (
    create_user, get_user, update_user, increment_daily_meow,
    add_meow_points, set_last_meow, get_last_meow, get_meow_points,
)
from database.content import pick_unseen_index

TEHRAN = ZoneInfo("Asia/Tehran")

MEOW_WORDS = {
    "میو", "معو", "ماو", "میومیو", "میو میو", "میو‌میو",
    "میــــو", "میــــــو", "میاو", "میاوو", "mew", "meow",
}

# متن‌های متنوع — {name} {gained} {total}
MEOW_RESPONSES = [
    "🐱 میو~ {name}!\n✨ +{gained} امتیاز\n🐾 میو فعلی: {total}",
    "🎀 آفرین {name}!\n✨ +{gained} امتیاز میو\n🐾 مجموع امتیاز فصل: {total}",
    "🌸 پیشی‌ها صداتو شنیدن {name}!\n✨ +{gained}\n🐾 امتیاز الان: {total}",
    "✨ میو میو~\n👤 {name}\n🎁 گرفتی: +{gained}\n📊 موجودی میو: {total}",
    "🩷 چه میو قشنگی {name}!\n✨ +{gained} امتیاز\n🐾 میو فعلی‌ات: {total}",
    "🐱 بوی میو میاد از سمت {name} 😼\n✨ +{gained}\n🐾 کل امتیاز: {total}",
    "🐾 {name} میو کرد!\n🎁 +{gained} امتیاز\n📊 میو فعلی: {total}",
    "😻 عالی بود {name}!\n✨ +{gained}\n🐾 امتیاز فصل تو: {total}",
    "🌟 میوی طلایی از {name}!\n✨ +{gained} امتیاز\n🐾 مجموع: {total}",
    "😹 {name} باز میو کرد!\n✨ +{gained}\n🐾 میو فعلی: {total}",
    "🐱 Meow!\n👤 {name}\n🎁 +{gained}\n📊 Total: {total}",
    "🎀 امروز هم میو کردی {name}!\n✨ +{gained} امتیاز\n🐾 موجودی: {total}",
    "✨ پوینت ثبت شد 🐾\n👤 {name}\n🎁 +{gained}\n📊 میو فعلی: {total}",
    "🩷 میو میو میو~ {name}!\n✨ +{gained}\n🐾 امتیاز الان: {total}",
    "😼 گربه‌ها به احترامت میو کردن {name}!\n✨ +{gained} امتیاز\n🐾 میو فعلی‌ات: {total}",
]


def normalize_text(text):
    if not text:
        return ""
    text = str(text).replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def is_meow(text) -> bool:
    normalized = normalize_text(text)
    if normalized in MEOW_WORDS:
        return True
    if re.fullmatch(r"می[ـ\-]*و+", normalized):
        return True
    if normalized in ("mew", "meow"):
        return True
    return False


def is_allowed_group(chat_id, chat_username):
    return chat_id is not None


def format_cooldown(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    if m > 0:
        return f"{m} دقیقه و {s} ثانیه"
    return f"{s} ثانیه"


async def register_meow(user_id: int, first_name: str = "", username: str = "", chat_id=None):
    now = time.time()
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, first_name=first_name, username=username, chat_id=chat_id)
        user = await get_user(user_id)

    last = float(user.get("last_meow") or 0)
    remaining = MEOW_COOLDOWN - (now - last)
    if remaining > 0:
        # در کول‌داون هم امتیاز فعلی را نشان بده
        current = int(user.get("meow_points") or 0)
        msgs = [
            f"🐱 هنوز زوده! {format_cooldown(remaining)} دیگه صبر کن 😴\n🐾 میو فعلی‌ات: {current}",
            f"😼 آروم باش، {format_cooldown(remaining)} تا میوی بعدی مونده!\n🐾 امتیاز فصل: {current}",
            f"💤 پیشی هنوز داره نفس می‌کشه... {format_cooldown(remaining)}\n🐾 میو فعلی: {current}",
            f"⏳ Cooldown: {format_cooldown(remaining)}\n🐾 میو فعلی‌ات: {current}",
        ]
        return False, random.choice(msgs), 0

    points = 1
    event_note = ""
    try:
        from database.events import apply_xp_bonus
        points, _mult, event_note = await apply_xp_bonus(points)
    except Exception:
        pass
    await add_meow_points(user_id, points, chat_id)
    await set_last_meow(user_id, now, chat_id)

    # امتیاز فعلی بعد از اضافه شدن
    total = await get_meow_points(user_id)
    if total is None:
        total = int(user.get("meow_points") or 0) + points

    day = datetime.now(TEHRAN).strftime("%Y-%m-%d")
    try:
        await increment_daily_meow(user_id, points, day)
    except Exception:
        pass

    idx = await pick_unseen_index(user_id, "meow_response", len(MEOW_RESPONSES))
    name = first_name or (user.get("first_name") if user else None) or "پیشی"
    msg = MEOW_RESPONSES[idx].format(name=name, gained=points, total=total)
    if event_note:
        msg += f"\n{event_note}"

    try:
        from database.missions import update_mission_progress
        from database.achievements import update_achievement_progress
        u = await get_user(user_id)
        total_meows = int(u.get("total_meows") or 0) if u else 0
        await update_mission_progress(user_id, "meows", 1)
        await update_achievement_progress(user_id, "meows", total_meows)
    except Exception:
        pass

    return True, msg, points
