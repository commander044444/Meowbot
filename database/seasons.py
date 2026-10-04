# ==========================================
# Seasons Repository
# ==========================================

from .pool import fetchrow, fetch, execute, fetchval


def _d(row):
    return dict(row) if row else None


async def get_active_season():
    return _d(await fetchrow(
        "SELECT * FROM seasons WHERE active = TRUE ORDER BY season_number DESC LIMIT 1"
    ))


async def create_season(season_number: int, start_date: str, end_date: str):
    await execute(
        """
        INSERT INTO seasons (season_number, start_date, end_date, active)
        VALUES ($1, $2::date, $3::date, TRUE)
        ON CONFLICT (season_number) DO UPDATE SET
            start_date = $2::date, end_date = $3::date, active = TRUE
        """,
        int(season_number), start_date, end_date,
    )


async def close_active_season():
    await execute("UPDATE seasons SET active = FALSE WHERE active = TRUE")


async def get_next_season_number() -> int:
    val = await fetchval("SELECT MAX(season_number) FROM seasons")
    return int(val or 0) + 1


async def save_season_result(season_id: int, user_id: int, meow_points: int, final_rank: int, chat_id=None):
    await execute(
        """
        INSERT INTO season_results (season_id, user_id, chat_id, meow_points, final_rank)
        VALUES ($1, $2, $3, $4, $5)
        """,
        int(season_id), int(user_id), str(chat_id) if chat_id else None,
        int(meow_points), int(final_rank),
    )


async def get_season_history(limit: int = 10):
    rows = await fetch(
        """
        SELECT * FROM seasons
        ORDER BY season_number DESC
        LIMIT $1
        """,
        int(limit),
    )
    return [_d(r) for r in rows]
