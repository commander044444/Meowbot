# ==========================================
# مدیریت دسترسی‌های ادمین (واقعی — تک‌تک روشن/خاموش)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.admins import (
    list_admins, get_admin, update_admin_permissions,
    ALL_PERMISSIONS, has_permission, is_owner,
)
from database.logs import log_action
from database.users import get_user

# برچسب فارسی + گروه منطقی
PERM_META = [
    ("users.view", "👁 مشاهده کاربران"),
    ("users.edit", "✏️ ویرایش سکه/امتیاز"),
    ("users.ban", "🚫 بن / آنبن"),
    ("groups.view", "💬 مشاهده گروه‌ها"),
    ("groups.edit", "⚙️ تنظیم گروه‌ها"),
    ("economy.view", "💰 مشاهده اقتصاد"),
    ("economy.edit", "💸 اقتصاد سراسری"),
    ("broadcast.send", "📢 همگانی / Broadcast"),
    ("tickets.manage", "🎫 تیکت‌ها"),
    ("logs.view", "📜 لاگ‌ها"),
    ("pets.view", "🐾 مشاهده Pet"),
    ("pets.edit", "🐾 ویرایش Pet"),
    ("battles.manage", "⚔️ مدیریت نبرد"),
    ("guides.view", "💡 مشاهده Guide"),
    ("guides.edit", "💡 ویرایش Guide"),
    ("missions.manage", "🎯 مأموریت‌ها"),
    ("achievements.manage", "🏆 دستاوردها"),
    ("events.manage", "🎉 ایونت‌ها"),
    ("seasons.manage", "📅 فصل‌ها"),
    ("admins.view", "🛡 مشاهده ادمین‌ها"),
    ("admins.manage", "🛡 مدیریت ادمین‌ها"),
    ("database.backup", "💾 بکاپ"),
    ("database.restore", "♻️ ریستور"),
    ("settings.manage", "⚙️ تنظیمات"),
    ("maintenance.manage", "🚧 Maintenance"),
]

# اطمینان همه در ALL_PERMISSIONS باشند
for key, _ in PERM_META:
    if key not in ALL_PERMISSIONS:
        ALL_PERMISSIONS.append(key)


def _kb(rows):
    kb = InlineKeyboardMarkup()
    rn = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(InlineKeyboardButton(text=str(text)[:64], callback_data=str(data)[:64]), row=rn)
        rn += 1
    return kb


async def admins_list_text():
    admins = await list_admins()
    lines = [
        "🛡 **مدیریت ادمین‌ها و دسترسی‌ها**",
        "━━━━━━━━━━━━━━",
        "یک ادمین را انتخاب کن تا دسترسی‌ها را روشن/خاموش کنی:",
    ]
    rows = []
    if not admins:
        lines.append("ادمینی ثبت نشده.")
    for a in admins or []:
        uid = int(a["user_id"])
        role = a.get("role") or "ADMIN"
        en = "🟢" if a.get("enabled", True) else "🔴"
        u = await get_user(uid)
        name = (u or {}).get("first_name") or str(uid)
        nperm = len(a.get("permissions") or [])
        rows.append([(f"{en} {name} | {role} ({nperm})", f"ap:view:{uid}")])
    rows.append([("➕ افزودن ادمین", "owner:admin_add")])
    rows.append([("🔙 منوی Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def admin_perms_card(target_id: int):
    a = await get_admin(target_id)
    if not a:
        return "❌ این کاربر ادمین نیست.", _kb([[("🔙", "ap:list")]])
    u = await get_user(target_id)
    name = (u or {}).get("first_name") or str(target_id)
    perms = set(a.get("permissions") or [])
    # SUPER / OWNER logical: show all on
    role = str(a.get("role") or "ADMIN").upper()
    lines = [
        f"🛡 **دسترسی‌های ادمین**",
        f"👤 {name} (`{target_id}`)",
        f"نقش: `{role}` | {'🟢 فعال' if a.get('enabled', True) else '🔴 خاموش'}",
        "━━━━━━━━━━━━━━",
        "روی هر مورد بزن تا **روشن ⇄ خاموش** شود:",
    ]
    rows = []
    for key, label in PERM_META:
        on = key in perms or "*" in perms or role in ("OWNER", "SUPER_ADMIN")
        # برای SUPER_ADMIN اگر لیست خالی است همه را روشن فرض نکن مگر واقعاً در DB باشد
        if role == "SUPER_ADMIN" and not perms:
            on = True
        if role == "OWNER":
            on = True
        mark = "✅" if on else "❌"
        # toggle only if not OWNER role in DB (config owner handled separately)
        if role == "OWNER":
            rows.append([(f"{mark} {label}", "ap:noop")])
        else:
            rows.append([(f"{mark} {label}", f"ap:toggle:{target_id}:{key}")])
    rows.append([
        ("✅ همه روشن", f"ap:allon:{target_id}"),
        ("❌ همه خاموش", f"ap:alloff:{target_id}"),
    ])
    rows.append([("🔙 لیست ادمین", "ap:list"), ("🔙 Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def toggle_perm(target_id: int, perm: str, actor_id: int):
    if not await is_owner(actor_id):
        # فقط owner می‌تواند دسترسی عوض کند مگر admins.manage
        if not await has_permission(actor_id, "admins.manage"):
            return "⛔ فقط Owner یا کسی با مجوز مدیریت ادمین.", _kb([[("🔙", "ap:list")]])
    a = await get_admin(target_id)
    if not a:
        return "❌ ادمین نیست.", _kb([[("🔙", "ap:list")]])
    if str(a.get("role") or "").upper() == "OWNER":
        return "⛔ دسترسی Owner قابل تغییر از اینجا نیست.", await admin_perms_card(target_id)

    perms = list(a.get("permissions") or [])
    # اگر SUPER_ADMIN با لیست خالی بود، اول همه را بریز
    role = str(a.get("role") or "").upper()
    if role == "SUPER_ADMIN" and not perms:
        perms = [k for k, _ in PERM_META]

    if perm in perms:
        perms = [p for p in perms if p != perm]
    else:
        perms.append(perm)
    # حذف *
    perms = [p for p in perms if p != "*"]
    await update_admin_permissions(target_id, perms)
    try:
        await log_action(actor_id, "perm_toggle", str(target_id), {"perm": perm, "perms": perms})
    except Exception:
        pass
    return await admin_perms_card(target_id)


async def set_all_perms(target_id: int, on: bool, actor_id: int):
    if not await is_owner(actor_id) and not await has_permission(actor_id, "admins.manage"):
        return "⛔ دسترسی ندارید.", _kb([[("🔙", "ap:list")]])
    a = await get_admin(target_id)
    if not a or str(a.get("role") or "").upper() == "OWNER":
        return "❌", _kb([[("🔙", "ap:list")]])
    perms = [k for k, _ in PERM_META] if on else []
    await update_admin_permissions(target_id, perms)
    try:
        await log_action(actor_id, "perm_all", str(target_id), {"on": on})
    except Exception:
        pass
    return await admin_perms_card(target_id)


async def handle_ap_callback(data: str, actor_id: int):
    parts = data.split(":")
    # ap:list | ap:view:UID | ap:toggle:UID:perm | ap:allon:UID | ap:alloff:UID
    cmd = parts[1] if len(parts) > 1 else "list"
    if cmd == "list":
        return await admins_list_text()
    if cmd == "noop":
        return "این مورد قفل است.", _kb([[("🔙", "ap:list")]])
    if cmd == "view" and len(parts) > 2:
        return await admin_perms_card(int(parts[2]))
    if cmd == "toggle" and len(parts) > 3:
        return await toggle_perm(int(parts[2]), parts[3], actor_id)
    if cmd == "allon" and len(parts) > 2:
        return await set_all_perms(int(parts[2]), True, actor_id)
    if cmd == "alloff" and len(parts) > 2:
        return await set_all_perms(int(parts[2]), False, actor_id)
    return await admins_list_text()


# ---------- enforcement helpers ----------
async def require_perm(user_id: int, perm: str) -> bool:
    """Owner همیشه True."""
    from database.admins import is_owner as _io
    if await _io(user_id):
        return True
    return await has_permission(user_id, perm)
