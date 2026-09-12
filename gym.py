# ==========================================
# 🐱 MeowBot - Meow Gym (Global Account)
# ==========================================

from config import MAX_GYM_LEVEL, DATABASE_NAME

from database import (
    create_user,
    get_user,
    get_meow_points,
    get_gym_level,
    ensure_group_membership,
)


# ==========================================
# Gym Cost
# ==========================================

def get_upgrade_cost(level):
    level = int(level)

    if level >= MAX_GYM_LEVEL:
        return 0

    return level * 5


# ==========================================
# Gym Power
# ==========================================

def get_power(level):
    level = max(
        1,
        min(int(level), MAX_GYM_LEVEL)
    )

    return level


# ==========================================
# Get Gym Status
# ==========================================

def get_gym_status(
    user_id,
    chat_id=None,
    first_name="",
    username=""
):
    user = get_user(user_id, chat_id)

    if not user:
        create_user(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )
        user = get_user(user_id, chat_id)

    level = get_gym_level(user_id, chat_id)
    points = get_meow_points(user_id, chat_id)

    cost = get_upgrade_cost(level)
    power = get_power(level)

    return {
        "level": level,
        "power": power,
        "points": points,
        "upgrade_cost": cost,
        "max_level": level >= MAX_GYM_LEVEL,
    }


# ==========================================
# Upgrade Gym (Global)
# ==========================================

def upgrade_gym(
    user_id,
    chat_id=None,
    first_name="",
    username=""
):
    """
    ارتقای باشگاه میویی (Global Account)

    - موجودی را داخل همان تراکنش بررسی می‌کند.
    - Point را فقط در صورت کافی بودن کم می‌کند.
    - Level را فقط در صورت موفق بودن افزایش می‌دهد.
    """

    user_id = int(user_id)

    # Make sure user exists
    user = get_user(user_id, chat_id)

    if not user:
        create_user(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )

    import sqlite3

    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT meow_points, gym_level
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if not row:
            connection.rollback()
            return {
                "success": False,
                "reason": "user_not_found",
                "level": 1,
                "new_level": 1,
                "cost": 0,
                "points": 0,
                "power": 1,
            }

        points = int(row[0])
        current_level = int(row[1])

        if current_level >= MAX_GYM_LEVEL:
            connection.rollback()
            return {
                "success": False,
                "reason": "max_level",
                "level": current_level,
                "new_level": current_level,
                "cost": 0,
                "points": points,
                "power": get_power(current_level),
            }

        cost = get_upgrade_cost(current_level)

        if points < cost:
            connection.rollback()
            return {
                "success": False,
                "reason": "not_enough_points",
                "level": current_level,
                "new_level": current_level,
                "cost": cost,
                "points": points,
                "power": get_power(current_level),
            }

        cursor.execute(
            """
            UPDATE users
            SET
                meow_points = meow_points - ?,
                gym_level = gym_level + 1
            WHERE user_id = ?
              AND gym_level = ?
              AND meow_points >= ?
            """,
            (cost, user_id, current_level, cost)
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return {
                "success": False,
                "reason": "upgrade_failed",
                "level": current_level,
                "new_level": current_level,
                "cost": cost,
                "points": points,
                "power": get_power(current_level),
            }

        connection.commit()

        new_level = current_level + 1
        new_points = points - cost

        if chat_id is not None:
            ensure_group_membership(user_id, chat_id)

        return {
            "success": True,
            "reason": "upgraded",
            "level": current_level,
            "new_level": new_level,
            "cost": cost,
            "points": new_points,
            "power": get_power(new_level),
        }

    except Exception:
        connection.rollback()
        return {
            "success": False,
            "reason": "database_error",
            "level": 1,
            "new_level": 1,
            "cost": 0,
            "points": 0,
            "power": 1,
        }

    finally:
        connection.close()
