# ==========================================
# ⚙️ تنظیمات گروه برای ادمین‌های گروه (در PV)
# ==========================================
# ادمین گروه می‌تواند در پیوی ربات:
# - پاسخ به میو (روشن/خاموش)
# - پیام خودکار راهنما (روشن/خاموش)
# را برای گروه خودش مدیریت کند.

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID
from database.groups import (
    get_user_groups, get_group, set_meow_enabled, set_guide_settings,
    get_meow_enabled, get_interaction, set_interaction,
)
from database.logs import log_action


def _kb(rows):
    kb = InlineKeyboardMarkup()
    row_num = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(
                InlineKeyboardButton(text=str(text), callback_data=str(data)),
                row=row_num,
            )
        row_num += 1
    return kb


async def is_group_admin(bot, chat_id, user_id) -> bool:
    """بررسی ادمین بودن کاربر در گروه (Bale API + fallback Owner)."""
    if int(user_id) == int(OWNER_ID):
        return True
    cid = chat_id
    # روش‌های رایج در python-bale-bot
    methods = [
        "get_chat_member",
        "get_chat_administrators",
        "getChatMember",
        "getChatAdministrators",
    ]
    for name in methods:
        fn = getattr(bot, name, None)
        if not callable(fn):
            continue
        try:
            if "administrators" in name.lower() or "Administrators" in name:
                admins = await fn(cid)
                if not admins:
                    continue
                for a in admins:
                    uid = None
                    if hasattr(a, "user"):
                        uid = getattr(a.user, "id", None)
                    elif hasattr(a, "id"):
                        uid = a.id
                    elif isinstance(a, dict):
                        uid = (a.get("user") or {}).get("id") or a.get("id")
                    if uid is not None and int(uid) == int(user_id):
                        return True
            else:
                member = await fn(cid, user_id)
                status = None
                if member is None:
                    continue
                if hasattr(member, "status"):
                    status = str(member.status).lower()
                elif isinstance(member, dict):
                    status = str(member.get("status", "")).lower()
                if status in ("creator", "administrator", "admin", "owner"):
                    return True
        except Exception:
            continue
    return False


def list_groups_kb(groups):
    rows = []
    for g in groups[:20]:
        title = (g.get("title") or g.get("username") or g.get("chat_id") or "?")[:28]
        cid = g.get("chat_id")
        rows.append([(f"💬 {title}", f"gset:open:{cid}")])
    rows.append([("🔄 بروزرسانی لیست", "gset:list")])
    rows.append([("🏠 منوی اصلی", "menu:main")])
    return _kb(rows)


def group_panel_kb(chat_id, meow_on: bool, guide_on: bool):
    meow_btn = "🐱 میو: ✅ روشن" if meow_on else "🐱 میو: ❌ خاموش"
    guide_btn = "💡 پیام خودکار: ✅ روشن" if guide_on else "💡 پیام خودکار: ❌ خاموش"
    return _kb([
        [(meow_btn, f"gset:meow:{chat_id}")],
        [(guide_btn, f"gset:guide:{chat_id}")],
        [("📋 وضعیت", f"gset:open:{chat_id}")],
        [("🔙 لیست گروه‌ها", "gset:list")],
        [("🏠 منوی اصلی", "menu:main")],
    ])


def status_text(g: dict) -> str:
    title = g.get("title") or g.get("username") or g.get("chat_id")
    meow = g.get("meow_enabled")
    if meow is None:
        meow = True
    guide = g.get("guide_enabled")
    if guide is None:
        guide = True
    interval = int(g.get("guide_interval") or 0)
    hours = f"{interval // 3600}س {(interval % 3600) // 60}د" if interval else "۲–۳ ساعت (تصادفی)"
    return (
        f"⚙️ **تنظیمات گروه**\n"
        f"━━━━━━━━━━━━━━\n"
        f"💬 {title}\n"
        f"🆔 `{g.get('chat_id')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🐱 پاسخ به میو: {'✅ روشن' if meow else '❌ خاموش'}\n"
        f"💡 پیام خودکار راهنما: {'✅ روشن' if guide else '❌ خاموش'}\n"
        f"⏱ فاصله تقریبی راهنما: {hours}\n"
        f"━━━━━━━━━━━━━━\n"
        f"با دکمه‌ها روشن/خاموش کن.\n"
        f"فقط **ادمین همان گروه** می‌تواند تغییر دهد."
    )


async def show_group_list(user_id: int):
    groups = await get_user_groups(user_id)
    if not groups:
        return (
            "⚙️ **تنظیمات گروه**\n"
            "━━━━━━━━━━━━━━\n"
            "گروهی پیدا نشد.\n\n"
            "اول ربات را به گروه اضافه کن و یک پیام در گروه بفرست "
            "تا گروه ثبت شود، بعد دوباره اینجا بیا.",
            _kb([[("🔄 تلاش دوباره", "gset:list")], [("🏠 منوی اصلی", "menu:main")]]),
        )
    text = (
        "⚙️ **تنظیمات گروه**\n"
        "━━━━━━━━━━━━━━\n"
        "گروهی که ادمینش هستی را انتخاب کن:\n"
        "(اگر ادمین نباشی، تغییر اعمال نمی‌شود)"
    )
    return text, list_groups_kb(groups)


async def handle_gset_callback(bot, user_id: int, data: str):
    """
    Returns (text, keyboard) or raises.
    """
    parts = data.split(":")
    # gset:list | gset:open:CID | gset:meow:CID | gset:guide:CID
    cmd = parts[1] if len(parts) > 1 else "list"

    if cmd == "list":
        return await show_group_list(user_id)

    if len(parts) < 3:
        return await show_group_list(user_id)

    chat_id = parts[2]
    g = await get_group(chat_id)
    if not g:
        return "❌ گروه پیدا نشد.", _kb([[("🔙 لیست", "gset:list")]])

    # فقط ادمین گروه
    admin = await is_group_admin(bot, chat_id, user_id)
    if not admin:
        return (
            "⛔ فقط **ادمین همین گروه** می‌تواند تنظیمات را تغییر دهد.\n"
            f"گروه: `{chat_id}`",
            _kb([[("🔙 لیست گروه‌ها", "gset:list")]]),
        )

    if cmd == "open":
        return status_text(g), group_panel_kb(
            chat_id,
            bool(g.get("meow_enabled") if g.get("meow_enabled") is not None else True),
            bool(g.get("guide_enabled") if g.get("guide_enabled") is not None else True),
        )

    if cmd == "meow":
        current = g.get("meow_enabled")
        if current is None:
            current = True
        new_val = not bool(current)
        await set_meow_enabled(chat_id, new_val)
        # همگام با interaction برای سازگاری
        await set_interaction(chat_id, new_val)
        await log_action(user_id, "group_meow_toggle", str(chat_id), {"meow_enabled": new_val})
        g = await get_group(chat_id)
        return (
            status_text(g) + f"\n\n✅ پاسخ به میو {'روشن' if new_val else 'خاموش'} شد.",
            group_panel_kb(chat_id, new_val, bool(g.get("guide_enabled", True))),
        )

    if cmd == "guide":
        current = g.get("guide_enabled")
        if current is None:
            current = True
        new_val = not bool(current)
        await set_guide_settings(chat_id, enabled=new_val)
        await log_action(user_id, "group_guide_toggle", str(chat_id), {"guide_enabled": new_val})
        g = await get_group(chat_id)
        meow = bool(g.get("meow_enabled") if g.get("meow_enabled") is not None else True)
        return (
            status_text(g) + f"\n\n✅ پیام خودکار {'روشن' if new_val else 'خاموش'} شد.",
            group_panel_kb(chat_id, meow, new_val),
        )

    return await show_group_list(user_id)
