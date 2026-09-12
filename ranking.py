# ==========================================
# 🐱 MeowBot - Ranking System
# ==========================================

from config import RANKING_LIMIT

from database import (
    get_top_users,
    get_user,
)


# ==========================================
# Get Ranking
# ==========================================

def get_ranking(
    chat_id,
    limit=RANKING_LIMIT
):
    """
    دریافت رتبه‌بندی کاربران همین گروه.

    ترتیب:
    1. Meow Point بیشتر
    2. Gym Level بالاتر
    """

    users = get_top_users(
        chat_id=chat_id,
        limit=limit
    )

    ranking = []

    for index, user in enumerate(users, start=1):

        ranking.append({
            "rank": index,
            "user_id": int(user["user_id"]),
            "first_name": user["first_name"] or "Unknown",
            "username": user["username"] or "",
            "meow_points": int(user["meow_points"]),
            "meow_coins": int(user["meow_coins"]),
            "gym_level": int(user["gym_level"]),
        })

    return ranking


# ==========================================
# Find User Rank
# ==========================================

def get_user_rank(
    user_id,
    chat_id
):
    """
    رتبه فعلی یک کاربر را در همین گروه پیدا می‌کند.
    """

    users = get_top_users(
        chat_id=chat_id,
        limit=999999
    )

    for index, user in enumerate(users, start=1):

        if int(user["user_id"]) == int(user_id):

            return {
                "rank": index,
                "user_id": int(user["user_id"]),
                "first_name": user["first_name"] or "Unknown",
                "meow_points": int(user["meow_points"]),
                "gym_level": int(user["gym_level"]),
            }

    return None


# ==========================================
# Format Ranking
# ==========================================

def format_ranking(
    chat_id,
    limit=RANKING_LIMIT
):
    """
    ساخت متن آماده برای ارسال در گروه.
    """

    ranking = get_ranking(
        chat_id=chat_id,
        limit=limit
    )

    if not ranking:

        return (
            "🏆🎀 رنکینگ میویی\n\n"
            "هنوز کسی وارد رقابت نشده! 🐱\n"
            "اولین میو رو بزن تا رتبه‌بندی شروع بشه ✨"
        )

    lines = [
        "🏆🎀 رنکینگ میویی",
        "",
        "🐱 برترین میوکارهای این گروه:",
        ""
    ]

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    for item in ranking:

        rank = item["rank"]
        name = item["first_name"]
        points = item["meow_points"]
        level = item["gym_level"]

        medal = medals.get(
            rank,
            f"{rank}."
        )

        lines.append(
            f"{medal} {name}"
        )

        lines.append(
            f"   🐾 {points} Meow Point"
            f"  |  🏋️ Lv.{level}"
        )

    lines.extend([
        "",
        "🎀 ادامه بده، شاید نفر اول بعدی تو باشی! 🐱✨"
    ])

    return "\n".join(lines)