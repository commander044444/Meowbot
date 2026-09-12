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
