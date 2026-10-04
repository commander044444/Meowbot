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
    add_meow_points, set_last_meow, get_last_meow,
)
from database.content import pick_unseen_index

TEHRAN = ZoneInfo("Asia/Tehran")

MEOW_WORDS = {
    "میو", "معو", "ماو", "میومیو", "میو میو", "میو‌میو",
    "میــــو", "میــــــو", "میاو", "میاوو", "mew", "meow",
}

MEOW_RESPONSES = [
    "🐱 میو~ {name} یه امتیاز گرفت!",
    "🎀 میووو! آفرین {name} ✨",
    "🌸 پیشی‌ها صداتو شنیدن {name}!",
    "✨ میو میو~ +۱ پوینت برای {name}",
    "🩷 چه میو قشنگی {name}!",
    "🐱 هوم... بوی میو میاد از سمت {name} 😼",
    "🐾 {name} داره میو می‌کنه و پوینت جمع می‌کنه!",
    "😻 میووو~ عالی بود {name}!",
    "🌟 یه میوی طلایی از {name}!",
    "😹 {name} باز میو کرد، پیشی‌ها خوشحال شدن!",
    "🐱 Meow! {name} +1",
    "🎀 امروز هم میو کردی {name}، ادامه بده!",
    "✨ پوینت میو برای {name} ثبت شد 🐾",
    "🩷 میو میو میو~ {name} ستاره شد!",
    "😼 گربه‌ها به احترام {name} میو کردن!",
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
        msgs = [
            f"🐱 هنوز زوده! {format_cooldown(remaining)} دیگه صبر کن 😴",
            f"😼 آروم باش، {format_cooldown(remaining)} تا میوی بعدی مونده!",
            f"💤 پیشی هنوز داره نفس می‌کشه... {format_cooldown(remaining)}",
            f"⏳ Cooldown: {format_cooldown(remaining)}",
        ]
        return False, random.choice(msgs), 0

    points = 1
    await add_meow_points(user_id, points, chat_id)
    await set_last_meow(user_id, now, chat_id)

    day = datetime.now(TEHRAN).strftime("%Y-%m-%d")
    try:
        await increment_daily_meow(user_id, points, day)
    except Exception:
        pass

    idx = await pick_unseen_index(user_id, "meow_response", len(MEOW_RESPONSES))
    name = first_name or user.get("first_name") or "پیشی"
    msg = MEOW_RESPONSES[idx].format(name=name)

    try:
        from database.missions import update_mission_progress
        from database.achievements import update_achievement_progress
        u = await get_user(user_id)
        total = int(u.get("total_meows") or 0)
        await update_mission_progress(user_id, "meows", 1)
        await update_achievement_progress(user_id, "meows", total)
    except Exception:
        pass

    return True, msg, points
