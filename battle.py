# ==========================================
# 🐱 MeowBot - Battle System (Global Account)
# ==========================================

import random
import time

from config import (
    BATTLE_COOLDOWN,
)

from database import (
    create_user,
    get_user,
    get_gym_level,
    add_meow_coins,
    get_last_battle,
    set_last_battle,
)


# ==========================================
# Rewards
# ==========================================

WIN_REWARD = 20
LOSE_REWARD = 5


# ==========================================
# Cooldown Messages (قابل گسترش)
# ==========================================

BATTLE_COOLDOWN_MESSAGES = [
    "🐱 هنوز خیلی خسته‌ای! یه کم استراحت کن 😴",
    "😼 گربه‌ات هنوز داره نفس می‌گیره... یه کم صبر کن!",
    "💤 هنوز ۹ تا جون دیگه لازم داری! بعداً برگرد 😂",
    "🐾 پنجه‌هات هنوز آماده نیستن! کمی صبر کن.",
    "😹 آروم باش فرمانده! جنگ قبلی هنوز یادت نرفته 😹",
    "⚡ انرژی جنگی در حال شارژه...",
    "🔥 هنوز وقت نبرد بعدی نرسیده!",
    "😴 MeowBot میگه: استراحت کن جنگجو!",
]


# ==========================================
# Battle Calculation
# ==========================================

def calculate_battle(
    attacker_level,
    defender_level
):

    attacker_level = int(attacker_level)
    defender_level = int(defender_level)

    # --------------------------------------
    # Equal Level
    # --------------------------------------

    if attacker_level == defender_level:

        attacker_chance = 0.50

    # --------------------------------------
    # Attacker Stronger
    # --------------------------------------

    elif attacker_level > defender_level:

        attacker_chance = 0.80

    # --------------------------------------
    # Defender Stronger
    # --------------------------------------

    else:

        attacker_chance = 0.20

    roll = random.random()

    attacker_wins = (
        roll < attacker_chance
    )

    return {
        "attacker_wins": attacker_wins,
        "attacker_chance": attacker_chance,
        "roll": roll,
    }


# ==========================================
# Cooldown Helpers
# ==========================================

def get_battle_remaining_cooldown(user_id, chat_id=None):
    """
    زمان باقی‌مانده Cooldown جنگ برای کاربر (ثانیه).
    اگر Cooldown تمام شده باشد ۰ برمی‌گرداند.
    """
    last_battle = get_last_battle(user_id, chat_id)

    if not last_battle:
        return 0

    remaining = BATTLE_COOLDOWN - (
        time.time() - float(last_battle)
    )

    if remaining <= 0:
        return 0

    return int(remaining)


def format_battle_cooldown(seconds):
    """
    فرمت خوانا برای زمان باقی‌مانده.
    مثال: 7 دقیقه و 24 ثانیه
    """
    seconds = max(0, int(seconds))

    minutes = seconds // 60
    secs = seconds % 60

    if minutes > 0:
        return f"{minutes} دقیقه و {secs} ثانیه"

    return f"{secs} ثانیه"


def get_random_cooldown_message():
    return random.choice(BATTLE_COOLDOWN_MESSAGES)


# ==========================================
# Start Battle
# ==========================================

def start_battle(
    attacker_id,
    defender_id,
    chat_id=None,
):

    attacker_id = int(attacker_id)
    defender_id = int(defender_id)

    # --------------------------------------
    # Self Battle
    # --------------------------------------

    if attacker_id == defender_id:

        return {
            "success": False,
            "reason": "self_battle",
        }

    # --------------------------------------
    # Cooldown Check (قبل از هر عملیات)
    # --------------------------------------

    remaining = get_battle_remaining_cooldown(
        user_id=attacker_id,
        chat_id=chat_id,
    )

    if remaining > 0:

        return {
            "success": False,
            "reason": "cooldown",
            "remaining": remaining,
            "message": get_random_cooldown_message(),
        }

    # --------------------------------------
    # Create Users (global)
    # --------------------------------------

    attacker = get_user(attacker_id, chat_id)

    if not attacker:

        create_user(
            user_id=attacker_id,
            chat_id=chat_id,
            first_name="Unknown",
            username=""
        )

        attacker = get_user(attacker_id, chat_id)

    defender = get_user(defender_id, chat_id)

    if not defender:

        create_user(
            user_id=defender_id,
            chat_id=chat_id,
            first_name="Unknown",
            username=""
        )

        defender = get_user(defender_id, chat_id)

    # --------------------------------------
    # Names
    # --------------------------------------

    attacker_name = (
        attacker["first_name"]
        or "Unknown"
    )

    defender_name = (
        defender["first_name"]
        or "Unknown"
    )

    # --------------------------------------
    # Gym Levels (Global)
    # --------------------------------------

    attacker_level = get_gym_level(attacker_id, chat_id)
    defender_level = get_gym_level(defender_id, chat_id)

    # --------------------------------------
    # Calculate
    # --------------------------------------

    battle = calculate_battle(
        attacker_level=attacker_level,
        defender_level=defender_level
    )

    # --------------------------------------
    # Winner / Loser
    # --------------------------------------

    if battle["attacker_wins"]:

        winner_id = attacker_id
        loser_id = defender_id

        winner_name = attacker_name
        loser_name = defender_name

    else:

        winner_id = defender_id
        loser_id = attacker_id

        winner_name = defender_name
        loser_name = attacker_name

    # --------------------------------------
    # Rewards (Global coins)
    # --------------------------------------

    add_meow_coins(
        user_id=winner_id,
        chat_id=chat_id,
        amount=WIN_REWARD
    )

    add_meow_coins(
        user_id=loser_id,
        chat_id=chat_id,
        amount=LOSE_REWARD
    )

    # --------------------------------------
    # ثبت زمان آخرین جنگ موفق (فقط بعد از موفقیت)
    # --------------------------------------

    set_last_battle(
        user_id=attacker_id,
        chat_id=chat_id,
        timestamp=time.time(),
    )

    # --------------------------------------
    # Result
    # --------------------------------------

    return {
        "success": True,
        "reason": "battle_finished",

        "attacker_id": attacker_id,
        "defender_id": defender_id,

        "attacker_name": attacker_name,
        "defender_name": defender_name,

        "attacker_level": attacker_level,
        "defender_level": defender_level,

        "winner_id": winner_id,
        "loser_id": loser_id,

        "winner_name": winner_name,
        "loser_name": loser_name,

        "winner_reward": WIN_REWARD,
        "loser_reward": LOSE_REWARD,

        "attacker_chance": battle[
            "attacker_chance"
        ],

        "roll": battle["roll"],
    }
