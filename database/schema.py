# ==========================================
# MeowBot PostgreSQL Schema
# ==========================================
# تمام جداول موجود + جداول جدید سیستم‌های ارتقا‌یافته
# ==========================================

from .pool import execute, get_pool
import logging

logger = logging.getLogger("meowbot.db")

SCHEMA_SQL = """
-- ========================================
-- Users (Global Account)
-- ========================================
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT PRIMARY KEY,
    first_name      TEXT DEFAULT '',
    username        TEXT DEFAULT '',
    meow_points     INTEGER DEFAULT 0,          -- season ranking points
    meow_coins      INTEGER DEFAULT 0,          -- permanent currency
    gym_level       INTEGER DEFAULT 1,
    xp              INTEGER DEFAULT 0,          -- permanent XP
    level           INTEGER DEFAULT 1,          -- permanent level
    total_meows     INTEGER DEFAULT 0,
    total_battles   INTEGER DEFAULT 0,
    total_wins      INTEGER DEFAULT 0,
    total_losses    INTEGER DEFAULT 0,
    last_meow       DOUBLE PRECISION DEFAULT 0,
    last_battle     DOUBLE PRECISION DEFAULT 0,
    last_daily      TEXT DEFAULT NULL,
    daily_streak    INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Groups
-- ========================================
CREATE TABLE IF NOT EXISTS groups (
    chat_id         TEXT PRIMARY KEY,
    title           TEXT DEFAULT '',
    username        TEXT DEFAULT '',
    interaction_on  BOOLEAN DEFAULT TRUE,
    guide_enabled   BOOLEAN DEFAULT TRUE,
    guide_interval  INTEGER DEFAULT 9000,
    meow_enabled    BOOLEAN DEFAULT TRUE,
    guide_last_sent DOUBLE PRECISION DEFAULT 0,
    guide_category  TEXT DEFAULT 'all',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS group_users (
    user_id     BIGINT NOT NULL,
    chat_id     TEXT NOT NULL,
    joined_at   TIMESTAMPTZ DEFAULT NOW(),
    last_seen   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, chat_id)
);

-- ========================================
-- Pets
-- ========================================
CREATE TABLE IF NOT EXISTS pets (
    user_id             BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    pet_name            TEXT DEFAULT '',
    level               INTEGER DEFAULT 1,
    xp                  INTEGER DEFAULT 0,
    relationship        INTEGER DEFAULT 50,
    hunger              INTEGER DEFAULT 80,
    energy              INTEGER DEFAULT 80,
    mood                INTEGER DEFAULT 70,
    health              INTEGER DEFAULT 100,
    is_sleeping         BOOLEAN DEFAULT FALSE,
    sleep_until         DOUBLE PRECISION DEFAULT 0,
    games_played        INTEGER DEFAULT 0,
    foods_given         INTEGER DEFAULT 0,
    gifts_received      INTEGER DEFAULT 0,
    interaction_count   INTEGER DEFAULT 0,
    last_feed           DOUBLE PRECISION DEFAULT 0,
    last_play           DOUBLE PRECISION DEFAULT 0,
    last_pet            DOUBLE PRECISION DEFAULT 0,
    last_sleep          DOUBLE PRECISION DEFAULT 0,
    last_gift           DOUBLE PRECISION DEFAULT 0,
    last_interaction    DOUBLE PRECISION DEFAULT 0,
    last_random         DOUBLE PRECISION DEFAULT 0,
    awaiting_name       BOOLEAN DEFAULT TRUE,
    last_point_claim    DOUBLE PRECISION DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Seasons (Season Ranking جدا از داده‌های دائمی)
-- ========================================
CREATE TABLE IF NOT EXISTS seasons (
    id              SERIAL PRIMARY KEY,
    season_number   INTEGER NOT NULL UNIQUE,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_results (
    id              SERIAL PRIMARY KEY,
    season_id       INTEGER NOT NULL REFERENCES seasons(id),
    user_id         BIGINT NOT NULL,
    chat_id         TEXT,
    meow_points     INTEGER DEFAULT 0,
    final_rank      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_meow_stats (
    user_id         BIGINT NOT NULL,
    day_date        DATE NOT NULL,
    meow_count      INTEGER DEFAULT 0,
    points_earned   INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, day_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_meow_date
    ON daily_meow_stats (day_date, points_earned DESC);

-- ========================================
-- Bank
-- ========================================
CREATE TABLE IF NOT EXISTS banks (
    user_id         BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    card_number     TEXT UNIQUE NOT NULL,
    balance         INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_banks_card ON banks (card_number);

CREATE TABLE IF NOT EXISTS bank_pending (
    user_id     BIGINT PRIMARY KEY,
    action      TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    type            TEXT NOT NULL,          -- deposit/withdraw/transfer/reward/shop/battle
    amount          INTEGER NOT NULL,
    balance_after   INTEGER,
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions (user_id, created_at DESC);

-- ========================================
-- Content History (Anti-Repetition)
-- ========================================
CREATE TABLE IF NOT EXISTS content_history (
    user_id         BIGINT NOT NULL,
    content_type    TEXT NOT NULL,
    item_index      INTEGER NOT NULL,
    seen_at         TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, content_type, item_index)
);

CREATE INDEX IF NOT EXISTS idx_content_history_user_type
    ON content_history (user_id, content_type);

-- Guide history per group (anti-repetition for Auto Guide)
CREATE TABLE IF NOT EXISTS guide_history (
    chat_id         TEXT NOT NULL,
    guide_key       TEXT NOT NULL,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chat_id, guide_key)
);

-- ========================================
-- Inventory
-- ========================================
CREATE TABLE IF NOT EXISTS inventory (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_id         TEXT NOT NULL,
    item_type       TEXT NOT NULL,          -- food/toy/gift/boost/rare/epic/legendary
    quantity        INTEGER DEFAULT 1,
    meta            JSONB DEFAULT '{}',
    acquired_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, item_id)
);

-- ========================================
-- Shop Items
-- ========================================
CREATE TABLE IF NOT EXISTS shop_items (
    item_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    price           INTEGER NOT NULL,
    stock           INTEGER DEFAULT -1,     -- -1 = unlimited
    rarity          TEXT DEFAULT 'common',
    item_type       TEXT NOT NULL,
    effect          JSONB DEFAULT '{}',
    active          BOOLEAN DEFAULT TRUE
);

-- ========================================
-- Achievements
-- ========================================
CREATE TABLE IF NOT EXISTS achievements (
    achievement_id  TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    category        TEXT DEFAULT 'general',
    icon            TEXT DEFAULT '🏆',
    reward_coins    INTEGER DEFAULT 0,
    reward_xp       INTEGER DEFAULT 0,
    condition_type  TEXT NOT NULL,          -- meows/battles/wins/coins/pet_level/...
    condition_value INTEGER NOT NULL,
    secret          BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id         BIGINT NOT NULL,
    achievement_id  TEXT NOT NULL REFERENCES achievements(achievement_id),
    progress        INTEGER DEFAULT 0,
    completed       BOOLEAN DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    PRIMARY KEY (user_id, achievement_id)
);

-- ========================================
-- Missions
-- ========================================
CREATE TABLE IF NOT EXISTS missions (
    mission_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    mission_type    TEXT NOT NULL,          -- daily/weekly
    condition_type  TEXT NOT NULL,
    condition_value INTEGER NOT NULL,
    reward_coins    INTEGER DEFAULT 0,
    reward_xp       INTEGER DEFAULT 0,
    reward_item     TEXT,
    active          BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS user_missions (
    user_id         BIGINT NOT NULL,
    mission_id      TEXT NOT NULL REFERENCES missions(mission_id),
    progress        INTEGER DEFAULT 0,
    completed       BOOLEAN DEFAULT FALSE,
    claimed         BOOLEAN DEFAULT FALSE,
    period_key      TEXT NOT NULL,          -- YYYY-MM-DD or YYYY-WW
    PRIMARY KEY (user_id, mission_id, period_key)
);

-- ========================================
-- Events
-- ========================================
CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    start_at        TIMESTAMPTZ NOT NULL,
    end_at          TIMESTAMPTZ NOT NULL,
    bonus_xp        NUMERIC(4,2) DEFAULT 1.0,
    bonus_coin      NUMERIC(4,2) DEFAULT 1.0,
    special_item    TEXT,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Admin System
-- ========================================
CREATE TABLE IF NOT EXISTS admins (
    user_id         BIGINT PRIMARY KEY,
    role            TEXT NOT NULL DEFAULT 'ADMIN',  -- OWNER/SUPER_ADMIN/ADMIN/MODERATOR
    permissions     JSONB DEFAULT '[]',
    enabled         BOOLEAN DEFAULT TRUE,
    added_by        BIGINT,
    note            TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Audit Logs
-- ========================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              SERIAL PRIMARY KEY,
    actor_id        BIGINT NOT NULL,
    action          TEXT NOT NULL,
    target          TEXT,
    details         JSONB DEFAULT '{}',
    result          TEXT DEFAULT 'ok',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action, created_at DESC);

-- ========================================
-- Backups metadata
-- ========================================
CREATE TABLE IF NOT EXISTS backups (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    size_bytes      BIGINT DEFAULT 0,
    created_by      BIGINT,
    status          TEXT DEFAULT 'ok',
    note            TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Bot Settings (key-value)
-- ========================================
CREATE TABLE IF NOT EXISTS bot_settings (
    key             TEXT PRIMARY KEY,
    value           JSONB NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
"""


async def init_schema():
    """Create all tables if they don't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
        # Ensure Owner is in admins table
        from config import OWNER_ID
        await conn.execute(
            """
            INSERT INTO admins (user_id, role, permissions, enabled, note)
            VALUES ($1, 'OWNER', '["*"]'::jsonb, TRUE, 'System Owner')
            ON CONFLICT (user_id) DO UPDATE
            SET role = 'OWNER', permissions = '["*"]'::jsonb, enabled = TRUE
            """,
            OWNER_ID,
        )
    # Safe migrations for existing DBs
    try:
        await conn.execute(
            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS meow_enabled BOOLEAN DEFAULT TRUE"
        )
        await conn.execute(
            "ALTER TABLE groups ALTER COLUMN guide_interval SET DEFAULT 9000"
        )
    except Exception as e:
        logger.warning(f"groups migration: {e}")
    logger.info("✅ Database schema initialized")
