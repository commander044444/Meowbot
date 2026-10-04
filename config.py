# ==========================================
# 🐱 MeowBot - Configuration (Production)
# ==========================================
# مقادیر واقعی پروژه حفظ شده‌اند.
# برای Railway: DATABASE_URL از Environment خوانده می‌شود.
# ==========================================

import os

# ------------------------------------------
# Bot Token (Bale)
# ------------------------------------------
BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "1136047890:50pbkHl72PKOZ-TOgO0k27_mjea_GNEgDms",
)

# ------------------------------------------
# Owner / Admin
# ------------------------------------------
OWNER_ID = int(os.getenv("OWNER_ID", "1967315238"))

# Admin IDs اضافی (غیر از Owner) — لیست واقعی فعلی
# Owner همیشه بالاترین دسترسی را دارد
ADMINS = [
    # می‌توانید IDهای ادمین را اینجا اضافه کنید
]

# ------------------------------------------
# Database — PostgreSQL (Railway)
# ------------------------------------------
# روی Railway متغیر DATABASE_URL به‌صورت خودکار ست می‌شود.
# اگر local اجرا می‌کنید، مقدار را اینجا یا در .env بگذارید.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/meowbot",
)

# Connection pool
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))

# ------------------------------------------
# Allowed Groups (legacy — اکنون همه گروه‌ها فعال‌اند)
# ------------------------------------------
ALLOWED_GROUP = [
    "@testcmbot",
    "@lilililillilililililililili",
    "@MeowKonan",
    "@possibly",
]

# ------------------------------------------
# Bot Info
# ------------------------------------------
BOT_NAME = "MeowBot"
BOT_VERSION = "2.0.0"

# ------------------------------------------
# Game Settings
# ------------------------------------------
MEOW_COOLDOWN = 5 * 60          # 5 دقیقه
BATTLE_COOLDOWN = 600           # 10 دقیقه
SEASON_DAYS = 15
MAX_GYM_LEVEL = 100
RANKING_LIMIT = 30

# ------------------------------------------
# 🐱 Pet Meow Settings
# ------------------------------------------
PET_FEED_COOLDOWN = 60
PET_PLAY_COOLDOWN = 90
PET_PET_COOLDOWN = 30
PET_SLEEP_COOLDOWN = 180
PET_GIFT_COOLDOWN = 300

PET_FEED_HUNGER = 20
PET_PLAY_ENERGY_COST = 15
PET_PLAY_RELATIONSHIP = 8
PET_PET_RELATIONSHIP = 5
PET_SLEEP_ENERGY = 40

PET_XP_FEED = 5
PET_XP_PLAY = 8
PET_XP_PET = 3
PET_XP_GIFT = 10
PET_XP_PER_LEVEL = 25
PET_XP_GROWTH = 0.4

PET_STAT_MAX = 100
PET_STAT_MIN = 0
PET_MAX_LEVEL = 50
PET_SLEEP_DURATION = 120
PET_GIFT_CHANCE_BASE = 0.12

PET_POINT_COOLDOWN = 3600
PET_POINT_BASE = 10
PET_POINT_PER_LEVEL = 10
PET_LEVELUP_COIN_PER_LEVEL = 20

# ------------------------------------------
# Economy
# ------------------------------------------
DAILY_REWARD_BASE = 50
DAILY_STREAK_BONUS = 10
TRANSFER_MIN = 1
TRANSFER_MAX = 100_000
BANK_INTEREST_RATE = 0.02       # 2% روزانه (اختیاری)

# ------------------------------------------
# Battle
# ------------------------------------------
BATTLE_WIN_REWARD = 20
BATTLE_LOSE_REWARD = 5
BATTLE_ROUNDS = 3

# ------------------------------------------
# Auto Guide Settings (default)
# ------------------------------------------
GUIDE_DEFAULT_ENABLED = True
GUIDE_DEFAULT_INTERVAL = 3600   # 1 ساعت
GUIDE_INTERVALS = {
    15: 15 * 60,
    30: 30 * 60,
    60: 60 * 60,
    120: 120 * 60,
    180: 180 * 60,
    360: 360 * 60,
    0: 0,  # خاموش
}

# ------------------------------------------
# Interaction Settings (default)
# ------------------------------------------
INTERACTION_DEFAULT = True

# ------------------------------------------
# Backup Settings
# ------------------------------------------
BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/meowbot_backups")
BACKUP_KEEP = 10

# ------------------------------------------
# Cooldowns / Rate limits
# ------------------------------------------
RATE_LIMIT_MESSAGES = 20        # پیام در دقیقه per user
ANTI_SPAM_WINDOW = 60

# ------------------------------------------
# Cute Emojis
# ------------------------------------------
MEOW_EMOJIS = ["🐱", "🎀", "🌸", "✨", "🩷"]

# ------------------------------------------
# Timezone
# ------------------------------------------
TIMEZONE = "Asia/Tehran"
