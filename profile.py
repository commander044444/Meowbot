# ==========================================
# 🐱 MeowBot - Profile System
# ==========================================

from database import (
    create_user,
    get_user,
    get_meow_points,
    get_meow_coins,
    get_gym_level,
    get_bank,
)

from gym import (
    get_power,
)

from ranking import (
    get_user_rank,
)


# ==========================================
# Get Profile
# ==========================================

def get_profile(
    user_id,
    chat_id,
    first_name="",
    username=""
):
    """
    دریافت تمام اطلاعات پروفایل کاربر.
    """

    user_id = int(user_id)
    chat_id = str(chat_id)

    user = get_user(
        user_id,
        chat_id
    )

    # --------------------------------------
    # Create User If Needed
    # --------------------------------------

    if not user:

        create_user(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )

        user = get_user(
            user_id,
            chat_id
        )

    # --------------------------------------
    # User Info
    # --------------------------------------

    saved_first_name = (
        user["first_name"]
        or first_name
        or "Unknown"
    )

    saved_username = (
        user["username"]
        or username
        or ""
    )

    # --------------------------------------
    # Game Stats
    # --------------------------------------

    meow_points = get_meow_points(
        user_id,
        chat_id
    )

    meow_coins = get_meow_coins(
        user_id,
        chat_id
    )

    gym_level = get_gym_level(
        user_id,
        chat_id
    )

    power = get_power(
        gym_level
    )

    # --------------------------------------
    # Rank
    # --------------------------------------

    rank_data = get_user_rank(
        user_id=user_id,
        chat_id=chat_id
    )

    if rank_data:

        rank = rank_data["rank"]

    else:

        rank = None

    bank = get_bank(user_id)
    if bank:
        bank_balance = int(bank["balance"] or 0)
        bank_card = bank["card_number"] or ""
    else:
        bank_balance = 0
        bank_card = None

    # --------------------------------------
    # Profile Data
    # --------------------------------------

    return {
        "user_id": user_id,
        "first_name": saved_first_name,
        "username": saved_username,

        "meow_points": meow_points,
        "meow_coins": meow_coins,

        "gym_level": gym_level,
        "power": power,

        "rank": rank,

        "bank_balance": bank_balance,
        "bank_card": bank_card,
    }


# ==========================================
# Format Profile
# ==========================================

def format_profile(
    user_id,
    chat_id,
    first_name="",
    username=""
):
    """
    ساخت متن آماده برای ارسال پروفایل.
    """

    profile = get_profile(
        user_id=user_id,
        chat_id=chat_id,
        first_name=first_name,
        username=username
    )

    name = profile["first_name"]

    username = profile["username"]

    if username:

        username_text = (
            f"🔗 @{username.lstrip('@')}"
        )

    else:

        username_text = (
            "🔗 بدون Username"
        )

    rank = profile["rank"]

    if rank:

        rank_text = f"🏆 رتبه: #{rank}"

    else:

        rank_text = (
            "🏆 رتبه: هنوز وارد رنکینگ نشده"
        )

    bank_card = profile.get("bank_card")
    bank_balance = profile.get("bank_balance", 0)
    if bank_card:
        bank_text = (
            f"🏦 موجودی بانک: {bank_balance} Meow Coin\n"
            f"💳 شماره کارت: {bank_card}"
        )
    else:
        bank_text = "🏦 بانک: هنوز ساخته نشده"

    return (
        "🐱🎀 پروفایل میویی\n"
        "\n"
        "━━━━━━━━━━━━━━\n"
        "\n"
        f"👤 نام: {name}\n"
        f"{username_text}\n"
        f"🆔 ID: {profile['user_id']}\n"
        "\n"
        "━━━━━━━━━━━━━━\n"
        "\n"
        "📊 آمار بازی\n"
        "\n"
        f"🐾 Meow Point: {profile['meow_points']}\n"
        f"🪙 Meow Coin: {profile['meow_coins']}\n"
        f"{bank_text}\n"
        f"🏋️ Gym Level: {profile['gym_level']} / 100\n"
        f"⚡ قدرت: {profile['power']}\n"
        f"{rank_text}\n"
        "\n"
        "━━━━━━━━━━━━━━\n"
        "\n"
        "✨ ادامه بده، قوی‌تر شو و میو کن! 🐱🩷"
    )