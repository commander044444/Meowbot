# ==========================================
# 🐱 MeowBot - Configuration
# ==========================================


# ------------------------------------------
# Bot Token
# ------------------------------------------

BOT_TOKEN = "1136047890:50pbkHl72PKOZ-TOgO0k27_mjea_GNEgDms"


# ------------------------------------------
# Owner / Admin
# ------------------------------------------

# آیدی عددی مالک ربات
OWNER_ID = 1967315238


# ------------------------------------------
# Allowed Groups
# ------------------------------------------

# گپ‌هایی که MeowBot اجازه فعالیت داخل آن‌ها را دارد
ALLOWED_GROUP = [
    "@testcmbot",
    "@lilililillilililililililili",
    "@MeowKonan",
    "@possibly"
]


# ------------------------------------------
# Game Settings
# ------------------------------------------

# هر ۵ دقیقه یک بار امکان میو کردن
MEOW_COOLDOWN = 5 * 60

# Cooldown جنگ میویی (ثانیه) — پیش‌فرض ۱۰ دقیقه
BATTLE_COOLDOWN = 600

# مدت هر فصل
SEASON_DAYS = 15

# حداکثر سطح باشگاه میویی
MAX_GYM_LEVEL = 100

# تعداد نفرات نمایش داده‌شده در رنکینگ
RANKING_LIMIT = 30


# ------------------------------------------
# 🐱 Pet Meow Settings
# ------------------------------------------

# Cooldownها (ثانیه)
PET_FEED_COOLDOWN = 60
PET_PLAY_COOLDOWN = 90
PET_PET_COOLDOWN = 30
PET_SLEEP_COOLDOWN = 180
PET_GIFT_COOLDOWN = 300

# مقدار تغییر آمار
PET_FEED_HUNGER = 20
PET_PLAY_ENERGY_COST = 15
PET_PLAY_RELATIONSHIP = 8
PET_PET_RELATIONSHIP = 5
PET_SLEEP_ENERGY = 40

# XP (هرچی لول بالاتر، XP لازم بیشتر رشد می‌کنه)
PET_XP_FEED = 5
PET_XP_PLAY = 8
PET_XP_PET = 3
PET_XP_GIFT = 10
PET_XP_PER_LEVEL = 25
# ضریب رشد سختی لول‌آپ (بالاتر = سخت‌تر در لول‌های بالا)
PET_XP_GROWTH = 0.4

# حدود
PET_STAT_MAX = 100
PET_STAT_MIN = 0
PET_MAX_LEVEL = 50

# خواب پیش‌فرض (ثانیه)
PET_SLEEP_DURATION = 120

# شانس هدیه تصادفی هنگام تعامل (۰ تا ۱)
PET_GIFT_CHANCE_BASE = 0.12

# امتیاز ساعتی پیشی در گروه (ثانیه cooldown)
# مقدار امتیاز = PET_POINT_BASE + level * PET_POINT_PER_LEVEL
# لول ۱ → ۲۰ | لول ۲ → ۳۰ | لول ۳ → ۴۰ ...
PET_POINT_COOLDOWN = 3600
PET_POINT_BASE = 10
PET_POINT_PER_LEVEL = 10

# هزینه ارتقا با Meow Coin: level فعلی × این عدد
# لول ۱→۲ = ۲۰ کوین | لول ۲→۳ = ۴۰ کوین | ...
PET_LEVELUP_COIN_PER_LEVEL = 20


# ------------------------------------------
# Database
# ------------------------------------------

DATABASE_NAME = "meow.db"


# ------------------------------------------
# Bot Info
# ------------------------------------------

BOT_NAME = "MeowBot"


# ------------------------------------------
# Cute Emojis 🎀
# ------------------------------------------

MEOW_EMOJIS = [
    "🐱",
    "🎀",
    "🌸",
    "✨",
    "🩷",
]
