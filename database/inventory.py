from .pool import fetch, fetchrow, execute, fetchval
import json


async def get_inventory(user_id: int):
    rows = await fetch(
        "SELECT * FROM inventory WHERE user_id = $1 ORDER BY item_type, item_id",
        int(user_id),
    )
    return [dict(r) for r in rows]


async def add_item(user_id: int, item_id: str, item_type: str, quantity: int = 1, meta: dict = None):
    await execute(
        """
        INSERT INTO inventory (user_id, item_id, item_type, quantity, meta)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        ON CONFLICT (user_id, item_id) DO UPDATE SET
            quantity = inventory.quantity + $4
        """,
        int(user_id), item_id, item_type, int(quantity), json.dumps(meta or {}),
    )


async def remove_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    result = await execute(
        """
        UPDATE inventory SET quantity = quantity - $3
        WHERE user_id = $1 AND item_id = $2 AND quantity >= $3
        """,
        int(user_id), item_id, int(quantity),
    )
    if result == "UPDATE 0":
        return False
    await execute(
        "DELETE FROM inventory WHERE user_id = $1 AND item_id = $2 AND quantity <= 0",
        int(user_id), item_id,
    )
    return True


async def seed_shop():
    items = [
        ("food_basic", "غذای ساده", "گرسنگی Pet رو کم می‌کنه", 20, -1, "common", "food", {"hunger": 20}),
        ("food_premium", "غذای ویژه", "گرسنگی + رابطه", 50, -1, "rare", "food", {"hunger": 40, "relationship": 5}),
        ("toy_ball", "توپ بازی", "انرژی و XP", 30, -1, "common", "toy", {"energy": 10, "xp": 5}),
        ("gift_flower", "گل هدیه", "رابطه +۱۰", 40, -1, "rare", "gift", {"relationship": 10}),
        ("boost_xp", "بوست XP", "XP دوبرابر برای ۱ ساعت", 100, 50, "epic", "boost", {"xp_mult": 2, "duration": 3600}),
    ]
    for it in items:
        await execute(
            """
            INSERT INTO shop_items (item_id, name, description, price, stock, rarity, item_type, effect)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
            ON CONFLICT (item_id) DO NOTHING
            """,
            it[0], it[1], it[2], it[3], it[4], it[5], it[6], json.dumps(it[7]),
        )


async def get_shop_items():
    rows = await fetch("SELECT * FROM shop_items WHERE active = TRUE ORDER BY price")
    return [dict(r) for r in rows]
