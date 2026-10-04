from .pool import fetch, execute, fetchrow
from datetime import datetime
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")


def period_key_daily():
    return datetime.now(TEHRAN).strftime("%Y-%m-%d")


def period_key_weekly():
    now = datetime.now(TEHRAN)
    return f"{now.year}-W{now.isocalendar()[1]}"


async def seed_missions():
    defaults = [
        ("daily_meow_5", "۵ میو روزانه", "امروز ۵ بار میو کن", "daily", "meows", 5, 30, 10, None),
        ("daily_battle", "یک نبرد", "امروز یک Battle انجام بده", "daily", "battles", 1, 25, 15, None),
        ("daily_pet", "مراقبت از Pet", "با Petت تعامل کن", "daily", "pet_interact", 1, 20, 10, None),
        ("weekly_meow_30", "۳۰ میو هفتگی", "این هفته ۳۰ میو بزن", "weekly", "meows", 30, 150, 50, None),
        ("weekly_wins_5", "۵ برد هفتگی", "این هفته ۵ نبرد ببر", "weekly", "wins", 5, 100, 40, None),
    ]
    for m in defaults:
        await execute(
            """
            INSERT INTO missions
                (mission_id, name, description, mission_type, condition_type, condition_value,
                 reward_coins, reward_xp, reward_item)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (mission_id) DO NOTHING
            """,
            *m,
        )


async def get_user_missions(user_id: int, mission_type: str = "daily"):
    pk = period_key_daily() if mission_type == "daily" else period_key_weekly()
    rows = await fetch(
        """
        SELECT m.*, COALESCE(um.progress, 0) AS progress,
               COALESCE(um.completed, FALSE) AS completed,
               COALESCE(um.claimed, FALSE) AS claimed
        FROM missions m
        LEFT JOIN user_missions um
            ON um.mission_id = m.mission_id AND um.user_id = $1 AND um.period_key = $2
        WHERE m.mission_type = $3 AND m.active = TRUE
        """,
        int(user_id), pk, mission_type,
    )
    return [dict(r) for r in rows]


async def update_mission_progress(user_id: int, condition_type: str, delta: int = 1):
    for mtype, pk_fn in [("daily", period_key_daily), ("weekly", period_key_weekly)]:
        pk = pk_fn()
        rows = await fetch(
            "SELECT * FROM missions WHERE condition_type = $1 AND mission_type = $2 AND active = TRUE",
            condition_type, mtype,
        )
        for m in rows:
            mid = m["mission_id"]
            needed = int(m["condition_value"])
            row = await fetchrow(
                "SELECT * FROM user_missions WHERE user_id=$1 AND mission_id=$2 AND period_key=$3",
                int(user_id), mid, pk,
            )
            progress = (int(row["progress"]) if row else 0) + delta
            done = progress >= needed
            await execute(
                """
                INSERT INTO user_missions (user_id, mission_id, progress, completed, period_key)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, mission_id, period_key) DO UPDATE SET
                    progress = user_missions.progress + $3,
                    completed = user_missions.completed OR $4
                """,
                int(user_id), mid, delta, done, pk,
            )
