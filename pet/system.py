# ==========================================
# 🐾 Pet System (Async + Glass UI)
# ==========================================

import random
import time
import re

from config import (
    PET_FEED_COOLDOWN, PET_PLAY_COOLDOWN, PET_PET_COOLDOWN,
    PET_SLEEP_COOLDOWN, PET_GIFT_COOLDOWN,
    PET_FEED_HUNGER, PET_PLAY_ENERGY_COST, PET_PLAY_RELATIONSHIP,
    PET_PET_RELATIONSHIP, PET_SLEEP_ENERGY,
    PET_XP_FEED, PET_XP_PLAY, PET_XP_PET, PET_XP_GIFT,
    PET_XP_PER_LEVEL, PET_XP_GROWTH, PET_STAT_MAX, PET_STAT_MIN,
    PET_MAX_LEVEL, PET_SLEEP_DURATION, PET_GIFT_CHANCE_BASE,
    PET_POINT_COOLDOWN, PET_POINT_BASE, PET_POINT_PER_LEVEL,
    PET_LEVELUP_COIN_PER_LEVEL,
)
from database.pets import get_pet, create_pet, update_pet, pet_exists
from database.users import get_user, create_user, get_meow_coins, spend_meow_coins, add_meow_points, add_meow_coins
from utils.keyboards import glass,  pet_home_kb, pet_play_kb, back_main_kb

FEED_MESSAGES = [
    "🐱 {name} با ذوق غذاشو خورد! 😋",
    "🐱 {name} حتی ظرف رو هم لیس زد 😂",
    "🐱 {name} گفت: بازم داری؟ 👀",
    "🐱 {name} با خوشحالی میووو کرد! 🍖",
    "🐱 {name} سریع غذا رو تموم کرد 😸",
]
PLAY_MESSAGES = {
    "ball": ["🐱 {name} دنبال توپ دوید! 💨", "🐱 {name} توپ رو گرفت 🎾", "🐱 {name} با توپ بازی کرد!"],
    "yarn": ["🐱 {name} با نخ سرگرم شد 🧶", "🐱 {name} توی نخ پیچیده شد 😂", "🐱 {name} نخ رو تعقیب کرد!"],
    "laser": ["🐱 {name} دنبال لیزر دوید! 🔴", "🐱 {name} سعی کرد لیزر رو بگیره 😹", "🐱 {name} دیوونه لیزر شد!"],
}
PET_MESSAGES = [
    "🐱 {name} خیلی خوشحال شد ❤️",
    "🐱 {name} خودش رو به دستت مالید 🥺",
    "🐱 {name} خرخر می‌کنه... 😸",
    "🐱 {name} چشم‌هاش رو بست و آروم شد ✨",
]
SLEEP_MESSAGES = ["💤 {name} خوابیده...", "😴 {name} خواب عمیق 💤", "🐱 {name} یه جا نرم پیدا کرد 🌙"]
WAKE_MESSAGES = ["🐱 {name} از خواب بیدار شد! ⚡", "🐱 {name} کش و قوس اومد 😸"]
GIFT_MESSAGES = ["🎁 {name} برات یه هدیه آورد!", "🐱 {name} یه سورپرایز پیدا کرد! ✨"]
NO_GIFT_MESSAGES = ["🐱 {name} چیزی پیدا نکرد 😅", "🐱 {name} دست خالی برگشت."]
CALL_MESSAGES = [
    "🐱 {name}: میووو! 😸\n«اومدم!»",
    "🐱 {name} دوید سمتت! 💨",
    "🐱 {name}: میو میو! ❤️",
]


def clamp(v, lo=PET_STAT_MIN, hi=PET_STAT_MAX):
    return max(lo, min(hi, int(v)))


def xp_needed(level):
    level = max(1, int(level))
    base = level * PET_XP_PER_LEVEL
    growth = int(base * (level - 1) * PET_XP_GROWTH)
    return max(1, base + growth)


def _apply_xp(level, xp):
    """اضافه کردن XP و ارتقا سطح در صورت نیاز. Returns (level, xp, leveled_up)."""
    level = max(1, int(level or 1))
    xp = max(0, int(xp or 0))
    leveled = False
    max_level = int(PET_MAX_LEVEL) if PET_MAX_LEVEL else 100
    while level < max_level:
        need = xp_needed(level)
        if xp < need:
            break
        xp -= need
        level += 1
        leveled = True
    if level >= max_level:
        level = max_level
        xp = min(xp, xp_needed(level) - 1) if level < max_level else xp
    return level, xp, leveled


def hourly_points(level):
    return PET_POINT_BASE + max(1, int(level)) * PET_POINT_PER_LEVEL


def fmt_cd(sec):
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}" if m else f"{s}ث"


def pet_card(pet: dict) -> str:
    name = pet.get("pet_name") or "بی‌نام"
    level = int(pet.get("level") or 1)
    xp = int(pet.get("xp") or 0)
    need = xp_needed(level)
    rel = int(pet.get("relationship") or 50)
    hunger = int(pet.get("hunger") or 0)
    energy = int(pet.get("energy") or 0)
    mood = int(pet.get("mood") or 70)
    health = int(pet.get("health") or 100)
    sleeping = pet.get("is_sleeping")

    def bar(v):
        filled = int(v / 10)
        return "█" * filled + "░" * (10 - filled)

    status = "💤 خواب" if sleeping else "✨ بیدار"
    return (
        f"🐾 **{name}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"⭐ Level `{level}`  |  XP `{xp}/{need}`\n"
        f"❤️ رابطه  {bar(rel)} `{rel}`\n"
        f"🍖 گرسنگی {bar(hunger)} `{hunger}`\n"
        f"⚡ انرژی  {bar(energy)} `{energy}`\n"
        f"😊 حال    {bar(mood)} `{mood}`\n"
        f"💚 سلامت  {bar(health)} `{health}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"وضعیت: {status}\n"
        f"تعامل‌ها: `{pet.get('interaction_count', 0)}`"
    )


async def ensure_user(user_id, first_name="", username=""):
    u = await get_user(user_id)
    if not u:
        await create_user(user_id, first_name=first_name, username=username)
    return await get_user(user_id)


async def get_or_create_flow(user_id):
    pet = await get_pet(user_id)
    if not pet:
        await create_pet(user_id, awaiting_name=True)
        pet = await get_pet(user_id)
        msg = "✨ Pet جدید ساخته شد!\n\n✏️ یک نام برای پیشی‌ات بفرست (۲ تا ۲۰ حرف).\nمثال: میوشا"
        return pet, msg, pet_home_kb(True, True)
    name = (pet.get("pet_name") or "").strip()
    awaiting = bool(pet.get("awaiting_name")) or (not name)
    if awaiting:
        msg = "✏️ هنوز نام نگذاشتی!\nهمین الان یک نام قشنگ بفرست (۲ تا ۲۰ حرف)."
        return pet, msg, pet_home_kb(True, True)
    return pet, pet_card(pet), pet_home_kb(True, False)



async def handle_name_input(user_id, text: str):
    """اگر Pet منتظر نام است، نام را ذخیره می‌کند. وگرنه (None, None)."""
    pet = await get_pet(user_id)
    if not pet:
        return None, None

    awaiting = pet.get("awaiting_name")
    if awaiting is None:
        awaiting = False
    if isinstance(awaiting, (int, float)):
        awaiting = bool(awaiting)
    if isinstance(awaiting, str):
        awaiting = awaiting.lower() in ("1", "true", "t", "yes")

    current_name = (pet.get("pet_name") or "").strip()
    if not current_name:
        awaiting = True

    if not awaiting:
        return None, None

    name = (text or "").strip()
    blocked = {
        "/start", "start", "منو", "شروع", "/menu", "/owner", "owner",
        "پنل مالک", "پروفایل", "رنکینگ", "تنظیم گروه", "لغو", "cancel",
    }
    if name.lower() in blocked or name in blocked:
        return None, None

    if len(name) < 2 or len(name) > 20:
        return (
            "❌ نام باید بین ۲ تا ۲۰ حرف باشد.\nیک نام قشنگ بفرست 🐱",
            pet_home_kb(True, True),
        )

    if not re.match(r"^[\w\u0600-\u06FF\s\-]+$", name, re.UNICODE):
        return "❌ فقط حروف، عدد و فاصله مجاز است.", pet_home_kb(True, True)

    try:
        await update_pet(user_id, pet_name=name, awaiting_name=False)
    except Exception as e:
        return f"❌ ذخیره نام ناموفق بود: `{e}`", pet_home_kb(True, True)

    pet = await get_pet(user_id)
    saved = (pet or {}).get("pet_name") or ""
    if not saved or pet.get("awaiting_name"):
        try:
            from database.pool import execute
            await execute(
                "UPDATE pets SET pet_name = $2, awaiting_name = FALSE WHERE user_id = $1",
                int(user_id),
                name,
            )
            pet = await get_pet(user_id)
            saved = (pet or {}).get("pet_name") or name
        except Exception as e:
            return f"❌ خطای دیتابیس هنگام ذخیره نام: `{e}`", pet_home_kb(True, True)

    return (
        f"🎉 نام پیشی‌ات ثبت شد: **{saved}**\n\n{pet_card(pet)}",
        pet_home_kb(True, False),
    )



async def try_call_pet(user_id, text: str):
    """
    اگر متن نام Pet باشد → پیام صدا + دکمه باز کردن پنل کامل.
    Returns (text, keyboard) یا None
    """
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name") or not pet.get("pet_name"):
        return None
    name = (pet.get("pet_name") or "").strip()
    if not name:
        return None
    raw = (text or "").strip()
    if not raw:
        return None
    # تطبیق نام (بدون حساسیت به فاصله اضافه)
    if raw.lower() != name.lower() and name not in raw and raw not in name:
        # فقط اگر دقیقاً نام یا «نام» + کمی پسوند
        norm = re.sub(r"\s+", "", raw).lower()
        nname = re.sub(r"\s+", "", name).lower()
        if norm != nname and not raw.lower().startswith(name.lower()):
            return None
    msg = random.choice(CALL_MESSAGES).format(name=name)
    # دکمه باز کردن همان پنل کامل Pet
    kb = glass(
        [("🐾 باز کردن پنل پیشی", "pet:home")],
        [("🍖 غذا", "pet:feed"), ("🎾 بازی", "pet:play_menu")],
        [("🫶 نوازش", "pet:pet"), ("💤 خواب", "pet:sleep")],
    )
    return msg, kb



async def _need_item(user_id, item_type: str, title: str):
    """اگر آیتم ندارد پیام خرید برگردان."""
    from database.inventory import find_usable_item
    item, meta = await find_usable_item(user_id, item_type)
    if not item:
        return None, None, (
            f"❌ برای **{title}** باید از فروشگاه چیزی بخری!\n"
            f"🛒 منو → فروشگاه → آیتم‌های Pet\n\n"
            f"نوع لازم: `{item_type}`",
            pet_home_kb(True),
        )
    return item, meta, None


async def action_feed(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز و اسم بذار!", pet_home_kb(False)
    if pet.get("is_sleeping"):
        return "💤 گربه خوابه؛ اول بیدارش کن.", pet_home_kb(True)

    item, meta, err = await _need_item(user_id, "food", "غذا دادن")
    if err:
        return err

    from database.inventory import consume_use
    ok, left, _ = await consume_use(user_id, item["item_id"], 1)
    if not ok:
        return "❌ این غذا تموم شده. از فروشگاه بخر.", pet_home_kb(True)

    effect = meta if meta else {}
    # effect ممکن است از shop باشد — از meta آیتم
    hunger_add = int(effect.get("hunger") or 25)
    rel_add = int(effect.get("relationship") or 0)
    xp_add = int(effect.get("xp") or PET_XP_FEED)
    mood_add = int(effect.get("mood") or 3)

    now = time.time()
    cd = PET_FEED_COOLDOWN - (now - float(pet.get("last_feed") or 0))
    if cd > 0:
        return f"⏳ غذا بعد از `{fmt_cd(cd)}`", pet_home_kb(True)

    hunger = clamp(int(pet.get("hunger") or 0) + hunger_add)
    rel = clamp(int(pet.get("relationship") or 50) + rel_add)
    mood = clamp(int(pet.get("mood") or 70) + mood_add)
    xp = int(pet.get("xp") or 0) + xp_add
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(
        user_id,
        hunger=hunger, relationship=rel, mood=mood, xp=xp, level=level,
        last_feed=now, foods_given=int(pet.get("foods_given") or 0) + 1,
        interaction_count=int(pet.get("interaction_count") or 0) + 1,
        last_interaction=now,
    )
    name = pet.get("pet_name") or "Pet"
    msg = random.choice(FEED_MESSAGES).format(name=name)
    msg += f"\n🥣 از: {item.get('item_id')}\n🔋 باقی استفاده غذا: `{left}`"
    if leveled:
        msg += f"\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_play(user_id, kind="ball"):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    if pet.get("is_sleeping"):
        return "💤 خوابه؛ نمی‌تونه بازی کنه.", pet_home_kb(True)

    item, meta, err = await _need_item(user_id, "toy", "بازی کردن")
    if err:
        return err

    from database.inventory import consume_use
    ok, left, _ = await consume_use(user_id, item["item_id"], 1)
    if not ok:
        return "❌ اسباب‌بازی تموم شده. از فروشگاه بخر.", pet_home_kb(True)

    effect = meta or {}
    energy_add = int(effect.get("energy") or 15)
    xp_add = int(effect.get("xp") or PET_XP_PLAY)
    rel_add = int(effect.get("relationship") or 3)
    mood_add = int(effect.get("mood") or 5)

    now = time.time()
    cd = PET_PLAY_COOLDOWN - (now - float(pet.get("last_play") or 0))
    if cd > 0:
        return f"⏳ بازی بعد از `{fmt_cd(cd)}`", pet_home_kb(True)

    energy = clamp(int(pet.get("energy") or 0) + energy_add)
    # بازی کمی گرسنگی می‌آورد
    hunger = clamp(int(pet.get("hunger") or 80) - 5)
    rel = clamp(int(pet.get("relationship") or 50) + rel_add)
    mood = clamp(int(pet.get("mood") or 70) + mood_add)
    xp = int(pet.get("xp") or 0) + xp_add
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(
        user_id,
        energy=energy, hunger=hunger, relationship=rel, mood=mood,
        xp=xp, level=level, last_play=now,
        games_played=int(pet.get("games_played") or 0) + 1,
        interaction_count=int(pet.get("interaction_count") or 0) + 1,
        last_interaction=now,
    )
    name = pet.get("pet_name") or "Pet"
    msg = random.choice(PLAY_MESSAGES).format(name=name)
    msg += f"\n🎾 با: {item.get('item_id')}\n🔋 باقی استفاده اسباب‌بازی: `{left}`"
    if leveled:
        msg += f"\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_pet(user_id):
    """نوازش — بدون آیتم فروشگاه."""
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    if pet.get("is_sleeping"):
        return "💤 داره می‌خوابه...", pet_home_kb(True)
    now = time.time()
    cd = PET_PET_COOLDOWN - (now - float(pet.get("last_pet") or 0))
    if cd > 0:
        return f"⏳ نوازش بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    rel = clamp(int(pet.get("relationship") or 50) + PET_PET_RELATIONSHIP)
    xp = int(pet.get("xp") or 0) + PET_XP_PET
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(
        user_id, relationship=rel, xp=xp, level=level, last_pet=now,
        interaction_count=int(pet.get("interaction_count") or 0) + 1,
        last_interaction=now, mood=clamp(int(pet.get("mood") or 70) + 3),
    )
    name = pet.get("pet_name") or "Pet"
    msg = random.choice(PET_MESSAGES).format(name=name)
    if leveled:
        msg += f"\n\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_sleep(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    now = time.time()

    # بیدار شدن
    if pet.get("is_sleeping"):
        until = float(pet.get("sleep_until") or 0)
        if now >= until:
            energy = clamp(int(pet.get("energy") or 0) + PET_SLEEP_ENERGY)
            await update_pet(user_id, is_sleeping=False, sleep_until=0, energy=energy, last_sleep=now)
            name = pet.get("pet_name") or "Pet"
            pet = await get_pet(user_id)
            return random.choice(WAKE_MESSAGES).format(name=name) + "\n\n" + pet_card(pet), pet_home_kb(True)
        return f"💤 هنوز خوابه... `{fmt_cd(until - now)}` مونده", pet_home_kb(True)

    # برای خواباندن باید جای خواب داشته باشد
    item, meta, err = await _need_item(user_id, "bed", "خواباندن")
    if err:
        return (
            "❌ برای خوابوندن گربه باید **جای خواب** از فروشگاه بخری!\n"
            "🛒 منو → فروشگاه → 🛏 جای خواب\n\n"
            "بدون جای خواب نمی‌تونه راحت بخوابه 😿",
            pet_home_kb(True),
        )

    cd = PET_SLEEP_COOLDOWN - (now - float(pet.get("last_sleep") or 0))
    if cd > 0:
        return f"⏳ خواب بعد از `{fmt_cd(cd)}`", pet_home_kb(True)

    from database.inventory import consume_use
    ok, left, _ = await consume_use(user_id, item["item_id"], 1)
    if not ok:
        return "❌ جای خواب فرسوده شده. یکی جدید از فروشگاه بخر.", pet_home_kb(True)

    effect = meta or {}
    energy_bonus = int(effect.get("energy") or PET_SLEEP_ENERGY)
    duration = PET_SLEEP_DURATION

    await update_pet(
        user_id,
        is_sleeping=True,
        sleep_until=now + duration,
        last_sleep=now,
    )
    name = pet.get("pet_name") or "Pet"
    msg = random.choice(SLEEP_MESSAGES).format(name=name)
    msg += f"\n🛏 با: {item.get('item_id')}\n🔋 باقی استفاده جای خواب: `{left}`\n⏱ حدود {duration} ثانیه"
    return msg, pet_home_kb(True)


async def action_gift(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)

    item, meta, err = await _need_item(user_id, "gift", "هدیه دادن")
    if err:
        return err

    now = time.time()
    cd = PET_GIFT_COOLDOWN - (now - float(pet.get("last_gift") or 0))
    if cd > 0:
        return f"⏳ هدیه بعد از `{fmt_cd(cd)}`", pet_home_kb(True)

    from database.inventory import consume_use
    ok, left, _ = await consume_use(user_id, item["item_id"], 1)
    if not ok:
        return "❌ هدیه تموم شده.", pet_home_kb(True)

    effect = meta or {}
    rel_add = int(effect.get("relationship") or 12)
    mood_add = int(effect.get("mood") or 8)
    xp_add = int(effect.get("xp") or PET_XP_GIFT)

    rel = clamp(int(pet.get("relationship") or 50) + rel_add)
    mood = clamp(int(pet.get("mood") or 70) + mood_add)
    xp = int(pet.get("xp") or 0) + xp_add
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(
        user_id,
        relationship=rel, mood=mood, xp=xp, level=level,
        last_gift=now, gifts_received=int(pet.get("gifts_received") or 0) + 1,
        last_interaction=now,
        interaction_count=int(pet.get("interaction_count") or 0) + 1,
    )
    name = pet.get("pet_name") or "Pet"
    msg = f"🎁 به **{name}** هدیه دادی!\nباقی استفاده: `{left}`"
    if leveled:
        msg += f"\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def handle_pet_callback(user_id, data: str, first_name="", username=""):
    await ensure_user(user_id, first_name, username)

    if data == "pet:home":
        pet, text, kb = await get_or_create_flow(user_id)
        return text, kb

    if data == "pet:create":
        await create_pet(user_id, awaiting_name=True)
        try:
            from database.pool import execute
            await execute(
                "UPDATE pets SET awaiting_name = TRUE WHERE user_id = $1",
                int(user_id),
            )
        except Exception:
            pass
        return (
            "✨ Pet ساخته شد!\n✏️ الان فقط یک نام بفرست (۲ تا ۲۰ حرف).\nمثال: پیشی",
            pet_home_kb(True, True),
        )

    if data == "pet:feed":
        return await action_feed(user_id)

    if data == "pet:play_menu":
        return "🎾 چه بازی؟", pet_play_kb()

    if data.startswith("pet:play:"):
        kind = data.split(":")[-1]
        return await action_play(user_id, kind)

    if data == "pet:pet":
        return await action_pet(user_id)

    if data == "pet:sleep":
        return await action_sleep(user_id)

    if data == "pet:gift":
        return await action_gift(user_id)

    if data == "pet:rename":
        await update_pet(user_id, awaiting_name=True)
        try:
            from database.pool import execute
            await execute(
                "UPDATE pets SET awaiting_name = TRUE WHERE user_id = $1",
                int(user_id),
            )
        except Exception:
            pass
        return (
            "✏️ نام جدید را همین الان در چت بفرست (۲ تا ۲۰ حرف):",
            pet_home_kb(True, True),
        )

    if data == "pet:delete":
        return (
            "⚠️ مطمئنی می‌خوای Pet رو حذف کنی؟",
            glass(
                [("✅ بله حذف کن", "pet:delete_yes"), ("❌ نه", "pet:home")],
            ),
        )

    if data == "pet:delete_yes":
        from database.pets import delete_pet
        await delete_pet(user_id)
        return "🗑️ Pet حذف شد.", pet_home_kb(False, False)


    if data == "pet:status":
        pet, text, kb = await get_or_create_flow(user_id)
        return text, kb

    if data == "pet:await_hint":
        return "✏️ همین الان نام پیشی را در چت بنویس (۲ تا ۲۰ حرف).", pet_home_kb(True, True)

    if data == "pet:levelup":
        pet = await get_pet(user_id)
        if not pet or pet.get("awaiting_name"):
            return "❌ اول Pet بساز!", pet_home_kb(False)
        return (
            "⬆️ ارتقا لول با XP از غذا/بازی/نوازش پر می‌شود.\n"
            "وقتی XP کافی باشد خودکار Level Up می‌شوی.",
            pet_home_kb(True),
        )

    # fallback
    pet, text, kb = await get_or_create_flow(user_id)
    return text, kb
