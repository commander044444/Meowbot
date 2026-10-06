# ==========================================
# Owner: Task / Role / Promotion management
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.admin_system import (
    list_tasks, get_task, update_task, set_task_enabled, create_task,
    list_role_defs, update_role_def, list_promotion_requests, review_promotion,
    admin_leaderboard, recent_admin_activity, ensure_admin_system_schema,
)
from database.logs import log_action

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


def back_owner():
    return _kb([[("🔙 منوی Owner", "owner:home")]])


async def tasks_home():
    await ensure_admin_system_schema()
    tasks = await list_tasks(False)
    lines = [
        "🎯 **مدیریت تسک‌های ادمین**",
        "━━━━━━━━━━━━━━",
        "Built-in و سفارشی. Target و Reward قابل تغییر است.",
    ]
    rows = []
    for t in tasks or []:
        en = "🟢" if t.get("enabled") else "⏸"
        builtin = "📦" if t.get("is_builtin") else "✨"
        rows.append([(
            f"{en}{builtin} {t.get('name')} [{t.get('progress') if False else t.get('target')}]",
            f"ot:view:{t['id']}",
        )])
    rows.append([("➕ تسک جدید", "ot:create")])
    rows.append([("🎖️ نقش‌ها", "ot:roles"), ("📨 درخواست ارتقا", "ot:promos")])
    rows.append([("🏅 لیدربورد", "ot:lb"), ("📊 فعالیت ادمین‌ها", "ot:acts")])
    rows.append([("🔙 Owner", "owner:home")])
    return "\n".join(lines), _kb(rows)


async def view_task(task_id: int):
    t = await get_task(task_id)
    if not t:
        return "❌ تسک پیدا نشد.", await tasks_home()
    text = (
        f"🎯 **{t.get('name')}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"کلید: `{t.get('task_key')}`\n"
        f"توضیح: {t.get('description') or '—'}\n"
        f"Activity: `{t.get('activity_type')}`\n"
        f"🎯 Target: `{t.get('target')}`\n"
        f"⭐ XP: `{t.get('xp_reward')}` | 🪙 Meow: `{t.get('meow_reward')}`\n"
        f"🔐 Permission: `{t.get('required_permission') or '—'}`\n"
        f"🔁 Repeat: `{t.get('repeat_type')}`\n"
        f"وضعیت: {'🟢 ON' if t.get('enabled') else '⏸ OFF'}\n"
        f"Built-in: `{t.get('is_builtin')}`"
    )
    tid = t["id"]
    kb = _kb([
        [("🎯 Target", f"ot:set:{tid}:target"), ("⭐ XP", f"ot:set:{tid}:xp")],
        [("🪙 Meow", f"ot:set:{tid}:meow"), ("🔐 Perm", f"ot:set:{tid}:perm")],
        [("▶️ Enable" if not t.get("enabled") else "⏸ Disable", f"ot:toggle:{tid}")],
        [("🗑 حذف", f"ot:del:{tid}")] if not t.get("is_builtin") else [],
        [("🔙 تسک‌ها", "ot:home")],
    ])
    return text, kb


async def handle_ot_callback(bot, data: str, owner_id: int):
    parts = data.split(":")
    cmd = parts[1] if len(parts) > 1 else "home"

    if cmd == "home":
        return await tasks_home()
    if cmd == "view" and len(parts) > 2:
        return await view_task(int(parts[2]))
    if cmd == "toggle" and len(parts) > 2:
        tid = int(parts[2])
        t = await get_task(tid)
        if not t:
            return "❌", await tasks_home()
        await set_task_enabled(tid, not bool(t.get("enabled")))
        await log_action(owner_id, "task_toggle", str(tid), {"enabled": not t.get("enabled")})
        return await view_task(tid)
    if cmd == "del" and len(parts) > 2:
        await update_task  # noqa — use delete
        from database.admin_system import delete_task
        await delete_task(int(parts[2]))
        return await tasks_home()
    if cmd == "set" and len(parts) > 3:
        tid, field = int(parts[2]), parts[3]
        _pending[owner_id] = {"action": "ot_set", "task_id": tid, "field": field}
        hints = {
            "target": "عدد Target جدید را بفرست:",
            "xp": "مقدار XP Reward را بفرست:",
            "meow": "مقدار Meow Reward را بفرست:",
            "perm": "کلید Permission را بفرست (مثلاً tickets.manage) یا `-` برای خالی:",
        }
        return hints.get(field, "مقدار را بفرست:"), _kb([[("❌ لغو", f"ot:view:{tid}")]])
    if cmd == "create":
        _pending[owner_id] = {"action": "ot_create"}
        return (
            "➕ **تسک جدید**\n"
            "فرمت:\n"
            "`key | نام | activity_type | target | xp | meow | permission`\n\n"
            "مثال:\n"
            "`custom_ban | بن ویژه | user_ban | 5 | 100 | 200 | users.ban`",
            _kb([[("❌ لغو", "ot:home")]]),
        )
    if cmd == "roles":
        roles = await list_role_defs()
        lines = ["🎖️ **نقش‌های ادمین**", "━━━━━━━━━━━━━━"]
        rows = []
        for r in roles:
            lines.append(
                f"**{r.get('title')}** (`{r.get('role_key')}`)\n"
                f"XP `{r.get('required_xp')}` | تسک `{r.get('required_tasks')}` | "
                f"فعالیت `{r.get('required_activity')}` | پاداش `{r.get('reward_meow')}`🪙\n"
                f"Auto: `{r.get('auto_upgrade')}` | Approval: `{r.get('needs_owner_approval')}`"
            )
            rows.append([(f"✏️ {r.get('title')}", f"ot:role:{r['role_key']}")])
        rows.append([("🔙", "ot:home")])
        return "\n".join(lines), _kb(rows)
    if cmd == "role" and len(parts) > 2:
        rk = parts[2]
        _pending[owner_id] = {"action": "ot_role", "role_key": rk}
        return (
            f"ویرایش نقش `{rk}`\n"
            "فرمت:\n"
            "`required_xp | required_tasks | required_activity | reward_meow | auto(0/1) | approval(0/1)`\n"
            "مثال: `1000 | 5 | 20 | 1000 | 1 | 0`",
            _kb([[("❌ لغو", "ot:roles")]]),
        )
    if cmd == "promos":
        reqs = await list_promotion_requests("pending")
        lines = ["📨 **درخواست ارتقا**", "━━━━━━━━━━━━━━"]
        rows = []
        if not reqs:
            lines.append("موردی نیست.")
        for r in reqs:
            lines.append(
                f"#{r['id']} admin `{r['admin_id']}`: "
                f"{r.get('from_role')} → **{r.get('to_role')}**"
            )
            rows.append([
                (f"✅ #{r['id']}", f"ot:promo_ok:{r['id']}"),
                (f"❌ #{r['id']}", f"ot:promo_no:{r['id']}"),
            ])
        rows.append([("🔙", "ot:home")])
        return "\n".join(lines), _kb(rows)
    if cmd == "promo_ok" and len(parts) > 2:
        await review_promotion(int(parts[2]), owner_id, True)
        return "✅ تأیید شد.", await handle_ot_callback(bot, "ot:promos", owner_id)
    if cmd == "promo_no" and len(parts) > 2:
        await review_promotion(int(parts[2]), owner_id, False)
        return "رد شد.", await handle_ot_callback(bot, "ot:promos", owner_id)
    if cmd == "lb":
        rows = await admin_leaderboard(20, "all")
        lines = ["🏅 لیدربورد ادمین", "━━━━━━━━━━━━━━"]
        for i, r in enumerate(rows or []):
            lines.append(f"{i+1}. {r.get('first_name') or r.get('user_id')} — XP `{r.get('admin_xp')}`")
        return "\n".join(lines), _kb([[("🔙", "ot:home")]])
    if cmd == "acts":
        acts = await recent_admin_activity(None, 25)
        lines = ["📊 فعالیت ادمین‌ها", "━━━━━━━━━━━━━━"]
        for a in acts or []:
            lines.append(f"`{a.get('admin_id')}` {a.get('action')} → {a.get('target')}")
        return "\n".join(lines), _kb([[("🔙", "ot:home")]])
    return await tasks_home()


async def handle_ot_text(bot, message, owner_id: int, text: str) -> bool:
    p = _pending.get(owner_id)
    if not p:
        return False
    text = (text or "").strip()
    if text in ("لغو", "cancel", "/cancel"):
        _pending.pop(owner_id, None)
        await message.reply("لغو شد.")
        return True

    if p.get("action") == "ot_set":
        tid, field = p["task_id"], p["field"]
        try:
            if field == "target":
                await update_task(tid, target=max(1, int(text)))
            elif field == "xp":
                await update_task(tid, xp_reward=max(0, int(text)))
            elif field == "meow":
                await update_task(tid, meow_reward=max(0, int(text)))
            elif field == "perm":
                await update_task(tid, required_permission="" if text == "-" else text.strip())
            await log_action(owner_id, "task_edit", str(tid), {"field": field, "value": text})
            _pending.pop(owner_id, None)
            from admin.owner_tasks import view_task
            card, kb = await view_task(tid)
            await message.reply(f"✅ ذخیره شد.\n\n{card}", components=kb)
        except Exception as e:
            await message.reply(f"❌ `{e}`")
        return True

    if p.get("action") == "ot_create":
        parts = [x.strip() for x in text.split("|")]
        if len(parts) < 4:
            await message.reply("❌ فرمت ناقص.")
            return True
        key, name, activity = parts[0], parts[1], parts[2]
        target = int(parts[3]) if len(parts) > 3 else 1
        xp = int(parts[4]) if len(parts) > 4 else 0
        meow = int(parts[5]) if len(parts) > 5 else 0
        perm = parts[6] if len(parts) > 6 else ""
        t = await create_task(
            task_key=key, name=name, activity_type=activity,
            target=target, xp_reward=xp, meow_reward=meow,
            required_permission=perm, enabled=True, created_by=owner_id,
        )
        _pending.pop(owner_id, None)
        await message.reply(f"✅ تسک ساخته شد: **{t.get('name')}** (id `{t.get('id')}`)")
        return True

    if p.get("action") == "ot_role":
        rk = p["role_key"]
        parts = [x.strip() for x in text.split("|")]
        try:
            await update_role_def(
                rk,
                required_xp=int(parts[0]),
                required_tasks=int(parts[1]) if len(parts) > 1 else 0,
                required_activity=int(parts[2]) if len(parts) > 2 else 0,
                reward_meow=int(parts[3]) if len(parts) > 3 else 0,
                auto_upgrade=bool(int(parts[4])) if len(parts) > 4 else True,
                needs_owner_approval=bool(int(parts[5])) if len(parts) > 5 else False,
            )
            _pending.pop(owner_id, None)
            await message.reply(f"✅ نقش `{rk}` به‌روز شد.")
        except Exception as e:
            await message.reply(f"❌ `{e}`")
        return True

    return False


def has_ot_pending(owner_id: int) -> bool:
    return owner_id in _pending
