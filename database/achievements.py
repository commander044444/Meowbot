from .pool import fetch, fetchrow, execute
import json


async def seed_achievements():
    defaults = [
        ("first_meow", "اولین میو", "اولین میو رو زدی!", "meow", "🐱", 10, 5, "meows", 1),
        ("meow_10", "میوکار", "۱۰ تا میو زدی", "meow", "🐾", 20, 10, "meows", 10),
        ("meow_100", "میو استاد", "۱۰۰ تا میو زدی", "meow", "👑", 100, 50, "meows", 100),
        ("first_battle", "اولین نبرد", "اولین جنگ رو کردی", "battle", "⚔️", 15, 10, "battles", 1),
        ("win_10", "جنگجو", "۱۰ تا برد", "battle", "🏆", 50, 30, "wins", 10),
        ("coin_1000", "ثروتمند", "۱۰۰۰ کوین جمع کردی", "economy", "💰", 0, 20, "coins", 1000),
        ("pet_level_5", "دوست پیشی", "Pet لول ۵", "pet", "🎀", 30, 15, "pet_level", 5),
        ("pet_level_20", "سرپرست پیشی", "Pet لول ۲۰", "pet", "🌟", 100, 50, "pet_level", 20),
    ]
    for a in defaults:
        await execute(
            """
            INSERT INTO achievements
                (achievement_id, name, description, category, icon, reward_coins, reward_xp, condition_type, condition_value)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (achievement_id) DO NOTHING
            """,
            *a,
        )


async def get_user_achievements(user_id: int):
    rows = await fetch(
        """
        SELECT a.*, COALESCE(ua.progress, 0) AS progress,
               COALESCE(ua.completed, FALSE) AS completed, ua.completed_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON ua.achievement_id = a.achievement_id AND ua.user_id = $1
        ORDER BY a.category, a.condition_value
        """,
        int(user_id),
    )
    return [dict(r) for r in rows]


async def update_achievement_progress(user_id: int, condition_type: str, value: int):
    """Check and update achievements matching condition_type."""
    rows = await fetch(
        "SELECT * FROM achievements WHERE condition_type = $1", condition_type
    )
    completed_new = []
    for a in rows:
        aid = a["achievement_id"]
        needed = int(a["condition_value"])
        row = await fetchrow(
            "SELECT * FROM user_achievements WHERE user_id = $1 AND achievement_id = $2",
            int(user_id), aid,
        )
        if row and row["completed"]:
            continue
        progress = min(value, needed)
        done = progress >= needed
        await execute(
            """
            INSERT INTO user_achievements (user_id, achievement_id, progress, completed, completed_at)
            VALUES ($1, $2, $3, $4, CASE WHEN $4 THEN NOW() ELSE NULL END)
            ON CONFLICT (user_id, achievement_id) DO UPDATE SET
                progress = GREATEST(user_achievements.progress, $3),
                completed = user_achievements.completed OR $4,
                completed_at = CASE WHEN (user_achievements.completed OR $4) AND user_achievements.completed_at IS NULL
                    THEN NOW() ELSE user_achievements.completed_at END
            """,
            int(user_id), aid, progress, done,
        )
        if done and (not row or not row["completed"]):
            completed_new.append(dict(a))
    return completed_new
