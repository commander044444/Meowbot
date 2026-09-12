# ==========================================
# 🐱 MeowBot - Database
# ==========================================

import sqlite3
from datetime import datetime

from config import DATABASE_NAME


# ==========================================
# Connection
# ==========================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


# ==========================================
# Database Initialization
# ==========================================

def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,

            first_name TEXT DEFAULT '',
            username TEXT DEFAULT '',

            meow_points INTEGER DEFAULT 0,
            meow_coins INTEGER DEFAULT 0,

            gym_level INTEGER DEFAULT 1,

            last_meow REAL DEFAULT 0,

            created_at TEXT NOT NULL,

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
            chat_id TEXT NOT NULL,

            meow_points INTEGER DEFAULT 0,

            final_rank INTEGER DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# User Management
# ==========================================

def create_user(
    user_id,
    chat_id,
    first_name="",
    username=""
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            user_id,
            chat_id,
            first_name,
            username,
            meow_points,
            meow_coins,
            gym_level,
            last_meow,
            created_at
        )
        VALUES (?, ?, ?, ?, 0, 0, 1, 0, ?)
    """, (
        int(user_id),
        str(chat_id),
        first_name or "",
        username or "",
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()


def get_user(user_id, chat_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        int(user_id),
        str(chat_id)
    ))

    user = cursor.fetchone()

    connection.close()

    return user


def update_user_info(
    user_id,
    chat_id,
    first_name="",
    username=""
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET
            first_name = ?,
            username = ?
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        first_name or "",
        username or "",
        int(user_id),
        str(chat_id)
    ))

    connection.commit()
    connection.close()


# ==========================================
# Meow Points
# ==========================================

def add_meow_points(
    user_id,
    chat_id,
    amount=1
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_points = meow_points + ?
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        int(amount),
        int(user_id),
        str(chat_id)
    ))

    connection.commit()
    connection.close()


def get_meow_points(user_id, chat_id):
    user = get_user(
        user_id,
        chat_id
    )

    if not user:
        return 0

    return int(user["meow_points"])


def spend_meow_points(
    user_id,
    chat_id,
    amount
):
    """
    مقدار مشخصی Meow Point خرج می‌کند.

    اگر موجودی کافی نباشد:
        False

    اگر موفق باشد:
        True
    """

    amount = int(amount)

    if amount <= 0:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_points = meow_points - ?
        WHERE user_id = ?
        AND chat_id = ?
        AND meow_points >= ?
    """, (
        amount,
        int(user_id),
        str(chat_id),
        amount
    ))

    success = cursor.rowcount > 0

    if success:
        connection.commit()
    else:
        connection.rollback()

    connection.close()

    return success


# ==========================================
# Meow Points - Global
# ==========================================

def add_meow_points_to_all(chat_id, amount):
    """
    به تمام کاربران ثبت‌شده یک گروه
    مقدار مشخصی Meow Point اضافه می‌کند.

    خروجی:
        تعداد کاربران تغییر داده‌شده
    """

    amount = int(amount)

    if amount <= 0:
        return 0

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET meow_points = meow_points + ?
            WHERE chat_id = ?
        """, (
            amount,
            str(chat_id)
        ))

        affected_users = cursor.rowcount

        connection.commit()

        return affected_users

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# Meow Coins
# ==========================================

def add_meow_coins(
    user_id,
    chat_id,
    amount
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_coins = meow_coins + ?
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        int(amount),
        int(user_id),
        str(chat_id)
    ))

    connection.commit()
    connection.close()


def get_meow_coins(user_id, chat_id):
    user = get_user(
        user_id,
        chat_id
    )

    if not user:
        return 0

    return int(user["meow_coins"])


# ==========================================
# Meow Coins - Global
# ==========================================

def add_meow_coins_to_all(chat_id, amount):
    """
    به تمام کاربران ثبت‌شده یک گروه
    مقدار مشخصی Meow Coin اضافه می‌کند.

    خروجی:
        تعداد کاربران تغییر داده‌شده
    """

    amount = int(amount)

    if amount <= 0:
        return 0

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET meow_coins = meow_coins + ?
            WHERE chat_id = ?
        """, (
            amount,
            str(chat_id)
        ))

        affected_users = cursor.rowcount

        connection.commit()

        return affected_users

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# Gym
# ==========================================

def set_gym_level(
    user_id,
    chat_id,
    level
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET gym_level = ?
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        int(level),
        int(user_id),
        str(chat_id)
    ))

    connection.commit()
    connection.close()


def get_gym_level(
    user_id,
    chat_id
):
    user = get_user(
        user_id,
        chat_id
    )

    if not user:
        return 1

    return int(user["gym_level"])


# ==========================================
# Last Meow
# ==========================================

def set_last_meow(
    user_id,
    chat_id,
    timestamp
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET last_meow = ?
        WHERE user_id = ?
        AND chat_id = ?
    """, (
        float(timestamp),
        int(user_id),
        str(chat_id)
    ))

    connection.commit()
    connection.close()


def get_last_meow(
    user_id,
    chat_id
):
    user = get_user(
        user_id,
        chat_id
    )

    if not user:
        return 0

    return float(user["last_meow"])


# ==========================================
# Ranking
# ==========================================

def get_top_users(
    chat_id,
    limit=30
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE chat_id = ?
        ORDER BY meow_points DESC, gym_level DESC
        LIMIT ?
    """, (
        str(chat_id),
        int(limit)
    ))

    users = cursor.fetchall()

    connection.close()

    return users


# ==========================================
# All Users
# ==========================================

def get_all_users(chat_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE chat_id = ?
    """, (
        str(chat_id),
    ))

    users = cursor.fetchall()

    connection.close()

    return users


# ==========================================
# Season
# ==========================================

def get_active_season():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM seasons
        WHERE active = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    season = cursor.fetchone()

    connection.close()

    return season


def create_season(
    season_number,
    start_date,
    end_date
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO seasons (
            season_number,
            start_date,
            end_date,
            active
        )
        VALUES (?, ?, ?, 1)
    """, (
        int(season_number),
        start_date,
        end_date
    ))

    connection.commit()
    connection.close()


def close_active_season():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE seasons
        SET active = 0
        WHERE active = 1
    """)

    connection.commit()
    connection.close()


# ==========================================
# Reset Meow Points
# ==========================================

def reset_meow_points():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET meow_points = 0
    """)

    connection.commit()
    connection.close()