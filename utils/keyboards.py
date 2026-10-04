# ==========================================
# 🪟 Glass UI — Inline Keyboards
# ==========================================
# ظاهر شیشه‌ای: دکمه‌های زیاد، چیدمان تمیز، ایموجی

from bale import InlineKeyboardMarkup, InlineKeyboardButton


def glass(*rows):
    """
    ساخت کیبورد شیشه‌ای.
    هر row: لیست از (text, callback_data)
    یا یک دکمه: (text, callback_data)
    """
    kb = InlineKeyboardMarkup()
    for row in rows:
        if not row:
            continue
        # single button passed as tuple
        if isinstance(row, tuple) and len(row) == 2 and isinstance(row[0], str):
            kb.add(InlineKeyboardButton(text=row[0], callback_data=row[1]))
            continue
        buttons = []
        for item in row:
            if isinstance(item, tuple) and len(item) == 2:
                buttons.append(InlineKeyboardButton(text=item[0], callback_data=item[1]))
        if buttons:
            kb.add(*buttons)
    return kb


def glass_url(*rows):
    """دکمه‌های لینک‌دار."""
    kb = InlineKeyboardMarkup()
    for row in rows:
        buttons = []
        for text, url in row:
            buttons.append(InlineKeyboardButton(text=text, url=url))
        if buttons:
            kb.add(*buttons)
    return kb


# ---------- Main Menu ----------
def main_menu_kb():
    return glass(
        [("🐱 میو", "act:meow_info"), ("👤 پروفایل", "menu:profile")],
        [("🐾 Pet", "pet:home"), ("⚔️ Battle", "battle:home")],
        [("🏦 بانک", "bank:home"), ("🛒 فروشگاه", "shop:home")],
        [("🏆 رنکینگ", "menu:rank"), ("📅 فصل", "menu:season")],
        [("🎯 مأموریت", "menu:missions"), ("🏅 دستاورد", "menu:achieve")],
        [("🎮 بازی‌ها", "games:home"), ("🎁 روزانه", "menu:daily")],
        [("📖 راهنما", "menu:guide"), ("ℹ️ درباره", "menu:about")],
        [("🔙 بستن", "menu:close")],
    )


def back_main_kb():
    return glass([("🏠 منوی اصلی", "menu:main")])


def profile_kb():
    return glass(
        [("🔄 بروزرسانی", "menu:profile"), ("🐾 Pet من", "pet:home")],
        [("🏦 بانک", "bank:home"), ("⚔️ Battle", "battle:home")],
        [("🏆 رنکینگ", "menu:rank"), ("🎯 مأموریت", "menu:missions")],
        [("🏠 منوی اصلی", "menu:main")],
    )


# ---------- Pet ----------
def pet_home_kb(has_pet=True, awaiting=False):
    if awaiting:
        return glass(
            [("✏️ نام بفرست (در چت)", "pet:await_hint")],
            [("🏠 منوی اصلی", "menu:main")],
        )
    if not has_pet:
        return glass(
            [("✨ ساخت Pet جدید", "pet:create")],
            [("🏠 منوی اصلی", "menu:main")],
        )
    return glass(
        [("🍖 غذا", "pet:feed"), ("🎾 بازی", "pet:play_menu")],
        [("🫶 نوازش", "pet:pet"), ("💤 خواب", "pet:sleep")],
        [("🎁 هدیه", "pet:gift"), ("📊 وضعیت", "pet:status")],
        [("⬆️ ارتقا لول", "pet:levelup"), ("✏️ تغییر نام", "pet:rename")],
        [("🏠 منوی اصلی", "menu:main")],
    )


def pet_play_kb():
    return glass(
        [("🎾 توپ", "pet:play:ball"), ("🧶 نخ", "pet:play:yarn")],
        [("🔴 لیزر", "pet:play:laser")],
        [("🔙 برگشت به Pet", "pet:home")],
    )


# ---------- Battle ----------
def battle_home_kb():
    return glass(
        [("⚔️ شروع نبرد تصادفی", "battle:random")],
        [("🏋️ باشگاه من", "battle:gym"), ("📊 آمار نبرد", "battle:stats")],
        [("🏠 منوی اصلی", "menu:main")],
    )


def gym_kb():
    return glass(
        [("⬆️ ارتقا باشگاه", "battle:gym_up")],
        [("⚔️ برگشت به Battle", "battle:home")],
        [("🏠 منوی اصلی", "menu:main")],
    )


# ---------- Bank ----------
def bank_home_kb(has_bank=True):
    if not has_bank:
        return glass(
            [("💳 افتتاح حساب", "bank:open")],
            [("🏠 منوی اصلی", "menu:main")],
        )
    return glass(
        [("📥 واریز", "bank:deposit"), ("📤 برداشت", "bank:withdraw")],
        [("💸 انتقال", "bank:transfer"), ("📋 تاریخچه", "bank:history")],
        [("💳 کارت من", "bank:card"), ("🔄 بروزرسانی", "bank:home")],
        [("🏠 منوی اصلی", "menu:main")],
    )


def bank_cancel_kb():
    return glass(
        [("❌ لغو", "bank:home")],
        [("🏠 منوی اصلی", "menu:main")],
    )


# ---------- Shop ----------
def shop_kb(items):
    rows = []
    for it in items[:12]:
        rows.append([(f"🛒 {it.get('name','?')} — {it.get('price',0)}🪙", f"shop:buy:{it['item_id']}")])
    rows.append([("🎒 اینونتوری", "shop:inv"), ("🏠 منوی اصلی", "menu:main")])
    return glass(*rows)


# ---------- Games ----------
def games_kb():
    return glass(
        [("🎲 حدس عدد", "games:guess"), ("❓ کوییز", "games:quiz")],
        [("🐱 کوییز گربه", "games:catquiz"), ("⚡ ری‌اکشن", "games:reaction")],
        [("🏠 منوی اصلی", "menu:main")],
    )


# ---------- Ranking ----------
def rank_kb():
    return glass(
        [("🐾 امتیاز فصل", "rank:points"), ("🪙 سکه", "rank:coins")],
        [("⚔️ برد نبرد", "rank:wins"), ("🏋️ باشگاه", "rank:gym")],
        [("🏠 منوی اصلی", "menu:main")],
    )


# ---------- Owner extras ----------
def owner_nav_kb():
    return glass(
        [("📊 Dashboard", "owner:dashboard"), ("🖥 Status", "owner:status")],
        [("🧪 Tests", "owner:tests"), ("👥 Users", "owner:users")],
        [("💬 Groups", "owner:groups"), ("🛡 Admins", "owner:admins")],
        [("💰 Economy", "owner:economy"), ("📅 Seasons", "owner:seasons")],
        [("💡 Guides", "owner:guides"), ("💾 Backup", "owner:backup")],
        [("📜 Logs", "owner:logs"), ("⚙️ Settings", "owner:settings")],
        [("📢 Broadcast", "owner:broadcast"), ("🔧 Maintenance", "owner:maint")],
        [("🔙 بستن", "owner:close")],
    )
