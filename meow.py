# ==========================================
# 🐱 MeowBot - Meow System
# ==========================================

import time
import random
import re

from config import MEOW_COOLDOWN, ALLOWED_GROUP

from database import (
    create_user,
    get_user,
    add_meow_points,
    set_last_meow,
    get_last_meow,
)


# ==========================================
# Meow Words
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
# Normalize Text
# ==========================================

def normalize_text(text):
    """
    متن را برای تشخیص بهتر میو یکدست می‌کند.
    """

    if not text:
        return ""

    text = text.strip().lower()

    # حذف فاصله‌های اضافی
    text = re.sub(r"\s+", " ", text)

    return text


# ==========================================
# Is Meow?
# ==========================================

def is_meow(text):
    """
    بررسی می‌کند که آیا پیام یک میوی معتبر است یا نه.
    """

    normalized = normalize_text(text)

    if not normalized:
        return False

    return normalized in MEOW_WORDS


# ==========================================
# Group Check
# ==========================================

def is_allowed_group(chat_id, chat_username=None):
    """
    بررسی می‌کند که بازی فقط در گروه مجاز اجرا شود.
    """

    if chat_username:
        username = str(chat_username).strip().lower()

        if not username.startswith("@"):
            username = "@" + username

        if username == ALLOWED_GROUP.lower():
            return True

    return str(chat_id) == str(ALLOWED_GROUP)


# ==========================================
# Cooldown
# ==========================================

def get_remaining_cooldown(user_id, chat_id):
    """
    مقدار زمان باقی‌مانده تا میوی بعدی را برمی‌گرداند.

    خروجی:
        0  = آماده میو کردن
        >0 = تعداد ثانیه باقی‌مانده
    """

    last_meow = get_last_meow(
        user_id,
        chat_id
    )

    if not last_meow:
        return 0

    elapsed = time.time() - last_meow

    remaining = MEOW_COOLDOWN - elapsed

    if remaining <= 0:
        return 0

    return int(remaining)


# ==========================================
# Register Meow
# ==========================================

def register_meow(
    user_id,
    chat_id,
    first_name="",
    username=""
):
    """
    ثبت یک میو.

    هر میو بین 1 تا 30 Meow Point
    به صورت تصادفی به کاربر می‌دهد.
    """

    # --------------------------------------
    # User
    # --------------------------------------

    user = get_user(
        user_id,
        chat_id
    )

    if not user:
        create_user(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )

    # --------------------------------------
    # Cooldown
    # --------------------------------------

    remaining = get_remaining_cooldown(
        user_id,
        chat_id
    )

    if remaining > 0:
        return {
            "success": False,
            "remaining": remaining,
            "points": 0,
            "earned": 0
        }

    # --------------------------------------
    # Random Meow Points
    # --------------------------------------

    earned_points = random.randint(1, 30)

    # --------------------------------------
    # Add Points
    # --------------------------------------

    add_meow_points(
        user_id,
        chat_id,
        amount=earned_points
    )

    # --------------------------------------
    # Update Last Meow
    # --------------------------------------

    now = time.time()

    set_last_meow(
        user_id,
        chat_id,
        now
    )

    # --------------------------------------
    # Current Points
    # --------------------------------------

    user = get_user(
        user_id,
        chat_id
    )

    points = int(
        user["meow_points"]
    )

    # --------------------------------------
    # Result
    # --------------------------------------

    return {
        "success": True,
        "remaining": 0,
        "points": points,
        "earned": earned_points
    }


# ==========================================
# Cooldown Formatter
# ==========================================

def format_cooldown(seconds):
    """
    تبدیل ثانیه به متن خوانا.
    """

    seconds = max(
        0,
        int(seconds)
    )

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes > 0:
        return f"{minutes} دقیقه و {seconds} ثانیه"

    return f"{seconds} ثانیه"