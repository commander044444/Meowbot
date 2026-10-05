# ==========================================
# Pets Repository
# ==========================================

from .pool import fetchrow, execute, fetchval


def _d(row):
    return dict(row) if row else None


async def get_pet(user_id: int):
    return _d(await fetchrow("SELECT * FROM pets WHERE user_id = $1", int(user_id)))


async def pet_exists(user_id: int) -> bool:
    return bool(await fetchval("SELECT 1 FROM pets WHERE user_id = $1", int(user_id)))


async def create_pet(user_id: int, pet_name: str = "", awaiting_name: bool = True):
    await execute(
        """
        INSERT INTO pets (
            user_id, pet_name, level, xp, relationship, hunger, energy, mood, health,
            awaiting_name
        ) VALUES ($1, $2, 1, 0, 50, 80, 80, 70, 100, $3)
        ON CONFLICT (user_id) DO UPDATE SET
            awaiting_name = EXCLUDED.awaiting_name
            WHERE pets.pet_name IS NULL OR pets.pet_name = '' OR pets.awaiting_name = TRUE
        """,
        int(user_id), pet_name or "", bool(awaiting_name),
    )
    return await get_pet(user_id)


async def update_pet(user_id: int, **fields):
    if not fields:
        return
    allowed = {
        "pet_name", "level", "xp", "relationship", "hunger", "energy", "mood", "health",
        "is_sleeping", "sleep_until", "games_played", "foods_given", "gifts_received",
        "interaction_count", "last_feed", "last_play", "last_pet", "last_sleep",
        "last_gift", "last_interaction", "last_random", "awaiting_name", "last_point_claim",
    }
    sets, args, i = [], [int(user_id)], 2
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ${i}")
            args.append(v)
            i += 1
    if not sets:
        return
    await execute(f"UPDATE pets SET {', '.join(sets)} WHERE user_id = $1", *args)


async def delete_pet(user_id: int):
    await execute("DELETE FROM pets WHERE user_id = $1", int(user_id))


async def count_pets() -> int:
    return int(await fetchval("SELECT COUNT(*) FROM pets") or 0)
