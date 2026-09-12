# ==========================================
# 🐱 MeowBot - Meow System
# ==========================================

import random
import re
import time

from config import (
    ALLOWED_GROUP,
    MEOW_COOLDOWN,
)

from database import (
    create_user,
    get_user,
    update_user,
)


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

    # حذف ZWNJ و ZWJ
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    # یکسان‌سازی فاصله‌ها
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# ==========================================
# 🐱 Check Meow
# ==========================================

def is_meow(text):
    normalized = normalize_text(text)

    if normalized in MEOW_WORDS:
        return True

    # میوهای کشیده مثل:
    # میــــــو
    # میــــــــــــــو
    if re.fullmatch(r"می[ـ\-]*و", normalized):
        return True

    # حالت‌های انگلیسی
    if normalized in ("mew", "meow"):
        return True

    return False


# ==========================================
# 🔐 Allowed Group
# ==========================================

def is_allowed_group(chat_id, chat_username):
    """
    بررسی می‌کند که پیام از یکی از گروه‌های مجاز آمده باشد.

    ALLOWED_GROUP می‌تواند:
        "@group1"

    یا:
        [
            "@group1",
            "@group2",
        ]
    باشد.
    """

    # --------------------------------------
    # تبدیل تنظیمات به لیست
    # --------------------------------------

    if isinstance(ALLOWED_GROUP, (list, tuple, set)):
        allowed_groups = ALLOWED_GROUP
    else:
        allowed_groups = [ALLOWED_GROUP]

    # --------------------------------------
    # نرمال‌سازی username
    # --------------------------------------

    username = str(chat_username or "").strip().lower()

    if username and not username.startswith("@"):
        username = "@" + username

    # --------------------------------------
    # بررسی username
    # --------------------------------------

    for group in allowed_groups:
        if not group:
            continue

        group = str(group).strip().lower()

        if group and not group.startswith("@"):
            group = "@" + group

        if username == group:
            return True

    return False


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

    # --------------------------------------
    # بررسی Cooldown
    # --------------------------------------

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

    # --------------------------------------
    # دریافت Meow Point
    # --------------------------------------

    points = random.randint(1, 30)

    current_points = int(user["meow_points"] or 0)

    current_coins = int(user["meow_coins"] or 0)

    gym_level = int(user["gym_level"] or 1)

    # --------------------------------------
    # ذخیره
    # --------------------------------------

    update_user(
        user_id=user_id,
        chat_id=chat_id,
        first_name=first_name or user["first_name"],
        username=username or user["username"],
        meow_points=current_points + points,
        meow_coins=current_coins,
        gym_level=gym_level,
        last_meow=time.time(),
    )

    return {
        "success": True,
        "reason": "meow",
        "points": points,
        "total_points": current_points + points,
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
        return f"{minutes} دقیقه و {seconds} ثانیه"

    return f"{seconds} ثانیه"
