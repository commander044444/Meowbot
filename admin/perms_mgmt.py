# ==========================================
# Owner: Admin Management + Permissions + Roles
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.admins import (
    list_admins, get_admin, update_admin_permissions,
    ALL_PERMISSIONS, has_permission, is_owner,
)
from database.admin_system import (
    ensure_admin_profile, get_admin_profile, list_role_defs, get_role_def,
    update_role_def, assign_role_manual, soft_remove_admin, get_role_history,
    set_manual_permission_override, ensure_admin_system_schema,
)
from database.logs import log_action
from database.users import get_user
from config import OWNER_ID

PERM_META = [
    ("users.view", "👁 مشاهده کاربران"),
    ("users.edit", "✏️ ویرایش سکه/امتیاز"),
    ("users.ban", "🚫 بن"),
    ("users.unban", "✅ آنبن"),
    ("reports.view", "🚨 مشاهده گزارش"),
    ("reports.manage", "🚨 مدیریت گزارش"),
    ("tickets.view", "🎫 مشاهده تیکت"),
    ("tickets.manage", "🎫 مدیریت تیکت"),
    ("groups.view", "💬 مشاهده گروه‌ها"),
    ("groups.edit", "⚙️ تنظیم گروه‌ها"),
    ("economy.view", "💰 مشاهده اقتصاد"),
    ("economy.edit", "💸 اقتصاد سراسری"),
    ("broadcast.view", "📢 مشاهده همگانی"),
    ("broadcast.send", "📢 ارسال همگانی"),
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
    ("tasks.view", "📋 مشاهده تسک"),
    ("tasks.manage", "📋 مدیریت تسک"),
    ("leaderboard.view", "🏅 لیدربورد"),
    ("admin_activity.view", "📊 فعالیت ادمین"),
    ("database.backup", "💾 بکاپ"),
    ("database.restore", "♻️ ریستور"),
    ("settings.manage", "⚙️ تنظیمات"),
    ("maintenance.manage", "🚧 Maintenance"),
]

for key, _ in PERM_META:
    if key not in ALL_PERMISSIONS:
        ALL_PERMISSIONS.append(key)

_pending = {}


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
    try:
        await ensure_admin_system_schema()
    except Exception:
        pass
    admins = await list_admins()
    lines = [
        "🛡 **مدیریت ادمین‌ها**",
        "━━━━━━━━━━━━━━",
        "یک ادمین را انتخاب کن:",
    ]
    rows = []
    if not admins:
        lines.append("ادمینی ثبت نشده.")
    for a in admins or []:
        uid = int(a["user_id"])
        if uid == int(OWNER_ID):
            continue  # Owner را در لیست ادمین نشان نده برای حذف تصادفی
        role = a.get("role") or "ADMIN"
        en = "🟢" if a.get("enabled", True) else "🔴"
        u = await get_user(uid)
        name = (u or {}).get("first_name") or str(uid)
        prof = await get_admin_profile(uid)
        pr = (prof or {}).get("role_key") or "—"
        st = (prof or {}).get("status") or "active"
        mark = "🗑" if st == "removed" else en
        rows.append([(f"{mark} {name} | {pr}", f"ap:view:{uid}")])
    rows.append([("🎖️ Role Management", "ap:roles")])
    rows.append([("➕ افزودن ادمین", "owner:admin_add")])
    rows.append([("🔙 منوی Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def admin_perms_card(target_id: int):
    a = await get_admin(target_id)
    u = await get_user(target_id)
    name = (u or {}).get("first_name") or str(target_id)
    uname = (u or {}).get("username") or "—"
    prof = await ensure_admin_profile(target_id)
    status = (prof or {}).get("status") or "active"
    role_key = (prof or {}).get("role_key") or "candidate"
    role = await get_role_def(role_key)
    role_title = (role or {}).get("title") or role_key

    if not a and status != "removed":
        return "❌ این کاربر ادمین فعال نیست.", _kb([[("🔙", "ap:list")]])

    perms = set((a or {}).get("permissions") or [])
    lines = [
        f"🛡 **کارت ادمین**",
        f"👤 {name} (@{uname})",
        f"آیدی: `{target_id}`",
        f"Status: `{status}`",
        f"🎖️ Role: **{role_title}** (`{role_key}`)",
        f"⭐ Admin XP: `{prof.get('admin_xp') or 0}`",
        f"✅ تسک: `{prof.get('completed_tasks') or 0}`",
        f"📊 فعالیت: `{prof.get('activity_count') or 0}`",
        "━━━━━━━━━━━━━━",
        "دسترسی‌ها (روشن/خاموش):",
    ]
    rows = []
    if a and status != "removed":
        for key, label in PERM_META:
            on = key in perms or "*" in perms
            mark = "✅" if on else "❌"
            rows.append([(f"{mark} {label}", f"ap:toggle:{target_id}:{key}")])
        rows.append([
            ("✅ همه روشن", f"ap:allon:{target_id}"),
            ("❌ همه خاموش", f"ap:alloff:{target_id}"),
        ])
        rows.append([("🎖️ Change Role", f"ap:rolemenu:{target_id}")])
        rows.append([("📜 Role History", f"ap:history:{target_id}")])
        rows.append([("🗑 Remove Admin", f"ap:rmask:{target_id}")])
    else:
        lines.append("⚠️ این ادمین حذف شده — سابقه حفظ شده است.")
        rows.append([("📜 Role History", f"ap:history:{target_id}")])

    rows.append([("🔙 لیست ادمین", "ap:list"), ("🔙 Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def toggle_perm(target_id: int, perm: str, actor_id: int):
    if not await is_owner(actor_id) and not await has_permission(actor_id, "admins.manage"):
        return "⛔ دسترسی ندارید.", _kb([[("🔙", "ap:list")]])
    if int(target_id) == int(OWNER_ID):
        return "⛔ Owner.", _kb([[("🔙", "ap:list")]])
    a = await get_admin(target_id)
    if not a:
        return "❌ ادمین نیست.", _kb([[("🔙", "ap:list")]])

    perms = list(a.get("permissions") or [])
    if perm in perms:
        perms = [p for p in perms if p != perm]
    else:
        perms.append(perm)
    perms = [p for p in perms if p != "*"]
    await update_admin_permissions(target_id, perms)
    # manual override snapshot
    try:
        await set_manual_permission_override(target_id, perms)
    except Exception:
        pass
    try:
        await log_action(actor_id, "perm_toggle", str(target_id), {"perm": perm})
    except Exception:
        pass
    return await admin_perms_card(target_id)


async def set_all_perms(target_id: int, on: bool, actor_id: int):
    if not await is_owner(actor_id) and not await has_permission(actor_id, "admins.manage"):
        return "⛔", _kb([[("🔙", "ap:list")]])
    a = await get_admin(target_id)
    if not a:
        return "❌", _kb([[("🔙", "ap:list")]])
    perms = [k for k, _ in PERM_META] if on else []
    await update_admin_permissions(target_id, perms)
    try:
        await set_manual_permission_override(target_id, perms)
    except Exception:
        pass
    return await admin_perms_card(target_id)


async def role_menu(target_id: int):
    roles = await list_role_defs()
    u = await get_user(target_id)
    name = (u or {}).get("first_name") or str(target_id)
    prof = await get_admin_profile(target_id)
    cur = (prof or {}).get("role_key") or "candidate"
    lines = [
        f"🎖️ **تغییر Role**",
        f"کاربر: {name} (`{target_id}`)",
        f"فعلی: `{cur}`",
        "━━━━━━━━━━━━━━",
        "Role جدید را انتخاب کن:",
    ]
    rows = []
    for r in roles:
        mark = "👉" if r["role_key"] == cur else "○"
        title = r.get("title") or r["role_key"]
        rows.append([(f"{mark} {title}", f"ap:roleask:{target_id}:{r['role_key']}")])
    rows.append([("🔙", f"ap:view:{target_id}")])
    return "\n".join(lines), _kb(rows)


async def role_confirm(target_id: int, role_key: str):
    u = await get_user(target_id)
    name = (u or {}).get("first_name") or str(target_id)
    role = await get_role_def(role_key)
    title = (role or {}).get("title") or role_key
    warn = ""
    if role_key == "super_admin":
        warn = "\n\n⚠️ **Super Admin دسترسی بسیار بالایی دارد.**"
    text = (
        f"⚠️ **تأیید تغییر Role**\n"
        f"━━━━━━━━━━━━━━\n"
        f"Admin: {name}\n"
        f"Role جدید: **{title}** (`{role_key}`)"
        f"{warn}\n\n"
        f"نوع: Manual Assignment"
    )
    return text, _kb([
        [("✅ Confirm", f"ap:roledo:{target_id}:{role_key}"), ("❌ لغو", f"ap:view:{target_id}")],
    ])


async def remove_ask(target_id: int):
    u = await get_user(target_id)
    name = (u or {}).get("first_name") or str(target_id)
    uname = (u or {}).get("username") or "—"
    prof = await get_admin_profile(target_id)
    role_key = (prof or {}).get("role_key") or "—"
    role = await get_role_def(role_key)
    title = (role or {}).get("title") or role_key
    text = (
        f"⚠️ **حذف Admin**\n"
        f"━━━━━━━━━━━━━━\n"
        f"Admin: {name} (@{uname})\n"
        f"آیدی: `{target_id}`\n"
        f"Role: **{title}**\n\n"
        f"دسترسی فوراً قطع می‌شود.\n"
        f"سابقه Activity و Logs **حفظ** می‌شود.\n\n"
        f"آیا مطمئنی؟"
    )
    return text, _kb([
        [("🗑 حذف Admin", f"ap:rmdo:{target_id}"), ("❌ لغو", f"ap:view:{target_id}")],
    ])


async def roles_management_home():
    roles = await list_role_defs()
    lines = [
        "🎖️ **Role Management**",
        "━━━━━━━━━━━━━━",
        "ID داخلی ثابت است؛ فقط نام نمایشی تغییر می‌کند.",
    ]
    rows = []
    for r in roles:
        icon = r.get("icon") or "🎖️"
        lines.append(
            f"{icon} **{r.get('title')}**\n"
            f"  ID: `{r.get('role_key')}`\n"
            f"  XP `{r.get('required_xp')}` | تسک `{r.get('required_tasks')}` | "
            f"پاداش `{r.get('reward_meow')}`🪙"
        )
        rows.append([(f"✏️ {r.get('title')}", f"ap:roleedit:{r['role_key']}")])
    rows.append([("🔙 لیست ادمین", "ap:list")])
    return "\n".join(lines), _kb(rows)


async def role_edit_card(role_key: str):
    r = await get_role_def(role_key)
    if not r:
        return "❌ Role پیدا نشد.", _kb([[("🔙", "ap:roles")]])
    text = (
        f"🎖️ **{r.get('title')}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"Internal ID: `{r.get('role_key')}` _(ثابت)_\n"
        f"نام نمایشی: **{r.get('title')}**\n"
        f"توضیح: {r.get('description') or '—'}\n"
        f"آیکون: {r.get('icon') or '—'}\n"
        f"Required XP: `{r.get('required_xp')}`\n"
        f"Required Tasks: `{r.get('required_tasks')}`\n"
        f"Required Activity: `{r.get('required_activity')}`\n"
        f"Meow Reward: `{r.get('reward_meow')}`\n"
        f"XP Reward: `{r.get('xp_reward') or 0}`\n"
        f"Auto Promotion: `{r.get('auto_upgrade')}`\n"
        f"Owner Approval: `{r.get('needs_owner_approval')}`"
    )
    kb = _kb([
        [("✏️ نام", f"ap:rset:{role_key}:title"), ("📝 توضیح", f"ap:rset:{role_key}:description")],
        [("⭐ XP لازم", f"ap:rset:{role_key}:required_xp"), ("📋 تسک لازم", f"ap:rset:{role_key}:required_tasks")],
        [("📊 فعالیت لازم", f"ap:rset:{role_key}:required_activity"), ("🪙 پاداش", f"ap:rset:{role_key}:reward_meow")],
        [("🤖 Auto ON/OFF", f"ap:rautotog:{role_key}"), ("🔐 Approval ON/OFF", f"ap:rapprovtog:{role_key}")],
        [("🔙 نقش‌ها", "ap:roles")],
    ])
    return text, kb


async def handle_ap_callback(data: str, actor_id: int):
    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "list"

    if not await is_owner(actor_id) and not await has_permission(actor_id, "admins.manage"):
        # فقط owner برای بیشتر عملیات
        if not await is_owner(actor_id):
            return "⛔ فقط Owner.", _kb([[("🔙", "owner:home")]])

    if cmd == "list":
        return await admins_list_text()
    if cmd == "noop":
        return "قفل است.", _kb([[("🔙", "ap:list")]])
    if cmd == "view" and len(parts) > 2:
        return await admin_perms_card(int(parts[2]))
    if cmd == "toggle" and len(parts) > 3:
        return await toggle_perm(int(parts[2]), parts[3], actor_id)
    if cmd == "allon" and len(parts) > 2:
        return await set_all_perms(int(parts[2]), True, actor_id)
    if cmd == "alloff" and len(parts) > 2:
        return await set_all_perms(int(parts[2]), False, actor_id)

    if cmd == "rolemenu" and len(parts) > 2:
        return await role_menu(int(parts[2]))
    if cmd == "roleask" and len(parts) > 3:
        return await role_confirm(int(parts[2]), parts[3])
    if cmd == "roledo" and len(parts) > 3:
        if not await is_owner(actor_id):
            return "⛔ فقط Owner.", _kb([[("🔙", "ap:list")]])
        tid, rk = int(parts[2]), parts[3]
        ok, msg = await assign_role_manual(tid, rk, actor_id, "manual by owner")
        if not ok:
            return f"❌ {msg}", _kb([[("🔙", f"ap:view:{tid}")]])
        card, kb = await admin_perms_card(tid)
        return f"✅ Role تغییر کرد (Manual Assignment).\n\n{card}", kb

    if cmd == "rmask" and len(parts) > 2:
        if not await is_owner(actor_id):
            return "⛔ فقط Owner.", _kb([[("🔙", "ap:list")]])
        return await remove_ask(int(parts[2]))
    if cmd == "rmdo" and len(parts) > 2:
        if not await is_owner(actor_id):
            return "⛔ فقط Owner.", _kb([[("🔙", "ap:list")]])
        tid = int(parts[2])
        ok, msg = await soft_remove_admin(tid, actor_id, "removed from owner panel")
        if not ok:
            return f"❌ {msg}", _kb([[("🔙", "ap:list")]])
        return (
            f"✅ Admin `{tid}` حذف شد.\n"
            f"Status: **Removed**\n"
            f"دیگر `/admin` باز نمی‌شود.\n"
            f"سابقه Activity حفظ شده است.",
            _kb([[("🔙 لیست", "ap:list")]]),
        )

    if cmd == "history" and len(parts) > 2:
        tid = int(parts[2])
        hist = await get_role_history(tid, 15)
        lines = [f"📜 **Role History** `{tid}`", "━━━━━━━━━━━━━━"]
        if not hist:
            lines.append("سابقه‌ای نیست.")
        for h in hist:
            lines.append(
                f"• {h.get('old_role')} → **{h.get('new_role')}**\n"
                f"  type: `{h.get('change_type')}` by `{h.get('changed_by')}`\n"
                f"  {h.get('created_at')}"
            )
        return "\n".join(lines), _kb([[("🔙", f"ap:view:{tid}")]])

    if cmd == "roles":
        return await roles_management_home()
    if cmd == "roleedit" and len(parts) > 2:
        return await role_edit_card(parts[2])
    if cmd == "rset" and len(parts) > 3:
        if not await is_owner(actor_id):
            return "⛔ فقط Owner.", _kb([[("🔙", "ap:roles")]])
        rk, field = parts[2], parts[3]
        _pending[actor_id] = {"action": "role_field", "role_key": rk, "field": field}
        hints = {
            "title": "نام نمایشی جدید Role را بفرست (ID داخلی ثابت می‌ماند):",
            "description": "توضیح Role را بفرست:",
            "required_xp": "Required XP (عدد):",
            "required_tasks": "Required Tasks (عدد):",
            "required_activity": "Required Activity (عدد):",
            "reward_meow": "Meow Reward (عدد):",
        }
        return hints.get(field, "مقدار را بفرست:"), _kb([[("❌ لغو", f"ap:roleedit:{rk}")]])
    if cmd == "rautotog" and len(parts) > 2:
        if not await is_owner(actor_id):
            return "⛔", _kb([[("🔙", "ap:roles")]])
        r = await get_role_def(parts[2])
        await update_role_def(parts[2], auto_upgrade=not bool(r.get("auto_upgrade", True)))
        return await role_edit_card(parts[2])
    if cmd == "rapprovtog" and len(parts) > 2:
        if not await is_owner(actor_id):
            return "⛔", _kb([[("🔙", "ap:roles")]])
        r = await get_role_def(parts[2])
        await update_role_def(parts[2], needs_owner_approval=not bool(r.get("needs_owner_approval")))
        return await role_edit_card(parts[2])

    return await admins_list_text()


async def handle_ap_text(message, actor_id: int, text: str) -> bool:
    p = _pending.get(actor_id)
    if not p:
        return False
    text = (text or "").strip()
    if text in ("لغو", "cancel"):
        _pending.pop(actor_id, None)
        await message.reply("لغو شد.")
        return True
    if p.get("action") == "role_field":
        rk, field = p["role_key"], p["field"]
        try:
            if field in ("required_xp", "required_tasks", "required_activity", "reward_meow", "xp_reward"):
                await update_role_def(rk, **{field: int(text)})
            elif field == "title":
                # rename display only — role_key ثابت
                await update_role_def(rk, title=text[:64])
            elif field == "description":
                await update_role_def(rk, description=text[:500])
            elif field == "icon":
                await update_role_def(rk, icon=text[:8])
            _pending.pop(actor_id, None)
            card, kb = await role_edit_card(rk)
            await message.reply(f"✅ ذخیره شد.\n\n{card}", components=kb)
        except Exception as e:
            await message.reply(f"❌ `{e}`")
        return True
    return False


def has_ap_pending(actor_id: int) -> bool:
    return actor_id in _pending


async def require_perm(user_id: int, perm: str) -> bool:
    if await is_owner(user_id):
        return True
    return await has_permission(user_id, perm)
