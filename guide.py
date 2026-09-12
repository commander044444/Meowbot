# 🐱 MeowBot - Guide

GUIDE_COMMANDS = {
    "راهنما", "راهنماا", "راهننا", "کمک", "کمکم",
    "هلپ", "help", "helpp", "guide", "guid"
}


def normalize_guide_text(text):
    if not text:
        return ""

    text = str(text).strip().lower()
    for char in ["\u200c", "\u200d", "\ufeff", " ", "؟", "?", "!", "！", "،", ",", ".", "؛", ";", ":"]:
        text = text.replace(char, "")

    return text


def is_guide_command(text):
    return normalize_guide_text(text) in {
        normalize_guide_text(x) for x in GUIDE_COMMANDS
    }


GUIDE_TEXT = """
🐱🎀 راهنمای MeowBot

🐾 میو
هر ۵ دقیقه یک بار میو کن.
هر میو بین 1 تا 30 Meow Point میده.

🏋️ Gym
Level از 1 تا 100.
هزینه ارتقا = Level فعلی × 5 Point

⚡ قدرت
هرچی Gym بالاتر باشه، قدرتت بیشتره.

⚔️ جنگ میویی
به پیام یک نفر ریپلای کن و بنویس:
جنگ میویی

Gym بیشتر → 80٪ شانس برد
Gym کمتر → 20٪
Level برابر → 50٪

🏆 جایزه جنگ
برنده: +20 Meow Coin
بازنده: +5 Meow Coin

🪙 انتقال Coin
به پیام طرف ریپلای کن:
انتقال میویی 10

یا:
انتقال میو 10
انتقال 10
transfer 10

👤 پروفایل
پروفایل

برای دیدن پروفایل دیگران، روی پیامشان ریپلای کن و بنویس:
پروفایل

🏆 رنکینگ
۳۰ نفر برتر بر اساس Meow Point.
در صورت مساوی بودن، Gym بالاتر اولویت دارد.

🧠 حقیقت / 🎯 جرأت / 💡 فکت
فقط در گروه بنویس (دقیقاً همین کلمات):
حقیقت
جرأت
فکت

هر بار یک مورد تصادفی می‌گیری.
برای هر نفر تکراری نمی‌آید تا همه‌ی لیست تموم بشه.

🐱 Pet Meow
در چت خصوصی ربات یک گربه مجازی بساز،
غذا بده، بازی کن و رابطه‌ات را بالا ببر.

🌸 فصل
هر فصل ۳۰ روز است.
با فصل جدید:
Point، Coin، Gym و Ranking ریست می‌شوند.

🔒 محدودیت
MeowBot فقط در گروه‌های تنظیم‌شده کار می‌کند.

🎯 هدف:
میو کن → Point بگیر → Gym ارتقا بده →
جنگ کن → Coin بگیر → برو بالای رنکینگ 🐱🏆

━━━━━━━━━━━━━━
🐱 MeowBot
ساخته شده توسط @commander04 با 💞 و یکم کد
"""


def get_guide():
    return GUIDE_TEXT.strip()
