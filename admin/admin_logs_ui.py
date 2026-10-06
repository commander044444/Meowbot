# ==========================================
# لاگ خوانای فعالیت ادمین‌ها برای Owner
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.logs import get_recent_logs
from database.users import get_user
from database.pool import fetch


def _kb(rows):
    kb = InlineKeyboardMarkup()
    rn = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(
                InlineKeyboardButton(text=str(text)[:64], callback_data=str(data)[:64]),
                row=rn,
            )
        rn += 1
    return kb


async def _name(uid) -> str:
    if uid is None:
        return "؟"
    try:
        u = await get_user(int(uid))
        if u:
            n = u.get("first_name") or ""
            un = u.get("username")
            if un:
                return f"{n} (@{un})".strip()
            return n or str(uid)
    except Exception:
        pass
    return str(uid)


def _fmt_time(ts) -> str:
    if not ts:
        return ""
    try:
        s = str(ts)
        # 2026-10-06 12:00:00+00:00 → کوتاه
        if "T" in s:
            s = s.replace("T", " ")
        return s[:16]
    except Exception:
        return str(ts)[:16]


async def format_log_line(row: dict) -> str:
    """یک خط لاگ خیلی خوانا به فارسی."""
    action = str(row.get("action") or "")
    actor = await _name(row.get("actor_id") or row.get("admin_id"))
    target_raw = row.get("target")
    details = row.get("details") or {}
    if isinstance(details, str):
        try:
            import json
            details = json.loads(details)
        except Exception:
            details = {"value": details}
    if not isinstance(details, dict):
        details = {}

    target_name = None
    if target_raw not in (None, "", "None"):
        try:
            target_name = await _name(int(target_raw))
        except Exception:
            target_name = str(target_raw)

    t = _fmt_time(row.get("created_at"))
    prefix = f"🕐 {t}\n" if t else ""

    # --- نگاشت خوانا ---
    if action in ("coin_add", "eco_one_coin") or (action == "coin_add"):
        val = details.get("value") or details.get("amount") or details.get("delta")
        return f"{prefix}🪙 **{actor}** به **{target_name or target_raw}** سکه داد — مقدار `{val}`"

    if action in ("coin_sub",):
        val = details.get("value")
        return f"{prefix}🪙 **{actor}** از **{target_name or target_raw}** سکه کم کرد — مقدار `{val}`"

    if action in ("pt_add", "eco_one_point"):
        val = details.get("value")
        return f"{prefix}⭐ **{actor}** به **{target_name or target_raw}** امتیاز داد — مقدار `{val}`"

    if action in ("pt_sub",):
        val = details.get("value")
        return f"{prefix}⭐ **{actor}** از **{target_name or target_raw}** امتیاز کم کرد — `{val}`"

    if action in ("gym", "eco_one_gym"):
        val = details.get("value")
        return f"{prefix}🏋️ **{actor}** سطح Gym **{target_name or target_raw}** را `{val}` کرد"

    if action in ("ban", "user_ban"):
        reason = details.get("reason") or details.get("code") or ""
        extra = f" — دلیل: {reason}" if reason else ""
        return f"{prefix}🚫 **{actor}** کاربر **{target_name or target_raw}** را **بن** کرد{extra}"

    if action in ("unban", "user_unban"):
        return f"{prefix}✅ **{actor}** بن **{target_name or target_raw}** را برداشت"

    if action in ("ticket_close",):
        return f"{prefix}🎫 **{actor}** تیکت `#{target_raw}` را **حل/بسته** کرد"

    if action in ("ticket_reply",):
        return f"{prefix}💬 **{actor}** به تیکت `#{target_raw}` **پاسخ** داد"

    if action in ("ticket_open", "ticket_view"):
        return f"{prefix}🎫 **{actor}** تیکت `#{target_raw}` را باز کرد"

    if action in ("report_resolve",):
        return f"{prefix}🚨 **{actor}** گزارش `#{target_raw}` را **حل** کرد"

    if action in ("report_view", "report_open"):
        return f"{prefix}🚨 **{actor}** گزارش `#{target_raw}` را باز کرد"

    if action in ("admin_msg", "msg"):
        return f"{prefix}📨 **{actor}** به **{target_name or target_raw}** پیام شخصی فرستاد"

    if action in ("admin_warning",):
        cnt = details.get("count")
        return f"{prefix}⚠️ **{actor}** به ادمین **{target_name or target_raw}** اخطار داد (#{cnt})"

    if action in ("admin_remove",):
        return f"{prefix}🗑 **{actor}** ادمین **{target_name or target_raw}** را حذف کرد"

    if action in ("admin_add", "admin_restore"):
        return f"{prefix}➕ **{actor}** ادمین **{target_name or target_raw}** را اضافه/بازگردانی کرد"

    if action in ("role_change", "perm_toggle"):
        return f"{prefix}🎖️ **{actor}** نقش/دسترسی **{target_name or target_raw}** را تغییر داد — {details}"

    if action in ("admin_warn_clear",):
        return f"{prefix}🧹 **{actor}** اخطارهای **{target_name or target_raw}** را پاک کرد"

    # generic
    tgt = f" → {target_name or target_raw}" if target_raw else ""
    det = f" | {details}" if details else ""
    return f"{prefix}📌 **{actor}** `{action}`{tgt}{det}"


async def build_admin_logs_text(actor_id: int = None, page: int = 0, per_page: int = 12):
    """
    فقط لاگ ادمین‌ها (بدون Owner).
    صفحه ۰ = جدیدترین فعالیت‌ها.
    """
    from config import OWNER_ID
    owner_id = int(OWNER_ID)
    page = max(0, int(page or 0))
    offset = page * per_page
    limit = per_page

    if actor_id:
        # اگر اشتباهاً Owner انتخاب شد، خالی برگردان
        if int(actor_id) == owner_id:
            return (
                "📜 لاگ Owner اینجا نمایش داده نمی‌شود.\nفقط فعالیت ادمین‌ها.",
                _kb([[("🔙 لیست ادمین", "ap:list")]]),
            )
        rows = await fetch(
            """
            SELECT id, actor_id, action, target, details, result, created_at
            FROM audit_logs
            WHERE actor_id = $1
              AND actor_id <> $4
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT $2 OFFSET $3
            """,
            int(actor_id), limit, offset, owner_id,
        )
        title_name = await _name(actor_id)
        title = f"📜 **لاگ ادمین: {title_name}**\n_جدیدترین‌ها اول_"
    else:
        # همه ادمین‌ها به‌جز Owner + فقط کسانی که در جدول admins هستند یا بوده‌اند
        rows = await fetch(
            """
            SELECT id, actor_id, action, target, details, result, created_at
            FROM audit_logs
            WHERE actor_id IS NOT NULL
              AND actor_id <> $3
              AND (
                    actor_id IN (SELECT user_id FROM admins)
                 OR actor_id IN (SELECT user_id FROM admin_profiles)
              )
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset, owner_id,
        )
        title = "📜 **لاگ فعالیت ادمین‌ها**\n_Owner در این لیست نیست · جدیدترین‌ها اول_"

    lines = [
        title,
        "━━━━━━━━━━━━━━",
        "_آخرین عملیات‌ها (خوانا)_",
        "",
    ]
    rows = [dict(r) for r in (rows or [])]
    if not rows:
        lines.append("هنوز لاگی ثبت نشده.")
    else:
        for r in rows:
            try:
                lines.append(await format_log_line(r))
                lines.append("┄┄┄┄┄┄┄┄┄┄")
            except Exception as e:
                lines.append(f"• `{r.get('action')}` ({e})")

    # pagination
    rows_kb = []
    nav = []
    if page > 0:
        nav.append(("◀️ قبلی", f"ap:alog:{actor_id or 0}:{page-1}"))
    nav.append(("▶️ بعدی", f"ap:alog:{actor_id or 0}:{page+1}"))
    if nav:
        rows_kb.append(nav)
    if actor_id:
        rows_kb.append([("🔙 کارت ادمین", f"ap:view:{actor_id}")])
    else:
        rows_kb.append([("🔙 لیست ادمین", "ap:list")])
    rows_kb.append([("🔙 Owner", "owner:home")])
    return "\n".join(lines), _kb(rows_kb)
