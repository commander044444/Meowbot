# ==========================================
# Inventory + Shop
# ==========================================

from .pool import fetch, fetchrow, execute, fetchval
import json


async def get_inventory(user_id: int):
    rows = await fetch(
        "SELECT * FROM inventory WHERE user_id = $1 AND quantity > 0 ORDER BY item_type, item_id",
        int(user_id),
    )
    return [dict(r) for r in rows]


async def get_inv_item(user_id: int, item_id: str):
    row = await fetchrow(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_id = $2",
        int(user_id), item_id,
    )
    return dict(row) if row else None


def _meta(row) -> dict:
    if not row:
        return {}
    m = row.get("meta") if isinstance(row, dict) else None
    if m is None:
        return {}
    if isinstance(m, dict):
        return m
    if isinstance(m, str):
        try:
            parsed = json.loads(m)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    try:
        return dict(m)
    except Exception:
        return {}


async def add_item(user_id: int, item_id: str, item_type: str, quantity: int = 1, meta: dict = None):
    """اضافه کردن آیتم. اگر meta.uses_left باشد، روی خرید جدید ست می‌شود / جمع می‌شود."""
    meta = dict(meta or {})
    existing = await get_inv_item(user_id, item_id)
    if existing:
        old_meta = _meta(existing)
        # اگر durability دارد، uses را جمع کن
        if "uses_left" in meta or "uses_left" in old_meta:
            old_uses = int(old_meta.get("uses_left") or 0)
            add_uses = int(meta.get("uses_left") or meta.get("max_uses") or 0)
            if add_uses <= 0 and "max_uses" in meta:
                add_uses = int(meta["max_uses"])
            new_uses = old_uses + add_uses
            max_u = int(meta.get("max_uses") or old_meta.get("max_uses") or new_uses)
            new_meta = {**old_meta, **meta, "uses_left": new_uses, "max_uses": max_u}
            await execute(
                """
                UPDATE inventory SET quantity = quantity + $3, meta = $4::jsonb
                WHERE user_id = $1 AND item_id = $2
                """,
                int(user_id), item_id, int(quantity), json.dumps(new_meta),
            )
            return
        await execute(
            """
            UPDATE inventory SET quantity = quantity + $3
            WHERE user_id = $1 AND item_id = $2
            """,
            int(user_id), item_id, int(quantity),
        )
        return

    # آیتم جدید
    if "max_uses" in meta and "uses_left" not in meta:
        meta["uses_left"] = int(meta["max_uses"])
    await execute(
        """
        INSERT INTO inventory (user_id, item_id, item_type, quantity, meta)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        ON CONFLICT (user_id, item_id) DO UPDATE SET
            quantity = inventory.quantity + EXCLUDED.quantity
        """,
        int(user_id), item_id, item_type, int(quantity), json.dumps(meta),
    )


async def remove_item(user_id: int, item_id: str, quantity: int = 1) -> bool:
    result = await execute(
        """
        UPDATE inventory SET quantity = quantity - $3
        WHERE user_id = $1 AND item_id = $2 AND quantity >= $3
        """,
        int(user_id), item_id, int(quantity),
    )
    # asyncpg may return status string
    await execute(
        "DELETE FROM inventory WHERE user_id = $1 AND item_id = $2 AND quantity <= 0",
        int(user_id), item_id,
    )
    return True


async def consume_use(user_id: int, item_id: str, amount: int = 1) -> tuple:
    """
    یک بار استفاده از آیتم با دوام (uses_left).
    Returns (ok, uses_left, message)
    """
    row = await get_inv_item(user_id, item_id)
    if not row or int(row.get("quantity") or 0) <= 0:
        return False, 0, "نداری"
    meta = _meta(row)
    uses = int(meta.get("uses_left") or 0)
    if uses <= 0:
        # آیتم بدون دوام → یک عدد از quantity کم کن
        await remove_item(user_id, item_id, 1)
        return True, 0, "مصرف شد"
    if uses < amount:
        return False, uses, "مصرف باقی‌مانده کافی نیست"
    uses -= amount
    meta["uses_left"] = uses
    if uses <= 0:
        await execute(
            "DELETE FROM inventory WHERE user_id = $1 AND item_id = $2",
            int(user_id), item_id,
        )
        return True, 0, "تموم شد"
    await execute(
        "UPDATE inventory SET meta = $3::jsonb WHERE user_id = $1 AND item_id = $2",
        int(user_id), item_id, json.dumps(meta),
    )
    return True, uses, "ok"


async def find_usable_item(user_id: int, item_type: str):
    """اولین آیتم از نوع مشخص که هنوز uses دارد."""
    rows = await get_inventory(user_id)
    for r in rows:
        if (r.get("item_type") or "") != item_type:
            continue
        meta = _meta(r)
        uses = meta.get("uses_left")
        if uses is None:
            # quantity-based
            if int(r.get("quantity") or 0) > 0:
                return r, meta
        elif int(uses) > 0:
            return r, meta
    return None, {}


async def has_item_type(user_id: int, item_type: str) -> bool:
    item, _ = await find_usable_item(user_id, item_type)
    return item is not None


async def has_item_id(user_id: int, item_id: str) -> bool:
    row = await get_inv_item(user_id, item_id)
    if not row or int(row.get("quantity") or 0) <= 0:
        return False
    meta = _meta(row)
    uses = meta.get("uses_left")
    if uses is None:
        return True
    return int(uses) > 0


# ---------- Shop catalog (Pet-focused) ----------
# max_uses: تعداد استفاده (مثلاً ۲۰)
# effect: اثر روی Pet

PET_SHOP_CATALOG = [
    # ─── غذا ─────────────────────────────────────────────
    # ارزان، دوام بالا، اثر کم
    {
        "item_id": "food_kibble",
        "name": "🥣 خوراک خشک",
        "description": "غذای روزمره. هر وعده کمی گرسنگی را کم می‌کند. بسته بزرگ، مناسب مصرف مداوم.",
        "price": 35,
        "rarity": "common",
        "item_type": "food",
        "effect": {"hunger": 18, "mood": 1, "max_uses": 40},
    },
    # متوسط: طعم بهتر + رابطه
    {
        "item_id": "food_fish",
        "name": "🐟 ماهی تازه",
        "description": "ماهی واقعی. گرسنگی را خوب کم می‌کند و کمی رابطه را بالا می‌برد. بسته متوسط.",
        "price": 75,
        "rarity": "rare",
        "item_type": "food",
        "effect": {"hunger": 35, "relationship": 4, "mood": 4, "max_uses": 15},
    },
    # گران، کم‌تعداد، قوی + XP
    {
        "item_id": "food_premium",
        "name": "🍣 سوشی ویژه",
        "description": "وعده لوکس. گرسنگی زیاد، خلق‌وخو و XP. تعداد کم — برای موقعیت خاص.",
        "price": 140,
        "rarity": "epic",
        "item_type": "food",
        "effect": {"hunger": 55, "mood": 10, "relationship": 8, "xp": 12, "max_uses": 6},
    },
    # خیلی قوی، خیلی کم
    {
        "item_id": "food_steak",
        "name": "🥩 استیک گربه",
        "description": "یک وعده سنگین. تقریباً گرسنگی را پر می‌کند و روحیه را قوی بالا می‌برد.",
        "price": 95,
        "rarity": "epic",
        "item_type": "food",
        "effect": {"hunger": 70, "mood": 12, "relationship": 6, "xp": 6, "max_uses": 3},
    },
    # ─── اسباب‌بازی ──────────────────────────────────────
    {
        "item_id": "toy_ball",
        "name": "🎾 توپ ساده",
        "description": "توپ پارچه‌ای مقاوم. بازی سبک، انرژی کم، دوام بالا.",
        "price": 40,
        "rarity": "common",
        "item_type": "toy",
        "effect": {"energy": 10, "mood": 4, "xp": 4, "play_kind": "ball", "max_uses": 30},
    },
    {
        "item_id": "toy_mouse",
        "name": "🐭 موش پارچه‌ای",
        "description": "شکار ساختگی. انرژی و رابطه متوسط. دوام متوسط.",
        "price": 65,
        "rarity": "rare",
        "item_type": "toy",
        "effect": {"energy": 18, "relationship": 7, "mood": 7, "xp": 7, "play_kind": "yarn", "max_uses": 12},
    },
    {
        "item_id": "toy_laser",
        "name": "🔴 لیزر دستی",
        "description": "سرگرمی شدید. XP و خلق‌وخو بالا، ولی باتری محدود است.",
        "price": 110,
        "rarity": "epic",
        "item_type": "toy",
        "effect": {"energy": 28, "mood": 14, "xp": 14, "play_kind": "laser", "max_uses": 8},
    },
    {
        "item_id": "toy_feather",
        "name": "🪶 چوب پر",
        "description": "بازی آرام با صاحب. رابطه را خوب بالا می‌برد؛ دوام متوسط.",
        "price": 55,
        "rarity": "rare",
        "item_type": "toy",
        "effect": {"energy": 12, "relationship": 10, "mood": 6, "xp": 5, "play_kind": "yarn", "max_uses": 18},
    },
    # ─── جای خواب (الزامی برای خواب) ─────────────────────
    {
        "item_id": "bed_basic",
        "name": "🛏 تشک ساده",
        "description": "بدون جای خواب نمی‌توانی بخوابانی. انرژی معمولی، دوام خوب.",
        "price": 80,
        "rarity": "common",
        "item_type": "bed",
        "effect": {"energy": 35, "sleep_bonus_sec": 0, "max_uses": 25},
    },
    {
        "item_id": "bed_cozy",
        "name": "🧺 سبد نرم",
        "description": "خواب راحت‌تر. انرژی بیشتر و کمی خلق‌وخو. دوام متوسط.",
        "price": 130,
        "rarity": "rare",
        "item_type": "bed",
        "effect": {"energy": 50, "mood": 6, "sleep_bonus_sec": 30, "max_uses": 12},
    },
    {
        "item_id": "bed_luxury",
        "name": "👑 جای خواب لوکس",
        "description": "بهترین استراحت. انرژی قوی، خلق‌وخو، رابطه. تعداد استفاده کم.",
        "price": 200,
        "rarity": "epic",
        "item_type": "bed",
        "effect": {"energy": 70, "mood": 12, "relationship": 5, "sleep_bonus_sec": 60, "max_uses": 5},
    },
    # ─── هدیه ────────────────────────────────────────────
    {
        "item_id": "gift_flower",
        "name": "🌸 گل کوچک",
        "description": "هدیه ساده. کمی رابطه و خلق‌وخو. بسته چندتایی.",
        "price": 45,
        "rarity": "common",
        "item_type": "gift",
        "effect": {"relationship": 8, "mood": 5, "xp": 2, "max_uses": 12},
    },
    {
        "item_id": "gift_collar",
        "name": "🎀 گردنبند زنگوله‌دار",
        "description": "هدیه ماندگارتر. رابطه قوی‌تر. تعداد محدود.",
        "price": 100,
        "rarity": "rare",
        "item_type": "gift",
        "effect": {"relationship": 18, "mood": 10, "xp": 8, "max_uses": 4},
    },
    {
        "item_id": "gift_diamond",
        "name": "💎 نشان ویژه",
        "description": "کمیاب. جهش بزرگ در رابطه و XP. فقط چند بار.",
        "price": 220,
        "rarity": "legendary",
        "item_type": "gift",
        "effect": {"relationship": 30, "mood": 15, "xp": 25, "max_uses": 2},
    },
]


async def seed_shop():
    for it in PET_SHOP_CATALOG:
        await execute(
            """
            INSERT INTO shop_items (item_id, name, description, price, stock, rarity, item_type, effect, active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb, TRUE)
            ON CONFLICT (item_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                rarity = EXCLUDED.rarity,
                item_type = EXCLUDED.item_type,
                effect = EXCLUDED.effect,
                active = TRUE
            """,
            it["item_id"], it["name"], it["description"], it["price"],
            -1, it["rarity"], it["item_type"], json.dumps(it["effect"]),
        )


async def get_shop_items():
    rows = await fetch(
        "SELECT * FROM shop_items WHERE active = TRUE ORDER BY item_type, price"
    )
    return [dict(r) for r in rows]


async def get_shop_item(item_id: str):
    row = await fetchrow("SELECT * FROM shop_items WHERE item_id = $1", item_id)
    return dict(row) if row else None
