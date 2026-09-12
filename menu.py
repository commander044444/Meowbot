# ==========================================
# 🐱 MeowBot - Main Menu (Start / Inline)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from profile import format_profile


# ------------------------------------------
# Callback data
# ------------------------------------------

CB_MAIN = "menu:main"
CB_PROFILE = "menu:profile"
CB_PET = "pet:home"
CB_ABOUT = "menu:about"
CB_ADD_GROUP = "menu:add_group"
CB_GUIDE = "menu:guide"


# ------------------------------------------
# Texts
# ------------------------------------------

WELCOME_TEXT = (
    "🐱 خوش اومدی به MeowBot!\n"
    "\n"
    "از منوی زیر بخش موردنظرت رو انتخاب کن."
)

ABOUT_TEXT = (
    "🐱 MeowBot\n"
    "\n"
    "این ربات توسط ۱ نفر ساخته و توسعه داده شده است.\n"
    "\n"
    "👨‍💻 سازنده:\n"
    "@commander04\n"
    "\n"
    "📩 برای ارتباط:\n"
    "@commander04"
)

ADD_GROUP_TEXT = (
    "🐱 افزودن MeowBot به گروه\n"
    "\n"
    "می‌خوای MeowBot رو به گروهت اضافه کنی؟\n"
    "\n"
    "1️⃣ وارد گروه موردنظرت شو.\n"
    "2️⃣ بخش افزودن عضو را باز کن.\n"
    "3️⃣ آیدی ربات را جستجو کن:\n"
    "\n"
    "🤖 @meowDarkKnightbot\n"
    "\n"
    "4️⃣ ربات را به گروه اضافه کن.\n"
    "5️⃣ اگر برای فعالیت صحیح نیاز به دسترسی ادمین داشت، "
    "دسترسی‌های لازم را به آن بده.\n"
    "\n"
    "✅ حالا MeowBot آماده استفاده در گروه است!"
)

GUIDE_MENU_TEXT = (
    "📖 راهنمای MeowBot\n"
    "\n"
    "🐱 برای شروع، از منوی اصلی وارد بخش‌های مختلف شو.\n"
    "\n"
    "👤 پروفایل:\n"
    "مشاهده اطلاعات، موجودی و آمار خودت.\n"
    "\n"
    "🐱 Pet Meow:\n"
    "در چت خصوصی ربات یک گربه مجازی بساز، غذا بده، "
    "بازی کن و با کوین ارتقا بده.\n"
    "در گروه با «پیشی» یا اسم گربه وضعیت ببین "
    "و هر ۱ ساعت Point بگیر.\n"
    "\n"
    "🐾 میو:\n"
    "در گروه بنویس «میو». هر ۵ دقیقه یک بار می‌تونی میو کنی "
    "و Meow Point بگیری.\n"
    "\n"
    "🏋️ باشگاه میویی:\n"
    "با Point باشگاهت رو ارتقا بده و قدرتت رو بالا ببر.\n"
    "\n"
    "⚔️ جنگ میویی:\n"
    "روی پیام حریف ریپلای کن و بنویس «جنگ میویی».\n"
    "\n"
    "🧠 حقیقت / 🎯 جرأت / 💡 فکت:\n"
    "در گروه فقط بنویس: حقیقت | جرأت | فکت\n"
    "هر بار یک مورد تصادفی و بدون تکرار برای خودت.\n"
    "\n"
    "🏆 رنکینگ:\n"
    "با فعالیت بیشتر رتبه خودت را در گروه بالا ببر.\n"
    "\n"
    "🪙 انتقال کوین:\n"
    "روی پیام طرف ریپلای کن و بنویس: انتقال میویی ۱۰\n"
    "\n"
    "➕ افزودن به گروه:\n"
    "ربات را به گروه خودت اضافه کن و بازی را شروع کنید."
)


# ------------------------------------------
# Keyboards
# ------------------------------------------

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="👤 پروفایل", callback_data=CB_PROFILE),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🐱 Pet Meow", callback_data=CB_PET),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="ℹ️ درباره ما", callback_data=CB_ABOUT),
        row=2,
    )
    markup.add(
        InlineKeyboardButton(text="➕ افزودن ربات به گروه", callback_data=CB_ADD_GROUP),
        row=3,
    )
    markup.add(
        InlineKeyboardButton(text="📖 آموزش", callback_data=CB_GUIDE),
        row=4,
    )
    return markup


def back_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=CB_MAIN),
        row=1,
    )
    return markup


def is_start_command(text):
    if not text:
        return False
    normalized = str(text).strip().lower()
    if normalized.startswith("/start"):
        return True
    if normalized in {"start", "استارت"}:
        return True
    return False


def is_menu_callback(data):
    if not data:
        return False
    return str(data).startswith("menu:")


def build_profile_text(user):
    user_id = getattr(user, "id", None)
    first_name = getattr(user, "first_name", None) or "Unknown"
    username = getattr(user, "username", None) or ""

    if user_id is None:
        return "❌ اطلاعات کاربر پیدا نشد."

    return format_profile(
        user_id=user_id,
        chat_id=None,
        first_name=first_name,
        username=username,
    )


def get_menu_page(data, user):
    if data == CB_PROFILE:
        return build_profile_text(user), back_keyboard()

    if data == CB_ABOUT:
        return ABOUT_TEXT, back_keyboard()

    if data == CB_ADD_GROUP:
        return ADD_GROUP_TEXT, back_keyboard()

    if data == CB_GUIDE:
        return GUIDE_MENU_TEXT, back_keyboard()

    return WELCOME_TEXT, main_menu_keyboard()
