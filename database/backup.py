# ==========================================
# Real DB Backup (JSON gzip) → send to PV
# ==========================================

from __future__ import annotations

import gzip
import io
import json
from datetime import datetime, date, time as dtime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from database.pool import fetch, execute

TEHRAN = ZoneInfo("Asia/Tehran")

# جداول مهم برای بکاپ کامل منطقی
BACKUP_TABLES = [
    "users",
    "groups",
    "group_users",
    "pets",
    "seasons",
    "season_results",
    "daily_meow_stats",
    "banks",
    "bank_pending",
    "transactions",
    "inventory",
    "shop_items",
    "achievements",
    "user_achievements",
    "missions",
    "user_missions",
    "events",
    "admins",
    "audit_logs",
    "bot_settings",
    "bug_reports",
    "group_stats",
    "bans",
    "tickets",
    "backups",
    "content_history",
    "guide_history",
]


def _json_safe(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date, dtime)):
        try:
            return val.isoformat()
        except Exception:
            return str(val)
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, (bytes, bytearray, memoryview)):
        return bytes(val).hex()
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_safe(v) for v in val]
    # asyncpg Record etc.
    try:
        return _json_safe(dict(val))
    except Exception:
        return str(val)


async def _table_exists(name: str) -> bool:
    row = await fetch(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = $1
        LIMIT 1
        """,
        name,
    )
    return bool(row)


async def export_backup_dict(created_by: int) -> dict:
    tables: dict = {}
    counts: dict = {}
    for tname in BACKUP_TABLES:
        try:
            if not await _table_exists(tname):
                continue
            rows = await fetch(f'SELECT * FROM "{tname}"')
            data = [_json_safe(dict(r)) for r in (rows or [])]
            tables[tname] = data
            counts[tname] = len(data)
        except Exception as e:
            tables[tname] = {"__error__": str(e)}
            counts[tname] = -1

    return {
        "format": "meowbot_json_v1",
        "created_at": datetime.now(TEHRAN).isoformat(),
        "created_by": int(created_by),
        "table_counts": counts,
        "tables": tables,
    }


async def build_backup_file(created_by: int) -> tuple[str, bytes, dict]:
    """
    Returns (filename, gzip_bytes, meta)
    """
    payload = await export_backup_dict(created_by)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as gz:
        gz.write(raw)
    data = buf.getvalue()
    stamp = datetime.now(TEHRAN).strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"MeowBot_Backup_{stamp}.json.gz"
    meta = {
        "filename": fname,
        "size_bytes": len(data),
        "tables": payload.get("table_counts") or {},
        "created_by": int(created_by),
    }
    return fname, data, meta


async def record_backup_meta(fname: str, size: int, created_by: int, note: str):
    try:
        await execute(
            """
            INSERT INTO backups (filename, size_bytes, created_by, status, note)
            VALUES ($1, $2, $3, 'ok', $4)
            """,
            fname,
            int(size),
            int(created_by),
            note[:500] if note else "",
        )
    except Exception:
        pass


async def send_backup_to_pv(bot, user_id: int) -> tuple[bool, str]:
    """
    ساخت بکاپ واقعی و ارسال فایل به پیوی کاربر.
    """
    try:
        fname, data, meta = await build_backup_file(user_id)
    except Exception as e:
        return False, f"ساخت بکاپ ناموفق: `{e}`"

    note = json.dumps(meta.get("tables") or {}, ensure_ascii=False)[:400]
    await record_backup_meta(fname, meta["size_bytes"], user_id, note)

    size_kb = max(1, meta["size_bytes"] // 1024)
    caption = (
        f"💾 بکاپ MeowBot\n"
        f"📅 {meta.get('filename', fname)}\n"
        f"📦 حجم: `{size_kb}` KB\n"
        f"👤 برای: `{user_id}`\n\n"
        f"فایل gzip + JSON است. نگهش دار."
    )

    # تلاش‌های مختلف API بله / python-bale-bot
    last_err = None
    try:
        from bale import InputFile
    except Exception:
        InputFile = None

    # 1) bot.send_document
    if hasattr(bot, "send_document"):
        try:
            doc = InputFile(data, file_name=fname) if InputFile else data
            kwargs = {"caption": caption}
            try:
                await bot.send_document(user_id, doc, caption=caption, file_name=fname)
            except TypeError:
                try:
                    await bot.send_document(user_id, doc, caption=caption)
                except TypeError:
                    await bot.send_document(chat_id=user_id, document=doc, caption=caption, file_name=fname)
            return True, f"✅ بکاپ ساخته و به پیوی `{user_id}` ارسال شد.\n📦 `{fname}` · `{size_kb}` KB"
        except Exception as e:
            last_err = e

    # 2) get_chat / user object
    try:
        chat = None
        if hasattr(bot, "get_chat"):
            chat = await bot.get_chat(user_id)
        if chat is not None and hasattr(chat, "send_document"):
            doc = InputFile(data, file_name=fname) if InputFile else data
            try:
                await chat.send_document(doc, caption=caption)
            except TypeError:
                await chat.send_document(document=doc, caption=caption)
            return True, f"✅ بکاپ ساخته و به پیوی `{user_id}` ارسال شد.\n📦 `{fname}` · `{size_kb}` KB"
    except Exception as e:
        last_err = e

    # 3) fallback: اگر فایل خیلی بزرگ/آپلود بسته بود، تکه متنی خلاصه + ذخیره فقط متا
    try:
        summary = (
            f"⚠️ ارسال فایل ممکن نشد ({last_err}).\n"
            f"بکاپ در دیتابیس به‌عنوان meta ثبت شد:\n"
            f"`{fname}` · `{size_kb}` KB\n\n"
            f"تعداد ردیف جداول:\n"
        )
        for k, v in sorted((meta.get("tables") or {}).items()):
            summary += f"• `{k}`: {v}\n"
        # اگر حجم JSON خام کوچک بود، به‌صورت تکه هم می‌فرستیم؟ نه — فقط پیام
        await bot.send_message(user_id, summary)
        return False, (
            f"⚠️ بکاپ ساخته شد ولی ارسال فایل شکست خورد:\n`{last_err}`\n"
            f"متادیتا ثبت شد: `{fname}`"
        )
    except Exception as e2:
        return False, f"❌ بکاپ ساخته شد ولی نه فایل و نه پیام رفت:\n`{last_err}` / `{e2}`"
