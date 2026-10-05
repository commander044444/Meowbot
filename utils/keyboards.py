# ==========================================
# 🪟 Glass UI — Inline Keyboards (Bale-compatible)
# ==========================================
# در python-bale-bot:
#   markup.add(InlineKeyboardButton(...), row=1)
# فقط یک دکمه در هر فراخوانی + row عدد طبیعی (>=1)

from bale import InlineKeyboardMarkup, InlineKeyboardButton


def glass(*rows) -> InlineKeyboardMarkup:
    """
    ساخت کیبورد شیشه‌ای سازگار با Bale.

    هر آرگومان یک ردیف است:
      - لیست/تاپل از (text, callback_data)
      - یا یک (text, callback_data) تکی

    مثال:
      glass(
        [("A", "a"), ("B", "b")],   # ردیف 1: دو دکمه
        [("C", "c")],               # ردیف 2: یک دکمه
      )
    """
    kb = InlineKeyboardMarkup()
    row_num = 1

    for row in rows:
        if not row:
            continue

        # تک‌دکمه به صورت tuple: ("text", "data")
        if (
            isinstance(row, tuple)
            and len(row) == 2
            and isinstance(row[0], str)
            and isinstance(row[1], str)
        ):
            items = [row]
        elif isinstance(row, (list, tuple)):
            items = list(row)
        else:
            continue

        for item in items:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            text, data = item[0], item[1]
            if not isinstance(text, str) or not isinstance(data, str):
                continue
            # مهم: فقط یک دکمه + row عددی
            kb.add(
                InlineKeyboardButton(text=text, callback_data=data),
                row=row_num,
            )

        row_num += 1

    return kb


def glass_url(*rows) -> InlineKeyboardMarkup:
    """دکمه‌های لینک‌دار — همان قوانین row."""
    kb = InlineKeyboardMarkup()
    row_num = 1
    for row in rows:
        if not row:
            continue
        if (
            isinstance(row, tuple)
            and len(row) == 2
            and isinstance(row[0], str)
            and isinstance(row[1], str)
        ):
            items = [row]
        else:
            items = list(row)
        for item in items:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            text, url = item[0], item[1]
            kb.add(
                InlineKeyboardButton(text=text, url=url),
                row=row_num,
            )
        row_num += 1
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
        [("🐛 گزارش باگ", "menu:report"), ("🐱 گپ میو", "menu:global_group")],
        [("⚙️ تنظیم گروه", "gset:list")],
        [("🔙 بستن", "menu:close")],
    )


def back_main_kb():
    return glass(
        [("🏠 منوی اصلی", "menu:main")],
    )


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
            [("✏️ نام را در چت بفرست", "pet:await_hint")],
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
        [("⚔️ ورود به صف نبرد", "battle:queue")],
        [("🚪 خروج از صف", "battle:leave_queue")],
        [("🏋️ باشگاه من", "battle:gym"), ("📊 آمار نبرد", "battle:home")],
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
    for it in (items or [])[:12]:
        name = it.get("name") or it.get("item_id") or "?"
        price = it.get("price", 0)
        item_id = it.get("item_id") or "x"
        rows.append([(f"🛒 {name} — {price}🪙", f"shop:buy:{item_id}")])
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


# ---------- Owner ----------
def owner_nav_kb():
    return glass(
        [("📊 Dashboard", "owner:dashboard"), ("🖥 Status", "owner:status")],
        [("🧪 Tests", "owner:tests"), ("📡 Ping", "owner:ping")],
        [("👥 Users", "owner:users"), ("🔍 Find User", "owner:user_find")],
        [("💬 Groups", "owner:groups"), ("🛡 Admins", "owner:admins")],
        [("💰 Economy", "owner:economy"), ("🐾 Pets", "owner:pets")],
        [("⚔️ Battles", "owner:battles"), ("📅 Seasons", "owner:seasons")],
        [("💡 Guides", "owner:guides"), ("📢 Broadcast", "owner:broadcast")],
        [("📜 Logs", "owner:logs"), ("💾 Backup", "owner:backup")],
        [("⚙️ Settings", "owner:settings"), ("🚧 Maintenance", "owner:maint")],
        [("🔙 بستن", "owner:close")],
    )
