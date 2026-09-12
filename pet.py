# ==========================================
# 🐱 MeowBot - Pet Meow System
# ==========================================

import random
import time
import re

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    PET_FEED_COOLDOWN,
    PET_PLAY_COOLDOWN,
    PET_PET_COOLDOWN,
    PET_SLEEP_COOLDOWN,
    PET_GIFT_COOLDOWN,
    PET_FEED_HUNGER,
    PET_PLAY_ENERGY_COST,
    PET_PLAY_RELATIONSHIP,
    PET_PET_RELATIONSHIP,
    PET_SLEEP_ENERGY,
    PET_XP_FEED,
    PET_XP_PLAY,
    PET_XP_PET,
    PET_XP_GIFT,
    PET_XP_PER_LEVEL,
    PET_STAT_MAX,
    PET_STAT_MIN,
    PET_MAX_LEVEL,
    PET_SLEEP_DURATION,
    PET_GIFT_CHANCE_BASE,
)

from database import (
    get_pet,
    create_pet,
    update_pet,
    pet_exists,
    create_user,
    get_user,
    add_meow_coins,
)


# ------------------------------------------
# Callback data
# ------------------------------------------

CB_PET_HOME = "pet:home"
CB_PET_CREATE = "pet:create"
CB_PET_FEED = "pet:feed"
CB_PET_PLAY = "pet:play"
CB_PET_PLAY_BALL = "pet:play:ball"
CB_PET_PLAY_YARN = "pet:play:yarn"
CB_PET_PLAY_LASER = "pet:play:laser"
CB_PET_PET = "pet:pet"
CB_PET_SLEEP = "pet:sleep"
CB_PET_GIFT = "pet:gift"
CB_PET_STATUS = "pet:status"
CB_PET_BACK_MENU = "menu:main"


# ------------------------------------------
# Random messages
# ------------------------------------------

FEED_MESSAGES = [
    "🐱 {name} با ذوق غذاشو خورد! 😋",
    "🐱 {name} حتی ظرف رو هم لیس زد 😂",
    "🐱 {name} گفت: بازم داری؟ 👀",
    "🐱 {name} با خوشحالی میووو کرد! 🍖",
    "🐱 {name} سریع غذا رو تموم کرد 😸",
]

PLAY_MESSAGES = {
    "ball": [
        "🐱 {name} دنبال توپ دوید! 💨",
        "🐱 {name} توپ رو گرفت و ولش نمی‌کنه 😂",
        "🐱 {name} با توپ بازی کرد و خوشحال شد 🎾",
    ],
    "yarn": [
        "🐱 {name} با نخ حسابی سرگرم شد 🧶",
        "🐱 {name} توی نخ پیچیده شد 😂",
        "🐱 {name} نخ رو مثل شکار تعقیب کرد!",
    ],
    "laser": [
        "🐱 {name} دنبال لیزر دوید و دوید! 🔴",
        "🐱 {name} سعی کرد لیزر رو بگیره ولی نشد 😹",
        "🐱 {name} دیوونه لیزر شد!",
    ],
}

PET_MESSAGES = [
    "🐱 {name} خیلی خوشحال شد ❤️",
    "🐱 {name} خودش رو به دستت مالید 🥺",
    "🐱 {name} خرخر می‌کنه... 😸",
    "🐱 {name} چشم‌هاش رو بست و آروم شد ✨",
    "🐱 {name} عاشق نوازش شد!",
]

SLEEP_MESSAGES = [
    "💤 {name} خوابیده... بذار یکم استراحت کنه.",
    "😴 {name} رفت تو حالت خواب عمیق 💤",
    "🐱 {name} یه جا نرم پیدا کرد و خوابید 🌙",
]

WAKE_MESSAGES = [
    "🐱 {name} از خواب بیدار شد! ⚡",
    "🐱 {name} کش و قوس اومد و بیدار شد 😸",
]

GIFT_MESSAGES = [
    "🎁 {name} برات یه هدیه آورد!",
    "🐱 {name} چیزی تو دهنش داره... یه هدیه! 🎁",
    "✨ {name} از جایی یه سورپرایز پیدا کرد!",
]

NO_GIFT_MESSAGES = [
    "🐱 {name} گشت ولی چیزی پیدا نکرد 😅",
    "🐱 {name} این بار دست خالی برگشت.",
    "👀 {name} هنوز داره دنبال هدیه می‌گرده...",
]

CALL_MESSAGES = [
    "🐱 {name}: میووو! 😸\n«اومدم!»",
    "🐱 {name} دوید سمتت! 💨\nمیوو!",
    "🐱 {name}: میو میو! ❤️\nاینجام!",
    "🐱 {name} اومد کنارت نشست. 🐾",
]

RANDOM_BEHAVIORS = [
    "🐱 {name} اومد کنارت نشست.",
    "🐱 {name} دنبال چیزی می‌گرده... 👀",
    "🐱 {name} خوابش گرفته 😴",
    "🐱 {name} با پنجه‌اش بهت زد 😂",
    "🐱 {name} داره خرخر می‌کنه 😸",
    "🐱 {name} یه لحظه بهت نگاه کرد و میو کرد.",
]

LEVEL_UP_MESSAGES = [
    "🎉 {name} به Level {level} رسید!",
    "⭐ تبریک! {name} Level {level} شد!",
]


# ------------------------------------------
# Helpers
# ------------------------------------------

def clamp(value, min_v=PET_STAT_MIN, max_v=PET_STAT_MAX):
    return max(min_v, min(max_v, int(value)))


def xp_needed_for_level(level):
    return max(1, int(level) * PET_XP_PER_LEVEL)


def apply_xp(pet_dict, amount):
    """
    Add XP and handle level ups.
    Returns (updated fields dict, level_up_message or None)
    """
    level = int(pet_dict.get("level") or 1)
    xp = int(pet_dict.get("xp") or 0) + int(amount)
    level_up_msg = None
    name = pet_dict.get("pet_name") or "پیشی"

    while level < PET_MAX_LEVEL and xp >= xp_needed_for_level(level):
        xp -= xp_needed_for_level(level)
        level += 1
        level_up_msg = random.choice(LEVEL_UP_MESSAGES).format(
            name=name, level=level
        )

    return {"level": level, "xp": xp}, level_up_msg


def ensure_awake(pet):
    """
    If sleep timer expired, wake the pet.
    Returns updated pet row (possibly refreshed from DB).
    """
    if not pet:
        return pet

    is_sleeping = int(pet["is_sleeping"] or 0)
    sleep_until = float(pet["sleep_until"] or 0)

    if is_sleeping and sleep_until > 0 and time.time() >= sleep_until:
        return update_pet(
            pet["user_id"],
            is_sleeping=0,
            sleep_until=0,
            energy=clamp(int(pet["energy"] or 0) + PET_SLEEP_ENERGY),
        )
    return pet


def is_pet_sleeping(pet):
    pet = ensure_awake(pet)
    if not pet:
        return False
    return bool(int(pet["is_sleeping"] or 0))


def remaining_cooldown(last_ts, cooldown):
    last_ts = float(last_ts or 0)
    if not last_ts:
        return 0
    left = cooldown - (time.time() - last_ts)
    return max(0, int(left))


def format_seconds(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes} دقیقه و {secs} ثانیه"
    return f"{secs} ثانیه"


def is_private_chat(chat):
    if chat is None:
        return False
    title = getattr(chat, "title", None)
    # Private chats typically have no title
    return not bool(title)


def is_pet_callback(data):
    if not data:
        return False
    return str(data).startswith("pet:")


def normalize_call_text(text):
    if not text:
        return ""
    text = str(text).replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


# ------------------------------------------
# Keyboards
# ------------------------------------------

def no_pet_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🐾 ساخت پیشی", callback_data=CB_PET_CREATE),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=CB_PET_BACK_MENU),
        row=2,
    )
    return markup


def pet_home_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🍖 غذا دادن", callback_data=CB_PET_FEED),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🎾 بازی", callback_data=CB_PET_PLAY),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="❤️ نوازش", callback_data=CB_PET_PET),
        row=2,
    )
    markup.add(
        InlineKeyboardButton(text="😴 خواب", callback_data=CB_PET_SLEEP),
        row=2,
    )
    markup.add(
        InlineKeyboardButton(text="🎁 هدیه", callback_data=CB_PET_GIFT),
        row=3,
    )
    markup.add(
        InlineKeyboardButton(text="📊 وضعیت Pet", callback_data=CB_PET_STATUS),
        row=3,
    )
    markup.add(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=CB_PET_BACK_MENU),
        row=4,
    )
    return markup


def play_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🎾 توپ", callback_data=CB_PET_PLAY_BALL),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🧶 نخ", callback_data=CB_PET_PLAY_YARN),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🔴 لیزر", callback_data=CB_PET_PLAY_LASER),
        row=2,
    )
    markup.add(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=CB_PET_HOME),
        row=3,
    )
    return markup


def back_to_pet_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🔙 بازگشت به Pet", callback_data=CB_PET_HOME),
        row=1,
    )
    return markup


# ------------------------------------------
# Text builders
# ------------------------------------------

def format_pet_home(pet):
    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"
    relationship = int(pet["relationship"] or 0)
    hunger = int(pet["hunger"] or 0)
    energy = int(pet["energy"] or 0)
    level = int(pet["level"] or 1)
    sleeping = is_pet_sleeping(pet)

    status_line = ""
    if sleeping:
        status_line = "\n💤 در حال خواب..."

    return (
        f"🐱 {name}\n"
        f"\n"
        f"❤️ رابطه: {relationship}/{PET_STAT_MAX}\n"
        f"🍖 گرسنگی: {hunger}/{PET_STAT_MAX}\n"
        f"⚡ انرژی: {energy}/{PET_STAT_MAX}\n"
        f"⭐ Level: {level}"
        f"{status_line}"
    )


def format_pet_status(pet):
    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"
    level = int(pet["level"] or 1)
    xp = int(pet["xp"] or 0)
    needed = xp_needed_for_level(level)
    relationship = int(pet["relationship"] or 0)
    hunger = int(pet["hunger"] or 0)
    energy = int(pet["energy"] or 0)
    games = int(pet["games_played"] or 0)
    foods = int(pet["foods_given"] or 0)
    gifts = int(pet["gifts_received"] or 0)
    created = pet["created_at"] or "—"
    # Show only date part if ISO
    if "T" in str(created):
        created = str(created).split("T")[0]

    sleeping = "بله 💤" if is_pet_sleeping(pet) else "خیر"

    return (
        f"📊 وضعیت Pet\n"
        f"\n"
        f"🐱 نام: {name}\n"
        f"⭐ Level: {level}\n"
        f"✨ XP: {xp}/{needed}\n"
        f"❤️ Relationship: {relationship}/{PET_STAT_MAX}\n"
        f"🍖 Hunger: {hunger}/{PET_STAT_MAX}\n"
        f"⚡ Energy: {energy}/{PET_STAT_MAX}\n"
        f"💤 خواب: {sleeping}\n"
        f"\n"
        f"🎮 تعداد بازی‌ها: {games}\n"
        f"🍖 تعداد غذاها: {foods}\n"
        f"🎁 تعداد هدایا: {gifts}\n"
        f"📅 تاریخ ساخت: {created}"
    )


def no_pet_text():
    return (
        "🐱 هنوز پیشی نداری!\n"
        "\n"
        "می‌خوای یک گربه برای خودت داشته باشی؟"
    )


def naming_prompt_text():
    return (
        "🐱 اسم پیشیت رو انتخاب کن!\n"
        "\n"
        "فقط اسم رو بفرست (مثلاً: Milo یا میلو)"
    )


# ------------------------------------------
# Actions
# ------------------------------------------

def get_or_prompt_pet(user_id):
    """
    Returns (text, keyboard, pet_or_None).
    """
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard(), None

    pet = ensure_awake(pet)

    if int(pet["awaiting_name"] or 0) == 1 and not (pet["pet_name"] or "").strip():
        return naming_prompt_text(), back_to_pet_keyboard(), pet

    return format_pet_home(pet), pet_home_keyboard(), pet


def action_create_pet(user_id, first_name="", username=""):
    # Ensure user exists in global users
    if not get_user(user_id):
        create_user(
            user_id=user_id,
            first_name=first_name or "",
            username=username or "",
        )

    if pet_exists(user_id):
        pet = get_pet(user_id)
        pet = ensure_awake(pet)
        return format_pet_home(pet), pet_home_keyboard()

    create_pet(user_id, pet_name="", awaiting_name=1)
    return naming_prompt_text(), back_to_pet_keyboard()


def action_set_name(user_id, name):
    name = (name or "").strip()
    # Limit length and clean
    name = re.sub(r"\s+", " ", name)[:24]
    if not name:
        return "❌ اسم معتبر نیست. دوباره اسم پیشیت رو بفرست.", None

    pet = get_pet(user_id)
    if not pet:
        return "🐱 تو هنوز پیشی نداری! از منوی Pet Meow یکی بساز.", None

    if int(pet["awaiting_name"] or 0) != 1:
        return None, None  # not in naming mode

    update_pet(
        user_id,
        pet_name=name,
        awaiting_name=0,
        last_interaction=time.time(),
    )
    pet = get_pet(user_id)
    text = (
        f"🎉 پیشی با اسم «{name}» ساخته شد!\n"
        f"\n"
        f"{format_pet_home(pet)}"
    )
    return text, pet_home_keyboard()


def action_feed(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()

    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"

    if is_pet_sleeping(pet):
        return (
            f"💤 {name} خوابیده... نمی‌تونی الان بهش غذا بدی.",
            back_to_pet_keyboard(),
        )

    left = remaining_cooldown(pet["last_feed"], PET_FEED_COOLDOWN)
    if left > 0:
        return (
            f"⏳ هنوز وقت غذای بعدی نرسیده!\n"
            f"زمان باقی‌مانده: {format_seconds(left)}",
            back_to_pet_keyboard(),
        )

    hunger = clamp(int(pet["hunger"] or 0) + PET_FEED_HUNGER)
    foods = int(pet["foods_given"] or 0) + 1
    xp_fields, level_msg = apply_xp(dict(pet), PET_XP_FEED)

    update_pet(
        user_id,
        hunger=hunger,
        foods_given=foods,
        last_feed=time.time(),
        last_interaction=time.time(),
        **xp_fields,
    )

    msg = random.choice(FEED_MESSAGES).format(name=name)
    extra = f"\n\n{level_msg}" if level_msg else ""
    text = (
        f"{msg}\n"
        f"\n"
        f"🍖 گرسنگی: {hunger}/{PET_STAT_MAX}"
        f"{extra}"
    )
    return text, back_to_pet_keyboard()


def action_play_menu(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()
    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"
    if is_pet_sleeping(pet):
        return (
            f"💤 {name} خوابیده... بعداً بازی کن.",
            back_to_pet_keyboard(),
        )
    return "🎾 با چی بازی کنیم؟", play_menu_keyboard()


def action_play(user_id, play_type="ball"):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()

    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"

    if is_pet_sleeping(pet):
        return (
            f"💤 {name} خوابیده... نمی‌تونه بازی کنه.",
            back_to_pet_keyboard(),
        )

    left = remaining_cooldown(pet["last_play"], PET_PLAY_COOLDOWN)
    if left > 0:
        return (
            f"⏳ پیشی هنوز خسته‌ست از بازی قبلی!\n"
            f"زمان باقی‌مانده: {format_seconds(left)}",
            back_to_pet_keyboard(),
        )

    energy = int(pet["energy"] or 0)
    if energy < PET_PLAY_ENERGY_COST:
        return (
            f"⚡ انرژی {name} کمه!\n"
            f"بذار یکم بخوابه یا بعداً بازی کن.",
            back_to_pet_keyboard(),
        )

    energy = clamp(energy - PET_PLAY_ENERGY_COST)
    relationship = clamp(
        int(pet["relationship"] or 0) + PET_PLAY_RELATIONSHIP
    )
    games = int(pet["games_played"] or 0) + 1
    xp_fields, level_msg = apply_xp(dict(pet), PET_XP_PLAY)

    update_pet(
        user_id,
        energy=energy,
        relationship=relationship,
        games_played=games,
        last_play=time.time(),
        last_interaction=time.time(),
        **xp_fields,
    )

    msgs = PLAY_MESSAGES.get(play_type) or PLAY_MESSAGES["ball"]
    msg = random.choice(msgs).format(name=name)
    extra = f"\n\n{level_msg}" if level_msg else ""
    text = (
        f"{msg}\n"
        f"\n"
        f"❤️ رابطه: {relationship}/{PET_STAT_MAX}\n"
        f"⚡ انرژی: {energy}/{PET_STAT_MAX}"
        f"{extra}"
    )
    return text, back_to_pet_keyboard()


def action_pet(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()

    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"

    if is_pet_sleeping(pet):
        return (
            f"💤 {name} خوابیده... آروم باش، بیدارش نکن 😴",
            back_to_pet_keyboard(),
        )

    left = remaining_cooldown(pet["last_pet"], PET_PET_COOLDOWN)
    if left > 0:
        return (
            f"⏳ یه کم صبر کن بعد دوباره نوازش کن.\n"
            f"زمان باقی‌مانده: {format_seconds(left)}",
            back_to_pet_keyboard(),
        )

    relationship = clamp(
        int(pet["relationship"] or 0) + PET_PET_RELATIONSHIP
    )
    xp_fields, level_msg = apply_xp(dict(pet), PET_XP_PET)

    update_pet(
        user_id,
        relationship=relationship,
        last_pet=time.time(),
        last_interaction=time.time(),
        **xp_fields,
    )

    msg = random.choice(PET_MESSAGES).format(name=name)
    extra = f"\n\n{level_msg}" if level_msg else ""
    text = (
        f"{msg}\n"
        f"\n"
        f"❤️ رابطه: {relationship}/{PET_STAT_MAX}"
        f"{extra}"
    )
    return text, back_to_pet_keyboard()


def action_sleep(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()

    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"

    if is_pet_sleeping(pet):
        left = max(0, int(float(pet["sleep_until"] or 0) - time.time()))
        return (
            f"💤 {name} هنوز خوابه...\n"
            f"حدود {format_seconds(left)} دیگه بیدار می‌شه.",
            back_to_pet_keyboard(),
        )

    left = remaining_cooldown(pet["last_sleep"], PET_SLEEP_COOLDOWN)
    if left > 0:
        return (
            f"⏳ هنوز وقت خواب بعدی نرسیده!\n"
            f"زمان باقی‌مانده: {format_seconds(left)}",
            back_to_pet_keyboard(),
        )

    energy_now = int(pet["energy"] or 0)
    if energy_now >= PET_STAT_MAX:
        return (
            f"⚡ انرژی {name} پره! نیازی به خواب نیست.",
            back_to_pet_keyboard(),
        )

    sleep_until = time.time() + PET_SLEEP_DURATION
    update_pet(
        user_id,
        is_sleeping=1,
        sleep_until=sleep_until,
        last_sleep=time.time(),
        last_interaction=time.time(),
    )

    msg = random.choice(SLEEP_MESSAGES).format(name=name)
    text = (
        f"{msg}\n"
        f"\n"
        f"⏳ حدود {format_seconds(PET_SLEEP_DURATION)} بعد بیدار می‌شه."
    )
    return text, back_to_pet_keyboard()


def action_gift(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()

    pet = ensure_awake(pet)
    name = pet["pet_name"] or "پیشی"

    if is_pet_sleeping(pet):
        return (
            f"💤 {name} خوابیده و نمی‌تونه هدیه بیاره.",
            back_to_pet_keyboard(),
        )

    left = remaining_cooldown(pet["last_gift"], PET_GIFT_COOLDOWN)
    if left > 0:
        return (
            f"⏳ هنوز وقت هدیه بعدی نرسیده!\n"
            f"زمان باقی‌مانده: {format_seconds(left)}",
            back_to_pet_keyboard(),
        )

    # Chance scales a bit with relationship and level
    relationship = int(pet["relationship"] or 0)
    level = int(pet["level"] or 1)
    chance = PET_GIFT_CHANCE_BASE + (relationship / 1000.0) + (level * 0.01)
    chance = min(0.45, chance)

    got_gift = random.random() < chance
    fields = {
        "last_gift": time.time(),
        "last_interaction": time.time(),
    }

    if got_gift:
        gifts = int(pet["gifts_received"] or 0) + 1
        fields["gifts_received"] = gifts
        xp_fields, level_msg = apply_xp(dict(pet), PET_XP_GIFT)
        fields.update(xp_fields)

        # Reward: small coins
        coin_amount = random.randint(3, 12)
        add_meow_coins(user_id, amount=coin_amount)

        update_pet(user_id, **fields)

        msg = random.choice(GIFT_MESSAGES).format(name=name)
        extra = f"\n\n{level_msg}" if level_msg else ""
        text = (
            f"{msg}\n"
            f"\n"
            f"🪙 +{coin_amount} Meow Coin"
            f"{extra}"
        )
    else:
        update_pet(user_id, **fields)
        msg = random.choice(NO_GIFT_MESSAGES).format(name=name)
        text = msg

    return text, back_to_pet_keyboard()


def action_status(user_id):
    pet = get_pet(user_id)
    if not pet:
        return no_pet_text(), no_pet_keyboard()
    pet = ensure_awake(pet)
    return format_pet_status(pet), back_to_pet_keyboard()


# ------------------------------------------
# Call / random behavior
# ------------------------------------------

def try_handle_pet_name_input(user_id, text):
    """
    If user is awaiting pet name, set it.
    Returns (text, keyboard) or (None, None) if not applicable.
    """
    pet = get_pet(user_id)
    if not pet:
        return None, None
    if int(pet["awaiting_name"] or 0) != 1:
        return None, None
    return action_set_name(user_id, text)


def try_call_pet(user_id, text, in_group=False):
    """
    Handle calling pet by name or generic words.
    Returns response text or None.
    """
    pet = get_pet(user_id)
    if not pet:
        # Only respond to explicit generic call in PV
        normalized = normalize_call_text(text)
        if not in_group and normalized in {
            "پیشی",
            "پیشی بیا",
            "پیشی جان",
            "pishi",
            "pishi bia",
        }:
            return "🐱 تو هنوز پیشی نداری! از منوی Pet Meow یکی بساز."
        return None

    pet = ensure_awake(pet)
    name = (pet["pet_name"] or "").strip()
    if not name:
        return None

    normalized = normalize_call_text(text)
    name_l = name.lower()

    triggers = {
        "پیشی",
        "پیشی بیا",
        "پیشی جان",
        "pishi",
        "pishi bia",
        name_l,
        f"{name_l} بیا",
        f"{name_l} جان",
    }

    if normalized not in triggers:
        return None

    if is_pet_sleeping(pet):
        if in_group:
            return f"💤 {name} خوابیده..."
        return f"💤 {name} خوابیده... بذار استراحت کنه."

    update_pet(user_id, last_interaction=time.time())
    return random.choice(CALL_MESSAGES).format(name=name)


def try_random_behavior(user_id, in_group=False):
    """
    Rare random behavior in PV only. Max once per ~15 minutes.
    """
    if in_group:
        return None

    pet = get_pet(user_id)
    if not pet:
        return None

    pet = ensure_awake(pet)
    name = (pet["pet_name"] or "").strip()
    if not name or int(pet["awaiting_name"] or 0) == 1:
        return None

    if is_pet_sleeping(pet):
        return None

    last_random = float(pet["last_random"] or 0)
    if time.time() - last_random < 15 * 60:
        return None

    # ~8% chance on a message
    if random.random() > 0.08:
        return None

    update_pet(user_id, last_random=time.time())
    return random.choice(RANDOM_BEHAVIORS).format(name=name)


# ------------------------------------------
# Callback router
# ------------------------------------------

def handle_pet_callback(data, user_id, first_name="", username=""):
    """
    Process pet:* callbacks.
    Returns (text, keyboard).
    """
    data = str(data or "")

    if data == CB_PET_HOME:
        return get_or_prompt_pet(user_id)[:2]

    if data == CB_PET_CREATE:
        return action_create_pet(user_id, first_name, username)

    if data == CB_PET_FEED:
        return action_feed(user_id)

    if data == CB_PET_PLAY:
        return action_play_menu(user_id)

    if data == CB_PET_PLAY_BALL:
        return action_play(user_id, "ball")

    if data == CB_PET_PLAY_YARN:
        return action_play(user_id, "yarn")

    if data == CB_PET_PLAY_LASER:
        return action_play(user_id, "laser")

    if data == CB_PET_PET:
        return action_pet(user_id)

    if data == CB_PET_SLEEP:
        return action_sleep(user_id)

    if data == CB_PET_GIFT:
        return action_gift(user_id)

    if data == CB_PET_STATUS:
        return action_status(user_id)

    # Fallback
    return get_or_prompt_pet(user_id)[:2]
