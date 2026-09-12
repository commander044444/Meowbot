# ==========================================
# 🐱 MeowBot - Coins System (Global Account)
# ==========================================

import sqlite3

from config import DATABASE_NAME
from database import create_user, get_user, ensure_group_membership


# ==========================================
# Database Connection
# ==========================================

def get_connection():
    conn = sqlite3.connect(DATABASE_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# Validate Transfer
# ==========================================

def validate_transfer(sender_id, receiver_id, chat_id, amount):
    try:
        sender_id = int(sender_id)
        receiver_id = int(receiver_id)
        amount = int(amount)
        chat_id = str(chat_id) if chat_id is not None else None
    except (TypeError, ValueError):
        return {
            "success": False,
            "reason": "invalid_data"
        }

    if amount <= 0:
        return {
            "success": False,
            "reason": "invalid_amount"
        }

    if sender_id == receiver_id:
        return {
            "success": False,
            "reason": "self_transfer"
        }

    conn = get_connection()

    try:
        sender = conn.execute(
            """
            SELECT meow_coins
            FROM users
            WHERE user_id = ?
            """,
            (sender_id,)
        ).fetchone()

        receiver = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ?
            """,
            (receiver_id,)
        ).fetchone()

        if not sender:
            return {
                "success": False,
                "reason": "sender_not_found"
            }

        if not receiver:
            return {
                "success": False,
                "reason": "receiver_not_found"
            }

        sender_coins = int(sender["meow_coins"] or 0)

        if sender_coins < amount:
            return {
                "success": False,
                "reason": "not_enough_coins",
                "sender_coins": sender_coins
            }

        return {
            "success": True,
            "reason": "valid",
            "sender_coins": sender_coins
        }

    finally:
        conn.close()


# ==========================================
# Transfer Coins (Global balances)
# ==========================================

def transfer_coins(sender_id, receiver_id, chat_id, amount):
    try:
        sender_id = int(sender_id)
        receiver_id = int(receiver_id)
        amount = int(amount)
        chat_id = str(chat_id) if chat_id is not None else None
    except (TypeError, ValueError):
        return {
            "success": False,
            "reason": "invalid_data"
        }

    validation = validate_transfer(
        sender_id=sender_id,
        receiver_id=receiver_id,
        chat_id=chat_id,
        amount=amount
    )

    if not validation["success"]:
        return validation

    conn = get_connection()

    try:
        conn.execute("BEGIN")

        sender = conn.execute(
            """
            SELECT meow_coins
            FROM users
            WHERE user_id = ?
            """,
            (sender_id,)
        ).fetchone()

        if not sender:
            conn.rollback()
            return {
                "success": False,
                "reason": "sender_not_found"
            }

        sender_coins = int(sender["meow_coins"] or 0)

        if sender_coins < amount:
            conn.rollback()
            return {
                "success": False,
                "reason": "not_enough_coins",
                "sender_coins": sender_coins
            }

        # Deduct from sender
        cursor = conn.execute(
            """
            UPDATE users
            SET meow_coins = meow_coins - ?
            WHERE user_id = ?
              AND meow_coins >= ?
            """,
            (amount, sender_id, amount)
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return {
                "success": False,
                "reason": "transfer_failed"
            }

        # Add to receiver
        cursor = conn.execute(
            """
            UPDATE users
            SET meow_coins = meow_coins + ?
            WHERE user_id = ?
            """,
            (amount, receiver_id)
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return {
                "success": False,
                "reason": "receiver_not_found"
            }

        conn.commit()

        sender_after = conn.execute(
            """
            SELECT meow_coins
            FROM users
            WHERE user_id = ?
            """,
            (sender_id,)
        ).fetchone()

        receiver_after = conn.execute(
            """
            SELECT meow_coins
            FROM users
            WHERE user_id = ?
            """,
            (receiver_id,)
        ).fetchone()

        # Ensure membership for both if chat_id present
        if chat_id is not None:
            ensure_group_membership(sender_id, chat_id)
            ensure_group_membership(receiver_id, chat_id)

        return {
            "success": True,
            "reason": "transfer_completed",
            "amount": amount,
            "sender_coins": int(sender_after["meow_coins"]),
            "receiver_coins": int(receiver_after["meow_coins"])
        }

    except Exception:
        conn.rollback()
        return {
            "success": False,
            "reason": "database_error"
        }

    finally:
        conn.close()


# ==========================================
# Parse Transfer Command
# ==========================================

def parse_transfer_command(text):
    if not text:
        return None

    text = str(text).strip()

    if not text:
        return None

    # یکسان‌سازی فاصله‌های خاص
    text = text.replace("\u200c", " ")

    parts = text.split()

    if not parts:
        return None

    # --------------------------------------
    # انتقال میویی 10
    # انتقال میو 10
    # انتقال 10
    # --------------------------------------

    if len(parts) == 3:
        command = parts[0].strip().lower()
        middle = parts[1].strip().lower()

        if command == "انتقال" and middle in {
            "میویی",
            "میو"
        }:
            try:
                amount = int(parts[2])
            except ValueError:
                return None

            if amount <= 0:
                return None

            return amount

    # --------------------------------------
    # انتقال 10
    # --------------------------------------

    if len(parts) == 2:
        command = parts[0].strip().lower()

        if command in {
            "انتقال",
            "transfer"
        }:
            try:
                amount = int(parts[1])
            except ValueError:
                return None

            if amount <= 0:
                return None

            return amount

    return None
