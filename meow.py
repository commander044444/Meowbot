# ==========================================
# 🐱 MeowBot - Meow System
# ==========================================

import random
import re
import time

from config import (
    MEOW_COOLDOWN,
)

from database import (
    create_user,
    get_user,
    update_user,
    increment_daily_meow,
)
from datetime import datetime
from zoneinfo import ZoneInfo


# ==========================================
# 🐾 Meow Words
# ==========================================

MEOW_WORDS = {
    "میو",
    "معو",
    "ماو",
    "میومیو",
    "میو میو",
    "میو‌میو",
    "میــــو",
    "میــــــو",
    "میاو",
    "میاوو",
    "mew",
    "meow",
}


# ==========================================
# 🧹 Text Normalizer
# ==========================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text)

    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# ==========================================
# 🐱 Check Meow
# ==========================================

def is_meow(text):

    normalized = normalize_text(text)

    if normalized in MEOW_WORDS:
        return True

    # میوهای کشیده
    if re.fullmatch(r"می[ـ\-]*و", normalized):
        return True

    # English
    if normalized in ("mew", "meow"):
        return True

    return False


# ==========================================
# 🌍 Allowed Group
# ==========================================

def is_allowed_group(chat_id, chat_username):
    """
    MeowBot در تمام گروه‌ها فعال است.

    دیگر ALLOWED_GROUP بررسی نمی‌شود.

    هر گروهی که ربات در آن پیام دریافت کند
    می‌تواند از سیستم MeowBot استفاده کند.
    """

    if chat_id is None:
        return False

    return True


# ==========================================
# ⏱ Cooldown
# ==========================================

def get_remaining_cooldown(user_id, chat_id):

    user = get_user(
        user_id=user_id,
        chat_id=chat_id,
    )

    if not user:
        return 0

    last_meow = user["last_meow"]

    if not last_meow:
        return 0

    remaining = MEOW_COOLDOWN - (
        time.time() - float(last_meow)
    )

    if remaining <= 0:
        return 0

    return int(remaining)


# ==========================================
# 🐾 Register Meow
# ==========================================

def register_meow(
    user_id,
    chat_id,
    first_name="",
    username="",
):

    user_id = int(user_id)
    chat_id = str(chat_id)

    user = get_user(
        user_id=user_id,
        chat_id=chat_id,
    )

    # اگر کاربر وجود نداشت
    if not user:

        create_user(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username,
        )

        user = get_user(
            user_id=user_id,
            chat_id=chat_id,
        )

    # ======================================
    # Cooldown
    # ======================================

    remaining = get_remaining_cooldown(
        user_id=user_id,
        chat_id=chat_id,
    )

    if remaining > 0:

        return {
            "success": False,
            "reason": "cooldown",
            "remaining": remaining,
            "points": 0,
        }


    # ======================================
    # Meow Points
    # ======================================

    points = random.randint(1, 30)

    current_points = int(
        user["meow_points"] or 0
    )

    current_coins = int(
        user["meow_coins"] or 0
    )

    gym_level = int(
        user["gym_level"] or 1
    )


    # ======================================
    # Save
    # ======================================

    update_user(
        user_id=user_id,
        chat_id=chat_id,
        first_name=(
            first_name
            or user["first_name"]
        ),
        username=(
            username
            or user["username"]
        ),
        meow_points=current_points + points,
        meow_coins=current_coins,
        gym_level=gym_level,
        last_meow=time.time(),
    )

    # Track daily meow for season rankings (Tehran date)
    try:
        tehran_date = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d")
        increment_daily_meow(user_id, points, tehran_date)
    except Exception:
        pass

    # ======================================
    # Result
    # ======================================

    return {
        "success": True,
        "reason": "meow",
        "earned": points,
        "points": points,
        "total_points": (
            current_points + points
        ),
        "remaining": 0,
    }


# ==========================================
# ⏱ Cooldown Formatter
# ==========================================

def format_cooldown(seconds):

    seconds = max(0, int(seconds))

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes > 0:

        return (
            f"{minutes} دقیقه و "
            f"{seconds} ثانیه"
        )

    return f"{seconds} ثانیه"
