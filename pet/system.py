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
    """صدا زدن با نام Pet."""
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name") or not pet.get("pet_name"):
        return None
    name = (pet.get("pet_name") or "").strip()
    if not name:
        return None
    t = text.strip()
    if t != name and t.lower() != name.lower():
        return None
    # hourly points in groups handled by caller
    msg = random.choice(CALL_MESSAGES).format(name=name)
    now = time.time()
    last = float(pet.get("last_point_claim") or 0)
    bonus = ""
    if now - last >= PET_POINT_COOLDOWN:
        pts = hourly_points(int(pet.get("level") or 1))
        await add_meow_points(user_id, pts)
        await update_pet(user_id, last_point_claim=now, last_interaction=now,
                         interaction_count=int(pet.get("interaction_count") or 0) + 1)
        bonus = f"\n\n⭐ +{pts} امتیاز ساعتی!"
    else:
        await update_pet(user_id, last_interaction=now)
    return msg + bonus


async def action_feed(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز و نام بذار!", pet_home_kb(False, True)
    if pet.get("is_sleeping"):
        return "💤 Pet خوابه! اول بیدارش کن.", pet_home_kb(True)
    now = time.time()
    cd = PET_FEED_COOLDOWN - (now - float(pet.get("last_feed") or 0))
    if cd > 0:
        return f"⏳ غذا بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    hunger = clamp(int(pet.get("hunger") or 0) + PET_FEED_HUNGER)
    xp = int(pet.get("xp") or 0) + PET_XP_FEED
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(user_id, hunger=hunger, xp=xp, level=level, last_feed=now,
                     foods_given=int(pet.get("foods_given") or 0) + 1,
                     interaction_count=int(pet.get("interaction_count") or 0) + 1,
                     last_interaction=now, mood=clamp(int(pet.get("mood") or 70) + 5))
    name = pet.get("pet_name") or "Pet"
    msg = random.choice(FEED_MESSAGES).format(name=name)
    if leveled:
        msg += f"\n\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_play(user_id, kind="ball"):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    if pet.get("is_sleeping"):
        return "💤 خوابه!", pet_home_kb(True)
    now = time.time()
    cd = PET_PLAY_COOLDOWN - (now - float(pet.get("last_play") or 0))
    if cd > 0:
        return f"⏳ بازی بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    energy = int(pet.get("energy") or 0)
    if energy < PET_PLAY_ENERGY_COST:
        return "⚡ انرژی کافی نیست! بذار بخوابه یا بعداً.", pet_home_kb(True)
    energy = clamp(energy - PET_PLAY_ENERGY_COST)
    rel = clamp(int(pet.get("relationship") or 50) + PET_PLAY_RELATIONSHIP)
    xp = int(pet.get("xp") or 0) + PET_XP_PLAY
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(user_id, energy=energy, relationship=rel, xp=xp, level=level,
                     last_play=now, games_played=int(pet.get("games_played") or 0) + 1,
                     interaction_count=int(pet.get("interaction_count") or 0) + 1,
                     last_interaction=now, mood=clamp(int(pet.get("mood") or 70) + 8))
    name = pet.get("pet_name") or "Pet"
    msgs = PLAY_MESSAGES.get(kind, PLAY_MESSAGES["ball"])
    msg = random.choice(msgs).format(name=name)
    if leveled:
        msg += f"\n\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_pet(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    if pet.get("is_sleeping"):
        return "💤 خوابه... آروم نوازشش کن بعداً 😴", pet_home_kb(True)
    now = time.time()
    cd = PET_PET_COOLDOWN - (now - float(pet.get("last_pet") or 0))
    if cd > 0:
        return f"⏳ نوازش بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    rel = clamp(int(pet.get("relationship") or 50) + PET_PET_RELATIONSHIP)
    xp = int(pet.get("xp") or 0) + PET_XP_PET
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    await update_pet(user_id, relationship=rel, xp=xp, level=level, last_pet=now,
                     interaction_count=int(pet.get("interaction_count") or 0) + 1,
                     last_interaction=now, mood=clamp(int(pet.get("mood") or 70) + 3))
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
    if pet.get("is_sleeping"):
        until = float(pet.get("sleep_until") or 0)
        if now >= until:
            energy = clamp(int(pet.get("energy") or 0) + PET_SLEEP_ENERGY)
            await update_pet(user_id, is_sleeping=False, sleep_until=0, energy=energy, last_sleep=now)
            name = pet.get("pet_name") or "Pet"
            pet = await get_pet(user_id)
            return random.choice(WAKE_MESSAGES).format(name=name) + "\n\n" + pet_card(pet), pet_home_kb(True)
        return f"💤 هنوز خوابه... `{fmt_cd(until - now)}` مونده", pet_home_kb(True)
    cd = PET_SLEEP_COOLDOWN - (now - float(pet.get("last_sleep") or 0))
    if cd > 0:
        return f"⏳ خواب بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    await update_pet(user_id, is_sleeping=True, sleep_until=now + PET_SLEEP_DURATION, last_sleep=now)
    name = pet.get("pet_name") or "Pet"
    return random.choice(SLEEP_MESSAGES).format(name=name) + f"\n⏱ {PET_SLEEP_DURATION}ثانیه", pet_home_kb(True)


async def action_gift(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    now = time.time()
    cd = PET_GIFT_COOLDOWN - (now - float(pet.get("last_gift") or 0))
    if cd > 0:
        return f"⏳ هدیه بعد از `{fmt_cd(cd)}`", pet_home_kb(True)
    chance = PET_GIFT_CHANCE_BASE + int(pet.get("level") or 1) * 0.01
    got = random.random() < min(0.5, chance)
    xp = int(pet.get("xp") or 0) + PET_XP_GIFT
    level = int(pet.get("level") or 1)
    level, xp, leveled = _apply_xp(level, xp)
    fields = dict(xp=xp, level=level, last_gift=now, last_interaction=now,
                  interaction_count=int(pet.get("interaction_count") or 0) + 1)
    name = pet.get("pet_name") or "Pet"
    if got:
        coins = random.randint(5, 25)
        await add_meow_coins(user_id, coins)
        fields["gifts_received"] = int(pet.get("gifts_received") or 0) + 1
        await update_pet(user_id, **fields)
        msg = random.choice(GIFT_MESSAGES).format(name=name) + f"\n🪙 +{coins} Meow Coin!"
    else:
        await update_pet(user_id, **fields)
        msg = random.choice(NO_GIFT_MESSAGES).format(name=name)
    if leveled:
        msg += f"\n\n🎉 Level Up → **{level}**!"
    pet = await get_pet(user_id)
    return msg + "\n\n" + pet_card(pet), pet_home_kb(True)


async def action_levelup(user_id):
    pet = await get_pet(user_id)
    if not pet or pet.get("awaiting_name"):
        return "❌ اول Pet بساز!", pet_home_kb(False)
    level = int(pet.get("level") or 1)
    if level >= PET_MAX_LEVEL:
        return f"👑 Pet در حداکثر لول ({PET_MAX_LEVEL}) است!", pet_home_kb(True)
    cost = level * PET_LEVELUP_COIN_PER_LEVEL
    coins = await get_meow_coins(user_id)
    if coins < cost:
        return f"❌ نیاز به `{cost}` کوین داری. موجودی: `{coins}`", pet_home_kb(True)
    ok = await spend_meow_coins(user_id, cost)
    if not ok:
        return "❌ برداشت کوین ناموفق.", pet_home_kb(True)
    await update_pet(user_id, level=level + 1, xp=0)
    pet = await get_pet(user_id)
    name = pet.get("pet_name") or "Pet"
    return f"🎉 {name} به Level **{level + 1}** رسید!\n🪙 -{cost}\n\n{pet_card(pet)}", pet_home_kb(True)


def _apply_xp(level, xp):
    leveled = False
    while level < PET_MAX_LEVEL and xp >= xp_needed(level):
        xp -= xp_needed(level)
        level += 1
        leveled = True
    return level, xp, leveled


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

    # fallback
    pet, text, kb = await get_or_create_flow(user_id)
    return text, kb
