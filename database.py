# ==========================================
# 🐱 MeowBot - Database (Global Account Architecture)
# ==========================================

import sqlite3
from datetime import datetime

from config import DATABASE_NAME


# ==========================================
# Connection
# ==========================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


# ==========================================
# Database Initialization + Safe Migration
# ==========================================

def init_database():
    """
    Initialize schema and safely migrate from
    Group-Based (user_id + chat_id) to Global Account (user_id only).
    Existing data is preserved. No destructive deletes without backup.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # ------------------------------------------------------------------
    # 1. Create new tables if they do not exist
    # ------------------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,

            first_name TEXT DEFAULT '',
            username TEXT DEFAULT '',

            meow_points INTEGER DEFAULT 0,
            meow_coins INTEGER DEFAULT 0,

            gym_level INTEGER DEFAULT 1,

            last_meow REAL DEFAULT 0,
            last_battle REAL DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    # Safe add last_battle column if missing (for existing databases)
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [c["name"] for c in cursor.fetchall()]
    if "last_battle" not in existing_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN last_battle REAL DEFAULT 0"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id TEXT PRIMARY KEY,

            title TEXT DEFAULT '',
            username TEXT DEFAULT '',

            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_users (
            user_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,

            joined_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,

            PRIMARY KEY (user_id, chat_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            season_number INTEGER NOT NULL,

            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,

            active INTEGER DEFAULT 1
        )
    """)

    # ------------------------------------------------------------------
    # Pets table (Pet Meow system)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            user_id INTEGER PRIMARY KEY,

            pet_name TEXT DEFAULT '',
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            relationship INTEGER DEFAULT 50,
            hunger INTEGER DEFAULT 80,
            energy INTEGER DEFAULT 80,

            is_sleeping INTEGER DEFAULT 0,
            sleep_until REAL DEFAULT 0,

            games_played INTEGER DEFAULT 0,
            foods_given INTEGER DEFAULT 0,
            gifts_received INTEGER DEFAULT 0,

            last_feed REAL DEFAULT 0,
            last_play REAL DEFAULT 0,
            last_pet REAL DEFAULT 0,
            last_sleep REAL DEFAULT 0,
            last_gift REAL DEFAULT 0,
            last_interaction REAL DEFAULT 0,
            last_random REAL DEFAULT 0,

            awaiting_name INTEGER DEFAULT 0,

            last_point_claim REAL DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    # Safe add last_point_claim for existing databases
    cursor.execute("PRAGMA table_info(pets)")
    pet_columns = [c["name"] for c in cursor.fetchall()]
    if "last_point_claim" not in pet_columns:
        cursor.execute(
            "ALTER TABLE pets ADD COLUMN last_point_claim REAL DEFAULT 0"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            season_id INTEGER NOT NULL,

            user_id INTEGER NOT NULL,
            chat_id TEXT,

            meow_points INTEGER DEFAULT 0,

            final_rank INTEGER DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    # ------------------------------------------------------------------
    # Daily meow stats (for season daily top meowers)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_meow_stats (
            user_id INTEGER NOT NULL,
            day_date TEXT NOT NULL,
            meow_count INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, day_date)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_meow_date
        ON daily_meow_stats (day_date, points_earned DESC)
    """)

    # ------------------------------------------------------------------
    # Content history (Truth / Dare / Fact) — per-user seen indices
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_history (
            user_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            seen_at TEXT NOT NULL,
            PRIMARY KEY (user_id, content_type, item_index)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_content_history_user_type
        ON content_history (user_id, content_type)
    """)

    # ------------------------------------------------------------------
    # Meow Bank
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            user_id INTEGER PRIMARY KEY,
            card_number TEXT NOT NULL UNIQUE,
            balance INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_banks_card
        ON banks (card_number)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_pending (
            user_id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()

    # ------------------------------------------------------------------
    # 2. Detect old schema and migrate if needed
    # ------------------------------------------------------------------

    # Check if old composite primary key table still exists
    # (SQLite stores the original CREATE in sqlite_master)
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name='users'
    """)
    row = cursor.fetchone()
    users_sql = (row["sql"] or "") if row else ""

    needs_migration = False

    # Old schema has "PRIMARY KEY (user_id, chat_id)" or has a chat_id column
    # New schema has "user_id INTEGER PRIMARY KEY" and no chat_id in users
    if "chat_id" in users_sql.lower() and "PRIMARY KEY (user_id, chat_id)" in users_sql.replace(" ", ""):
        needs_migration = True
    else:
        # Also check columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [c["name"] for c in cursor.fetchall()]
        if "chat_id" in columns:
            needs_migration = True

    if needs_migration:
        _migrate_to_global_accounts(connection, cursor)

    connection.commit()
    connection.close()


def _migrate_to_global_accounts(connection, cursor):
    """
    Safe migration from old group-based users table to global users + group_users.
    Strategy for economic values when a user appears in multiple groups:
    - Take MAX(meow_points), MAX(meow_coins), MAX(gym_level)
    - Take MAX(last_meow) (most recent)
    - Prefer first_name / username from the record that has the highest meow_points
    Never SUM values (avoids accidental multiplication of balances).
    """
    print("🔄 Starting safe migration to Global Account architecture...")

    # Rename old table
    cursor.execute("ALTER TABLE users RENAME TO users_old")

    # Create clean new users table
    cursor.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,

            first_name TEXT DEFAULT '',
            username TEXT DEFAULT '',

            meow_points INTEGER DEFAULT 0,
            meow_coins INTEGER DEFAULT 0,

            gym_level INTEGER DEFAULT 1,

            last_meow REAL DEFAULT 0,
            last_battle REAL DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    # Ensure group_users and groups exist (already created above, but safe)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            username TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_users (
            user_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            PRIMARY KEY (user_id, chat_id)
        )
    """)

    # Fetch all old rows
    cursor.execute("SELECT * FROM users_old")
    old_rows = cursor.fetchall()

    # Group by user_id
    from collections import defaultdict
    by_user = defaultdict(list)
    for row in old_rows:
        by_user[int(row["user_id"])].append(row)

    now = datetime.now().isoformat()

    for user_id, records in by_user.items():
        # Choose best economic values with MAX (never SUM)
        best_points = max(int(r["meow_points"] or 0) for r in records)
        best_coins = max(int(r["meow_coins"] or 0) for r in records)
        best_gym = max(int(r["gym_level"] or 1) for r in records)
        best_last_meow = max(float(r["last_meow"] or 0) for r in records)

        # Prefer name from the record with highest points
        best_record = max(records, key=lambda r: int(r["meow_points"] or 0))
        first_name = best_record["first_name"] or ""
        username = best_record["username"] or ""

        # Earliest created_at
        created_ats = [r["created_at"] for r in records if r["created_at"]]
        created_at = min(created_ats) if created_ats else now

        cursor.execute("""
            INSERT OR REPLACE INTO users (
                user_id, first_name, username,
                meow_points, meow_coins, gym_level,
                last_meow, last_battle, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            first_name,
            username,
            best_points,
            best_coins,
            best_gym,
            best_last_meow,
            0,
            created_at
        ))

        # Create group memberships
        for r in records:
            chat_id = str(r["chat_id"])
            joined = r["created_at"] or now
            last_seen = now

            # Register group if missing
            cursor.execute("""
                INSERT OR IGNORE INTO groups (
                    chat_id, title, username, created_at, last_seen
                ) VALUES (?, '', '', ?, ?)
            """, (chat_id, joined, last_seen))

            cursor.execute("""
                INSERT OR IGNORE INTO group_users (
                    user_id, chat_id, joined_at, last_seen
                ) VALUES (?, ?, ?, ?)
            """, (user_id, chat_id, joined, last_seen))

            # Also update last_seen
            cursor.execute("""
                UPDATE group_users
                SET last_seen = ?
                WHERE user_id = ? AND chat_id = ?
            """, (last_seen, user_id, chat_id))

    # Keep old table as backup (users_old). Do NOT drop it.
    # Admin can drop it later after verification.
    print(f"✅ Migration finished. Migrated {len(by_user)} unique users from {len(old_rows)} old rows.")
    print("ℹ️  Old table kept as 'users_old' for safety.")


# ==========================================
# Group Management
# ==========================================

def register_group(chat_id, title="", username=""):
    """
    ثبت یا بروزرسانی یک گروه.
    فقط برای گروه‌ها (نه private chat).
    """
    if chat_id is None:
        return

    chat_id = str(chat_id)
    now = datetime.now().isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO groups (
            chat_id, title, username, created_at, last_seen
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(chat_id)
        DO UPDATE SET
            title = excluded.title,
            username = excluded.username,
            last_seen = excluded.last_seen
    """, (
        chat_id,
        title or "",
        username or "",
        now,
        now
    ))

    connection.commit()
    connection.close()


def get_all_groups():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM groups
        ORDER BY created_at ASC
    """)
    groups = cursor.fetchall()
    connection.close()
    return groups


def get_group(chat_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM groups WHERE chat_id = ?
    """, (str(chat_id),))
    group = cursor.fetchone()
    connection.close()
    return group


def remove_group(chat_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        DELETE FROM groups WHERE chat_id = ?
    """, (str(chat_id),))
    deleted = cursor.rowcount > 0
    connection.commit()
    connection.close()
    return deleted


def get_group_count():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM groups")
    result = cursor.fetchone()
    connection.close()
    return int(result["count"])


# ==========================================
# Group Membership (group_users)
# ==========================================

def ensure_group_membership(user_id, chat_id):
    """
    Ensure the user is recorded as member of the group.
    Does NOT touch economic data.
    """
    if chat_id is None:
        return

    user_id = int(user_id)
    chat_id = str(chat_id)
    now = datetime.now().isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO group_users (user_id, chat_id, joined_at, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id)
        DO UPDATE SET last_seen = excluded.last_seen
    """, (user_id, chat_id, now, now))

    connection.commit()
    connection.close()


def get_user_groups(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT gu.*, g.title, g.username
        FROM group_users gu
        LEFT JOIN groups g ON g.chat_id = gu.chat_id
        WHERE gu.user_id = ?
        ORDER BY gu.last_seen DESC
    """, (int(user_id),))
    rows = cursor.fetchall()
    connection.close()
    return rows


# ==========================================
# User Management (Global)
# ==========================================

def create_user(user_id, chat_id=None, first_name="", username=""):
    """
    Create global user if not exists.
    Also registers group membership if chat_id is provided.
    Signature keeps chat_id for backward compatibility of callers.
    """
    user_id = int(user_id)
    now = datetime.now().isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            user_id, first_name, username,
            meow_points, meow_coins, gym_level,
            last_meow, last_battle, created_at
        )
        VALUES (?, ?, ?, 0, 0, 1, 0, 0, ?)
    """, (
        user_id,
        first_name or "",
        username or "",
        now
    ))

    # If names are empty and user already existed, optionally update later
    # via update_user_info. Here we only INSERT OR IGNORE.

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_user(user_id, chat_id=None):
    """
    Get global user by user_id.
    chat_id is accepted for backward compatibility but ignored for lookup.
    If chat_id is given, membership is ensured.
    """
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM users WHERE user_id = ?
    """, (user_id,))
    user = cursor.fetchone()
    connection.close()

    if user and chat_id is not None:
        ensure_group_membership(user_id, chat_id)

    return user


def update_user_info(user_id, chat_id=None, first_name="", username=""):
    """
    Update profile info of the global user.
    """
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET first_name = ?, username = ?
        WHERE user_id = ?
    """, (
        first_name or "",
        username or "",
        user_id
    ))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def update_user(
    user_id,
    chat_id=None,
    first_name="",
    username="",
    meow_points=0,
    meow_coins=0,
    gym_level=1,
    last_meow=0
):
    """
    Full update of global user data.
    chat_id is optional and only used for membership.
    """
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET
            first_name = ?,
            username = ?,
            meow_points = ?,
            meow_coins = ?,
            gym_level = ?,
            last_meow = ?
        WHERE user_id = ?
    """, (
        first_name or "",
        username or "",
        int(meow_points),
        int(meow_coins),
        int(gym_level),
        float(last_meow),
        user_id
    ))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


# ==========================================
# Meow Points (Global)
# ==========================================

def add_meow_points(user_id, chat_id=None, amount=1):
    user_id = int(user_id)
    amount = int(amount)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_points = meow_points + ?
        WHERE user_id = ?
    """, (amount, user_id))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_meow_points(user_id, chat_id=None):
    user = get_user(user_id, chat_id)
    if not user:
        return 0
    return int(user["meow_points"])


def spend_meow_points(user_id, chat_id=None, amount=0):
    amount = int(amount)
    if amount <= 0:
        return False

    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_points = meow_points - ?
        WHERE user_id = ?
          AND meow_points >= ?
    """, (amount, user_id, amount))

    success = cursor.rowcount > 0

    if success:
        connection.commit()
    else:
        connection.rollback()

    connection.close()

    if success and chat_id is not None:
        ensure_group_membership(user_id, chat_id)

    return success


def add_meow_points_to_all(chat_id, amount):
    """
    Add points to every user who is a member of the given group.
    """
    amount = int(amount)
    if amount <= 0:
        return 0

    chat_id = str(chat_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET meow_points = meow_points + ?
            WHERE user_id IN (
                SELECT user_id FROM group_users WHERE chat_id = ?
            )
        """, (amount, chat_id))

        affected = cursor.rowcount
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ==========================================
# Meow Coins (Global)
# ==========================================

def add_meow_coins(user_id, chat_id=None, amount=0):
    user_id = int(user_id)
    amount = int(amount)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_coins = meow_coins + ?
        WHERE user_id = ?
    """, (amount, user_id))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_meow_coins(user_id, chat_id=None):
    user = get_user(user_id, chat_id)
    if not user:
        return 0
    return int(user["meow_coins"])


def spend_meow_coins(user_id, chat_id=None, amount=0):
    """
    Spend Meow Coins if balance is enough.
    Returns True on success, False otherwise.
    """
    user_id = int(user_id)
    amount = int(amount)
    if amount <= 0:
        return True

    user = get_user(user_id, chat_id)
    if not user:
        return False
    if int(user["meow_coins"] or 0) < amount:
        return False

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE users
        SET meow_coins = meow_coins - ?
        WHERE user_id = ? AND meow_coins >= ?
        """,
        (amount, user_id, amount),
    )
    ok = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if ok and chat_id is not None:
        ensure_group_membership(user_id, chat_id)
    return ok


def add_meow_coins_to_all(chat_id, amount):
    """
    Add coins to every member of the given group.
    """
    amount = int(amount)
    if amount <= 0:
        return 0

    chat_id = str(chat_id)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET meow_coins = meow_coins + ?
            WHERE user_id IN (
                SELECT user_id FROM group_users WHERE chat_id = ?
            )
        """, (amount, chat_id))

        affected = cursor.rowcount
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ==========================================
# Gym (Global)
# ==========================================

def set_gym_level(user_id, chat_id=None, level=1):
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET gym_level = ?
        WHERE user_id = ?
    """, (int(level), user_id))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_gym_level(user_id, chat_id=None):
    user = get_user(user_id, chat_id)
    if not user:
        return 1
    return int(user["gym_level"])


# ==========================================
# Last Meow (Global cooldown)
# ==========================================

def set_last_meow(user_id, chat_id=None, timestamp=0):
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET last_meow = ?
        WHERE user_id = ?
    """, (float(timestamp), user_id))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_last_meow(user_id, chat_id=None):
    user = get_user(user_id, chat_id)
    if not user:
        return 0
    return float(user["last_meow"])


# ==========================================
# Last Battle (Global cooldown)
# ==========================================

def set_last_battle(user_id, chat_id=None, timestamp=0):
    user_id = int(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET last_battle = ?
        WHERE user_id = ?
    """, (float(timestamp), user_id))

    connection.commit()
    connection.close()

    if chat_id is not None:
        ensure_group_membership(user_id, chat_id)


def get_last_battle(user_id, chat_id=None):
    user = get_user(user_id, chat_id)
    if not user:
        return 0
    # Support older DBs that might not have the column yet
    try:
        return float(user["last_battle"] or 0)
    except (KeyError, IndexError, TypeError):
        return 0


# ==========================================
# Ranking (Group-scoped via group_users)
# ==========================================

def get_top_users(chat_id, limit=30):
    """
    Ranking of users who are members of this group.
    Ordered by global meow_points then gym_level.
    """
    chat_id = str(chat_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT u.*
        FROM users u
        INNER JOIN group_users gu ON gu.user_id = u.user_id
        WHERE gu.chat_id = ?
        ORDER BY u.meow_points DESC, u.gym_level DESC
        LIMIT ?
    """, (chat_id, int(limit)))

    users = cursor.fetchall()
    connection.close()
    return users


def get_all_users(chat_id=None):
    """
    If chat_id given → members of that group.
    If None → all global users.
    """
    connection = get_connection()
    cursor = connection.cursor()

    if chat_id is not None:
        cursor.execute("""
            SELECT u.*
            FROM users u
            INNER JOIN group_users gu ON gu.user_id = u.user_id
            WHERE gu.chat_id = ?
        """, (str(chat_id),))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()
    connection.close()
    return users


# ==========================================
# Season helpers (unchanged logic)
# ==========================================

def get_active_season():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM seasons
        WHERE active = 1
        ORDER BY id DESC
        LIMIT 1
    """)
    season = cursor.fetchone()
    connection.close()
    return season


def create_season(season_number, start_date, end_date):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO seasons (season_number, start_date, end_date, active)
        VALUES (?, ?, ?, 1)
    """, (int(season_number), start_date, end_date))
    connection.commit()
    connection.close()


def close_active_season():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE seasons SET active = 0 WHERE active = 1
    """)
    connection.commit()
    connection.close()


def reset_meow_points():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET meow_points = 0")
    connection.commit()
    connection.close()


def add_meow_points_global(amount):
    """Add meow points to EVERY user in the database."""
    amount = int(amount)
    if amount <= 0:
        return 0
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE users SET meow_points = meow_points + ?",
            (amount,),
        )
        affected = cursor.rowcount
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_meow_coins_global(amount):
    """Add meow coins to EVERY user in the database."""
    amount = int(amount)
    if amount <= 0:
        return 0
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE users SET meow_coins = meow_coins + ?",
            (amount,),
        )
        affected = cursor.rowcount
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_next_season_number():
    """Return the next season number (max + 1, or 1 if none)."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(season_number) AS m FROM seasons")
    row = cursor.fetchone()
    connection.close()
    if row is None or row["m"] is None:
        return 1
    return int(row["m"]) + 1


def get_global_top_users(limit=30):
    """Global ranking by meow_points then gym_level."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM users
        ORDER BY meow_points DESC, gym_level DESC
        LIMIT ?
    """, (int(limit),))
    users = cursor.fetchall()
    connection.close()
    return users


def increment_daily_meow(user_id, points_earned, day_date):
    """
    Record one successful meow for the given Tehran day_date (YYYY-MM-DD).
    points_earned: the points awarded for this meow.
    """
    user_id = int(user_id)
    points_earned = int(points_earned)
    day_date = str(day_date)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO daily_meow_stats (user_id, day_date, meow_count, points_earned)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, day_date) DO UPDATE SET
            meow_count = meow_count + 1,
            points_earned = points_earned + excluded.points_earned
    """, (user_id, day_date, points_earned))
    connection.commit()
    connection.close()


def get_top_daily_meowers(day_date, limit=10):
    """Top users by points_earned on the given day_date."""
    day_date = str(day_date)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT d.user_id, d.meow_count, d.points_earned,
               u.first_name, u.username
        FROM daily_meow_stats d
        LEFT JOIN users u ON u.user_id = d.user_id
        WHERE d.day_date = ?
        ORDER BY d.points_earned DESC, d.meow_count DESC
        LIMIT ?
    """, (day_date, int(limit)))
    rows = cursor.fetchall()
    connection.close()
    return rows


def save_season_result(season_id, user_id, meow_points, final_rank, chat_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO season_results
            (season_id, user_id, chat_id, meow_points, final_rank, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (int(season_id), int(user_id), chat_id, int(meow_points), int(final_rank), now))
    connection.commit()
    connection.close()


# ==========================================
# 🐱 Pet Meow Database
# ==========================================

def get_pet(user_id):
    """Get pet for a user. Returns None if no pet."""
    user_id = int(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM pets WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def create_pet(user_id, pet_name="", awaiting_name=1):
    """
    Create a new pet for user. Fails silently if already exists
    (INSERT OR IGNORE). Returns the pet row.
    """
    user_id = int(user_id)
    now = datetime.now().isoformat()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO pets (
            user_id, pet_name, level, xp,
            relationship, hunger, energy,
            is_sleeping, sleep_until,
            games_played, foods_given, gifts_received,
            last_feed, last_play, last_pet, last_sleep,
            last_gift, last_interaction, last_random,
            awaiting_name, created_at
        ) VALUES (
            ?, ?, 1, 0,
            50, 80, 80,
            0, 0,
            0, 0, 0,
            0, 0, 0, 0,
            0, 0, 0,
            ?, ?
        )
    """, (
        user_id,
        pet_name or "",
        int(awaiting_name),
        now,
    ))
    connection.commit()
    connection.close()
    return get_pet(user_id)


def update_pet(user_id, **fields):
    """
    Update arbitrary pet fields.
    Only known columns are applied.
    """
    user_id = int(user_id)
    if not fields:
        return get_pet(user_id)

    allowed = {
        "pet_name", "level", "xp", "relationship", "hunger", "energy",
        "is_sleeping", "sleep_until",
        "games_played", "foods_given", "gifts_received",
        "last_feed", "last_play", "last_pet", "last_sleep",
        "last_gift", "last_interaction", "last_random",
        "awaiting_name",
        "last_point_claim",
    }

    sets = []
    values = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        sets.append(f"{key} = ?")
        values.append(value)

    if not sets:
        return get_pet(user_id)

    values.append(user_id)
    sql = f"UPDATE pets SET {', '.join(sets)} WHERE user_id = ?"

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(sql, values)
    connection.commit()
    connection.close()
    return get_pet(user_id)


def delete_pet(user_id):
    user_id = int(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM pets WHERE user_id = ?", (user_id,))
    connection.commit()
    connection.close()


def pet_exists(user_id):
    return get_pet(user_id) is not None


# ==========================================
# 🧠🎯💡 Content History (Truth / Dare / Fact)
# ==========================================

def get_seen_content_indices(user_id, content_type):
    """
    Return list of item_index values already seen by this user
    for the given content_type ('truth' | 'dare' | 'fact').
    """
    user_id = int(user_id)
    content_type = str(content_type)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT item_index FROM content_history
        WHERE user_id = ? AND content_type = ?
        """,
        (user_id, content_type),
    )
    rows = cursor.fetchall()
    connection.close()
    return [int(r["item_index"]) for r in rows]


def mark_content_seen(user_id, content_type, item_index):
    """
    Record that user has seen this content item.
    Uses INSERT OR IGNORE so duplicates are harmless.
    """
    from datetime import datetime

    user_id = int(user_id)
    content_type = str(content_type)
    item_index = int(item_index)
    now = datetime.now().isoformat()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO content_history
            (user_id, content_type, item_index, seen_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, content_type, item_index, now),
    )
    connection.commit()
    connection.close()


def count_seen_content(user_id, content_type):
    user_id = int(user_id)
    content_type = str(content_type)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM content_history
        WHERE user_id = ? AND content_type = ?
        """,
        (user_id, content_type),
    )
    row = cursor.fetchone()
    connection.close()
    return int(row["c"]) if row else 0


# ==========================================
# 🏦 Meow Bank
# ==========================================

def get_bank(user_id):
    user_id = int(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM banks WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def get_bank_by_card(card_number):
    card_number = str(card_number).strip()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM banks WHERE card_number = ?",
        (card_number,),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def card_number_exists(card_number):
    return get_bank_by_card(card_number) is not None


def create_bank(user_id, card_number):
    from datetime import datetime

    user_id = int(user_id)
    card_number = str(card_number).strip()
    now = datetime.now().isoformat()
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO banks (user_id, card_number, balance, created_at)
            VALUES (?, ?, 0, ?)
            """,
            (user_id, card_number, now),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        return None
    connection.close()
    return get_bank(user_id)


def update_bank_balance(user_id, delta):
    """
    Add delta to bank balance (can be negative).
    Returns updated bank row or None if fail / insufficient.
    """
    user_id = int(user_id)
    delta = int(delta)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT balance FROM banks WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None
    new_bal = int(row["balance"] or 0) + delta
    if new_bal < 0:
        connection.close()
        return None
    cursor.execute(
        "UPDATE banks SET balance = ? WHERE user_id = ?",
        (new_bal, user_id),
    )
    connection.commit()
    connection.close()
    return get_bank(user_id)


def set_bank_pending(user_id, action):
    from datetime import datetime

    user_id = int(user_id)
    action = str(action)
    now = datetime.now().isoformat()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO bank_pending (user_id, action, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, action, now),
    )
    connection.commit()
    connection.close()


def get_bank_pending(user_id):
    user_id = int(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM bank_pending WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def clear_bank_pending(user_id):
    user_id = int(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM bank_pending WHERE user_id = ?",
        (user_id,),
    )
    connection.commit()
    connection.close()


def bank_transfer(sender_id, receiver_id, amount):
    """
    Transfer amount from sender bank to receiver bank.
    Returns dict with success/reason.
    """
    sender_id = int(sender_id)
    receiver_id = int(receiver_id)
    amount = int(amount)
    if amount <= 0:
        return {"success": False, "reason": "invalid_amount"}
    if sender_id == receiver_id:
        return {"success": False, "reason": "self_transfer"}

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("BEGIN")
        cursor.execute(
            "SELECT balance, card_number FROM banks WHERE user_id = ?",
            (sender_id,),
        )
        sender = cursor.fetchone()
        cursor.execute(
            "SELECT balance, card_number FROM banks WHERE user_id = ?",
            (receiver_id,),
        )
        receiver = cursor.fetchone()

        if not sender:
            connection.rollback()
            return {"success": False, "reason": "sender_no_bank"}
        if not receiver:
            connection.rollback()
            return {"success": False, "reason": "receiver_no_bank"}

        s_bal = int(sender["balance"] or 0)
        if s_bal < amount:
            connection.rollback()
            return {
                "success": False,
                "reason": "not_enough_balance",
                "balance": s_bal,
            }

        cursor.execute(
            "UPDATE banks SET balance = balance - ? WHERE user_id = ?",
            (amount, sender_id),
        )
        cursor.execute(
            "UPDATE banks SET balance = balance + ? WHERE user_id = ?",
            (amount, receiver_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        return {"success": False, "reason": "error"}
    connection.close()

    s_bank = get_bank(sender_id)
    r_bank = get_bank(receiver_id)
    return {
        "success": True,
        "sender_balance": int(s_bank["balance"]) if s_bank else 0,
        "receiver_balance": int(r_bank["balance"]) if r_bank else 0,
        "sender_card": s_bank["card_number"] if s_bank else "",
        "receiver_card": r_bank["card_number"] if r_bank else "",
        "amount": amount,
    }

