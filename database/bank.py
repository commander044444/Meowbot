# ==========================================
# Bank Repository
# ==========================================

from .pool import fetchrow, execute, fetchval
import random


def _d(row):
    return dict(row) if row else None


def _generate_card() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(16))


async def get_bank(user_id: int):
    return _d(await fetchrow("SELECT * FROM banks WHERE user_id = $1", int(user_id)))


async def get_bank_by_card(card_number: str):
    return _d(await fetchrow("SELECT * FROM banks WHERE card_number = $1", str(card_number)))


async def card_number_exists(card_number: str) -> bool:
    return bool(await fetchval("SELECT 1 FROM banks WHERE card_number = $1", str(card_number)))


async def create_bank(user_id: int, card_number: str = None):
    if not card_number:
        for _ in range(20):
            card_number = _generate_card()
            if not await card_number_exists(card_number):
                break
    await execute(
        """
        INSERT INTO banks (user_id, card_number, balance)
        VALUES ($1, $2, 0)
        ON CONFLICT (user_id) DO NOTHING
        """,
        int(user_id), card_number,
    )
    return await get_bank(user_id)


async def update_bank_balance(user_id: int, delta: int) -> bool:
    if delta >= 0:
        await execute(
            "UPDATE banks SET balance = balance + $2 WHERE user_id = $1",
            int(user_id), int(delta),
        )
        return True
    result = await execute(
        "UPDATE banks SET balance = balance + $2 WHERE user_id = $1 AND balance >= $3",
        int(user_id), int(delta), abs(int(delta)),
    )
    return result != "UPDATE 0"


async def set_bank_pending(user_id: int, action: str):
    await execute(
        """
        INSERT INTO bank_pending (user_id, action) VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET action = $2, created_at = NOW()
        """,
        int(user_id), action,
    )


async def get_bank_pending(user_id: int):
    return _d(await fetchrow("SELECT * FROM bank_pending WHERE user_id = $1", int(user_id)))


async def clear_bank_pending(user_id: int):
    await execute("DELETE FROM bank_pending WHERE user_id = $1", int(user_id))


async def bank_transfer(sender_id: int, receiver_id: int, amount: int) -> bool:
    ok = await update_bank_balance(sender_id, -amount)
    if not ok:
        return False
    await update_bank_balance(receiver_id, amount)
    return True
