# ==========================================
# Admin System: XP, Roles, Tasks, Activity (real PostgreSQL)
# ==========================================

from datetime import datetime, timezone
from .pool import fetch, fetchrow, execute, fetchval
import json


def _d(row):
    return dict(row) if row else None


# ---------- Schema bootstrap ----------
ADMIN_SYSTEM_SQL = """
CREATE TABLE IF NOT EXISTS admin_profiles (
    user_id         BIGINT PRIMARY KEY,
    role_key        TEXT DEFAULT 'candidate',
    admin_xp        INTEGER DEFAULT 0,
    activity_count  INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    streak          INTEGER DEFAULT 0,
    last_activity   TIMESTAMPTZ DEFAULT NULL,
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_role_defs (
    role_key            TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    required_xp         INTEGER DEFAULT 0,
    required_tasks      INTEGER DEFAULT 0,
    required_activity   INTEGER DEFAULT 0,
    reward_meow         INTEGER DEFAULT 0,
    auto_upgrade        BOOLEAN DEFAULT TRUE,
    needs_owner_approval BOOLEAN DEFAULT FALSE,
    sort_order          INTEGER DEFAULT 0,
    enabled             BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS admin_tasks (
    id                  SERIAL PRIMARY KEY,
    task_key            TEXT UNIQUE,
    name                TEXT NOT NULL,
    description         TEXT DEFAULT '',
    category            TEXT DEFAULT 'general',
    activity_type       TEXT NOT NULL,
    target              INTEGER DEFAULT 1,
    xp_reward           INTEGER DEFAULT 0,
    meow_reward         INTEGER DEFAULT 0,
    required_role       TEXT DEFAULT '',
    required_permission TEXT DEFAULT '',
    repeat_type         TEXT DEFAULT 'permanent',
    cooldown_hours      INTEGER DEFAULT 0,
    enabled             BOOLEAN DEFAULT TRUE,
    is_builtin          BOOLEAN DEFAULT FALSE,
    assign_mode         TEXT DEFAULT 'global',
    assign_target       TEXT DEFAULT '',
    start_at            TIMESTAMPTZ DEFAULT NULL,
    end_at              TIMESTAMPTZ DEFAULT NULL,
    created_by          BIGINT DEFAULT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_task_progress (
    admin_id        BIGINT NOT NULL,
    task_id         INTEGER NOT NULL REFERENCES admin_tasks(id) ON DELETE CASCADE,
    progress        INTEGER DEFAULT 0,
    completed       BOOLEAN DEFAULT FALSE,
    completed_at    TIMESTAMPTZ DEFAULT NULL,
    period_key      TEXT DEFAULT 'all',
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (admin_id, task_id, period_key)
);

CREATE TABLE IF NOT EXISTS admin_task_completions (
    id              SERIAL PRIMARY KEY,
    admin_id        BIGINT NOT NULL,
    task_id         INTEGER NOT NULL,
    unique_key      TEXT NOT NULL,
    xp_earned       INTEGER DEFAULT 0,
    meow_earned     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (admin_id, task_id, unique_key)
);

CREATE TABLE IF NOT EXISTS admin_activity (
    id              SERIAL PRIMARY KEY,
    admin_id        BIGINT NOT NULL,
    action          TEXT NOT NULL,
    target          TEXT DEFAULT '',
    task_id         INTEGER DEFAULT NULL,
    xp_earned       INTEGER DEFAULT 0,
    meow_reward     INTEGER DEFAULT 0,
    result          TEXT DEFAULT 'ok',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_activity_admin ON admin_activity (admin_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_activity_action ON admin_activity (action, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_role_rewards_claimed (
    admin_id        BIGINT NOT NULL,
    role_key        TEXT NOT NULL,
    claimed_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (admin_id, role_key)
);

CREATE TABLE IF NOT EXISTS admin_notifications (
    id              SERIAL PRIMARY KEY,
    admin_id        BIGINT NOT NULL,
    kind            TEXT DEFAULT 'info',
    title           TEXT DEFAULT '',
    body            TEXT DEFAULT '',
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_notif_admin ON admin_notifications (admin_id, is_read, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_promotion_requests (
    id              SERIAL PRIMARY KEY,
    admin_id        BIGINT NOT NULL,
    from_role       TEXT DEFAULT '',
    to_role         TEXT NOT NULL,
    status          TEXT DEFAULT 'pending',
    reviewed_by     BIGINT DEFAULT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ DEFAULT NULL
);
"""


async def ensure_admin_system_schema():
    from .pool import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(ADMIN_SYSTEM_SQL)
    await seed_role_defs()
    await seed_builtin_tasks()


async def seed_role_defs():
    defaults = [
        ("candidate", "Candidate", 0, 0, 0, 0, True, False, 1),
        ("moderator", "Moderator", 1000, 5, 20, 1000, True, False, 2),
        ("admin", "Admin", 5000, 20, 100, 3000, True, False, 3),
        ("super_admin", "Super Admin", 15000, 50, 300, 10000, False, True, 4),
    ]
    for row in defaults:
        await execute(
            """
            INSERT INTO admin_role_defs (
                role_key, title, required_xp, required_tasks, required_activity,
                reward_meow, auto_upgrade, needs_owner_approval, sort_order
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (role_key) DO NOTHING
            """,
            *row,
        )


async def seed_builtin_tasks():
    builtins = [
        ("ticket_handle", "رسیدگی به تیکت‌ها", "بستن/پاسخ تیکت پشتیبانی", "tickets",
         "ticket_close", 10, 250, 500, "tickets.manage", "permanent", True),
        ("user_ban", "بن کاربران متخلف", "بن کردن کاربران", "moderation",
         "user_ban", 5, 150, 300, "users.ban", "permanent", True),
        ("user_unban", "آنبن کاربران", "برداشتن بن", "moderation",
         "user_unban", 3, 100, 200, "users.ban", "permanent", True),
        ("report_resolve", "حل گزارش‌ها", "بستن گزارش باگ/مشکل", "reports",
         "report_resolve", 5, 200, 400, "reports.manage", "permanent", True),
        ("admin_msg", "پیام به کاربران", "ارسال پیام شخصی مدیریتی", "support",
         "admin_msg", 10, 100, 200, "users.edit", "permanent", True),
    ]
    for b in builtins:
        await execute(
            """
            INSERT INTO admin_tasks (
                task_key, name, description, category, activity_type,
                target, xp_reward, meow_reward, required_permission,
                repeat_type, enabled, is_builtin
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,FALSE,$11)
            ON CONFLICT (task_key) DO NOTHING
            """,
            b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10],
        )


# ---------- Profile ----------
async def ensure_admin_profile(user_id: int):
    await execute(
        """
        INSERT INTO admin_profiles (user_id) VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING
        """,
        int(user_id),
    )
    return await get_admin_profile(user_id)


async def get_admin_profile(user_id: int):
    return _d(await fetchrow(
        "SELECT * FROM admin_profiles WHERE user_id = $1", int(user_id)
    ))


async def add_admin_xp(user_id: int, amount: int):
    await ensure_admin_profile(user_id)
    await execute(
        """
        UPDATE admin_profiles SET
            admin_xp = admin_xp + $2,
            last_activity = NOW(),
            updated_at = NOW()
        WHERE user_id = $1
        """,
        int(user_id), int(amount),
    )


async def bump_activity(user_id: int):
    await ensure_admin_profile(user_id)
    await execute(
        """
        UPDATE admin_profiles SET
            activity_count = activity_count + 1,
            last_activity = NOW(),
            updated_at = NOW()
        WHERE user_id = $1
        """,
        int(user_id),
    )


# ---------- Roles ----------
async def list_role_defs():
    rows = await fetch(
        "SELECT * FROM admin_role_defs WHERE enabled = TRUE ORDER BY sort_order"
    )
    return [_d(r) for r in rows]


async def get_role_def(role_key: str):
    return _d(await fetchrow(
        "SELECT * FROM admin_role_defs WHERE role_key = $1", role_key
    ))


async def update_role_def(role_key: str, **fields):
    allowed = {
        "title", "required_xp", "required_tasks", "required_activity",
        "reward_meow", "auto_upgrade", "needs_owner_approval", "enabled", "sort_order",
    }
    sets, args, i = [], [role_key], 2
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ${i}")
            args.append(v)
            i += 1
    if not sets:
        return
    await execute(
        f"UPDATE admin_role_defs SET {', '.join(sets)} WHERE role_key = $1",
        *args,
    )


# ---------- Tasks ----------
async def list_tasks(enabled_only: bool = False):
    if enabled_only:
        rows = await fetch(
            "SELECT * FROM admin_tasks WHERE enabled = TRUE ORDER BY id"
        )
    else:
        rows = await fetch("SELECT * FROM admin_tasks ORDER BY id")
    return [_d(r) for r in rows]


async def get_task(task_id: int):
    return _d(await fetchrow("SELECT * FROM admin_tasks WHERE id = $1", int(task_id)))


async def get_task_by_key(task_key: str):
    return _d(await fetchrow(
        "SELECT * FROM admin_tasks WHERE task_key = $1", task_key
    ))


async def create_task(**fields):
    row = await fetchrow(
        """
        INSERT INTO admin_tasks (
            task_key, name, description, category, activity_type,
            target, xp_reward, meow_reward, required_role, required_permission,
            repeat_type, cooldown_hours, enabled, is_builtin,
            assign_mode, assign_target, created_by
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17
        ) RETURNING *
        """,
        fields.get("task_key"),
        fields.get("name"),
        fields.get("description") or "",
        fields.get("category") or "general",
        fields.get("activity_type"),
        int(fields.get("target") or 1),
        int(fields.get("xp_reward") or 0),
        int(fields.get("meow_reward") or 0),
        fields.get("required_role") or "",
        fields.get("required_permission") or "",
        fields.get("repeat_type") or "permanent",
        int(fields.get("cooldown_hours") or 0),
        bool(fields.get("enabled", True)),
        bool(fields.get("is_builtin", False)),
        fields.get("assign_mode") or "global",
        fields.get("assign_target") or "",
        fields.get("created_by"),
    )
    return _d(row)


async def update_task(task_id: int, **fields):
    allowed = {
        "name", "description", "category", "activity_type", "target",
        "xp_reward", "meow_reward", "required_role", "required_permission",
        "repeat_type", "cooldown_hours", "enabled", "assign_mode", "assign_target",
    }
    sets, args, i = ["updated_at = NOW()"], [int(task_id)], 2
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ${i}")
            args.append(v)
            i += 1
    await execute(
        f"UPDATE admin_tasks SET {', '.join(sets)} WHERE id = $1", *args
    )
    return await get_task(task_id)


async def delete_task(task_id: int):
    await execute("DELETE FROM admin_tasks WHERE id = $1 AND is_builtin = FALSE", int(task_id))


async def set_task_enabled(task_id: int, enabled: bool):
    await execute(
        "UPDATE admin_tasks SET enabled = $2, updated_at = NOW() WHERE id = $1",
        int(task_id), bool(enabled),
    )


def _period_key(repeat_type: str) -> str:
    now = datetime.now(timezone.utc)
    rt = (repeat_type or "permanent").lower()
    if rt == "daily":
        return now.strftime("%Y-%m-%d")
    if rt == "weekly":
        return f"{now.year}-W{now.isocalendar()[1]}"
    if rt == "monthly":
        return now.strftime("%Y-%m")
    if rt == "season":
        return "season"
    return "all"


async def get_task_progress(admin_id: int, task_id: int, period_key: str = "all"):
    return _d(await fetchrow(
        """
        SELECT * FROM admin_task_progress
        WHERE admin_id = $1 AND task_id = $2 AND period_key = $3
        """,
        int(admin_id), int(task_id), period_key,
    ))


async def list_admin_task_progress(admin_id: int):
    """Enabled tasks + progress for this admin."""
    tasks = await list_tasks(enabled_only=True)
    result = []
    for t in tasks:
        # assignment filter
        mode = t.get("assign_mode") or "global"
        target = t.get("assign_target") or ""
        if mode == "individual" and str(target) != str(admin_id):
            continue
        if mode == "role":
            prof = await get_admin_profile(admin_id)
            if (prof or {}).get("role_key") != target:
                continue
        pk = _period_key(t.get("repeat_type"))
        prog = await get_task_progress(admin_id, t["id"], pk)
        progress = int((prog or {}).get("progress") or 0)
        completed = bool((prog or {}).get("completed"))
        result.append({**t, "progress": progress, "completed": completed, "period_key": pk})
    return result


# ---------- Activity + XP (idempotent) ----------
async def record_admin_activity(
    admin_id: int,
    action: str,
    target: str = "",
    unique_key: str = None,
    metadata: dict = None,
    result: str = "ok",
):
    """
    ثبت فعالیت واقعی + پیشرفت Taskهای مرتبط.
    unique_key برای anti-cheat (یک بار XP).
    """
    await ensure_admin_profile(admin_id)
    await bump_activity(admin_id)

    await execute(
        """
        INSERT INTO admin_activity (admin_id, action, target, result, metadata)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        int(admin_id), action, str(target or ""), result,
        json.dumps(metadata or {}, ensure_ascii=False),
    )

    # notify matching enabled tasks
    tasks = await fetch(
        "SELECT * FROM admin_tasks WHERE enabled = TRUE AND activity_type = $1",
        action,
    )
    total_xp = 0
    total_meow = 0
    for t in tasks:
        t = dict(t)
        mode = t.get("assign_mode") or "global"
        atarget = t.get("assign_target") or ""
        if mode == "individual" and str(atarget) != str(admin_id):
            continue
        if mode == "role":
            prof = await get_admin_profile(admin_id)
            if (prof or {}).get("role_key") != atarget:
                continue

        # permission gate
        req_perm = t.get("required_permission") or ""
        if req_perm:
            from database.admins import has_permission, is_owner
            if not await is_owner(admin_id) and not await has_permission(admin_id, req_perm):
                continue

        pk = _period_key(t.get("repeat_type"))
        ukey = unique_key or f"{action}:{target}:{t['id']}"

        # already counted this unique event for this task?
        exists = await fetchval(
            """
            SELECT 1 FROM admin_task_completions
            WHERE admin_id = $1 AND task_id = $2 AND unique_key = $3
            """,
            int(admin_id), int(t["id"]), ukey,
        )
        if exists:
            continue

        # once: if already completed period, skip
        prog = await get_task_progress(admin_id, t["id"], pk)
        if t.get("repeat_type") == "once" and prog and prog.get("completed"):
            continue

        new_progress = int((prog or {}).get("progress") or 0) + 1
        target_n = max(1, int(t.get("target") or 1))
        done = new_progress >= target_n

        await execute(
            """
            INSERT INTO admin_task_progress (admin_id, task_id, progress, completed, completed_at, period_key)
            VALUES ($1, $2, $3, $4, CASE WHEN $4 THEN NOW() ELSE NULL END, $5)
            ON CONFLICT (admin_id, task_id, period_key) DO UPDATE SET
                progress = EXCLUDED.progress,
                completed = EXCLUDED.completed,
                completed_at = CASE WHEN EXCLUDED.completed THEN COALESCE(admin_task_progress.completed_at, NOW()) ELSE admin_task_progress.completed_at END,
                updated_at = NOW()
            """,
            int(admin_id), int(t["id"]), new_progress, done, pk,
        )

        xp = 0
        meow = 0
        if done and not (prog and prog.get("completed")):
            xp = int(t.get("xp_reward") or 0)
            meow = int(t.get("meow_reward") or 0)
            if xp:
                await add_admin_xp(admin_id, xp)
            if meow:
                from database.users import add_meow_coins
                await add_meow_coins(admin_id, meow)
            await execute(
                """
                UPDATE admin_profiles SET
                    completed_tasks = completed_tasks + 1,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                int(admin_id),
            )
            await notify(
                admin_id,
                "task_completed",
                f"✅ تسک تکمیل شد: {t.get('name')}",
                f"+{xp} Admin XP | +{meow}🪙",
            )
            await maybe_promote(admin_id)

        await execute(
            """
            INSERT INTO admin_task_completions (admin_id, task_id, unique_key, xp_earned, meow_earned)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (admin_id, task_id, unique_key) DO NOTHING
            """,
            int(admin_id), int(t["id"]), ukey, xp, meow,
        )
        total_xp += xp
        total_meow += meow

    return {"xp": total_xp, "meow": total_meow}


async def notify(admin_id: int, kind: str, title: str, body: str = ""):
    await execute(
        """
        INSERT INTO admin_notifications (admin_id, kind, title, body)
        VALUES ($1, $2, $3, $4)
        """,
        int(admin_id), kind, title, body,
    )


async def list_notifications(admin_id: int, limit: int = 15):
    rows = await fetch(
        """
        SELECT * FROM admin_notifications
        WHERE admin_id = $1
        ORDER BY created_at DESC LIMIT $2
        """,
        int(admin_id), int(limit),
    )
    return [_d(r) for r in rows]


async def mark_notifications_read(admin_id: int):
    await execute(
        "UPDATE admin_notifications SET is_read = TRUE WHERE admin_id = $1 AND is_read = FALSE",
        int(admin_id),
    )


# ---------- Promotion ----------
async def maybe_promote(admin_id: int):
    prof = await get_admin_profile(admin_id)
    if not prof:
        return
    roles = await list_role_defs()
    current = prof.get("role_key") or "candidate"
    cur_order = 0
    for r in roles:
        if r["role_key"] == current:
            cur_order = int(r.get("sort_order") or 0)
            break
    xp = int(prof.get("admin_xp") or 0)
    tasks_done = int(prof.get("completed_tasks") or 0)
    activity = int(prof.get("activity_count") or 0)

    for r in roles:
        if int(r.get("sort_order") or 0) <= cur_order:
            continue
        if xp < int(r.get("required_xp") or 0):
            continue
        if tasks_done < int(r.get("required_tasks") or 0):
            continue
        if activity < int(r.get("required_activity") or 0):
            continue
        # eligible
        if r.get("needs_owner_approval") or not r.get("auto_upgrade", True):
            # create pending request if not exists
            pending = await fetchval(
                """
                SELECT id FROM admin_promotion_requests
                WHERE admin_id = $1 AND to_role = $2 AND status = 'pending'
                """,
                int(admin_id), r["role_key"],
            )
            if not pending:
                await execute(
                    """
                    INSERT INTO admin_promotion_requests (admin_id, from_role, to_role)
                    VALUES ($1, $2, $3)
                    """,
                    int(admin_id), current, r["role_key"],
                )
                await notify(
                    admin_id, "promotion_pending",
                    f"درخواست ارتقا به {r.get('title')}",
                    "منتظر تأیید Owner",
                )
            return
        await apply_role_upgrade(admin_id, r["role_key"])
        return


async def apply_role_upgrade(admin_id: int, role_key: str):
    role = await get_role_def(role_key)
    if not role:
        return False
    prof = await ensure_admin_profile(admin_id)
    old = (prof or {}).get("role_key")
    await execute(
        "UPDATE admin_profiles SET role_key = $2, updated_at = NOW() WHERE user_id = $1",
        int(admin_id), role_key,
    )
    # reward once
    claimed = await fetchval(
        "SELECT 1 FROM admin_role_rewards_claimed WHERE admin_id = $1 AND role_key = $2",
        int(admin_id), role_key,
    )
    if not claimed:
        meow = int(role.get("reward_meow") or 0)
        if meow:
            from database.users import add_meow_coins
            await add_meow_coins(admin_id, meow)
        await execute(
            "INSERT INTO admin_role_rewards_claimed (admin_id, role_key) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            int(admin_id), role_key,
        )
    await notify(
        admin_id, "role_unlocked",
        f"🎉 Role جدید: {role.get('title')}",
        f"از {old} به {role_key}",
    )
    return True


async def list_promotion_requests(status: str = "pending"):
    rows = await fetch(
        "SELECT * FROM admin_promotion_requests WHERE status = $1 ORDER BY created_at",
        status,
    )
    return [_d(r) for r in rows]


async def review_promotion(req_id: int, reviewer_id: int, approve: bool):
    req = _d(await fetchrow(
        "SELECT * FROM admin_promotion_requests WHERE id = $1", int(req_id)
    ))
    if not req or req.get("status") != "pending":
        return False
    status = "approved" if approve else "rejected"
    await execute(
        """
        UPDATE admin_promotion_requests
        SET status = $2, reviewed_by = $3, reviewed_at = NOW()
        WHERE id = $1
        """,
        int(req_id), status, int(reviewer_id),
    )
    if approve:
        await apply_role_upgrade(req["admin_id"], req["to_role"])
    else:
        await notify(req["admin_id"], "promotion_rejected", "درخواست ارتقا رد شد", "")
    return True


# ---------- Leaderboard ----------
async def admin_leaderboard(limit: int = 15, period: str = "all"):
    """period: all | today | week | month — XP from activity if filtered."""
    if period == "all":
        rows = await fetch(
            """
            SELECT p.*, u.first_name, u.username
            FROM admin_profiles p
            LEFT JOIN users u ON u.user_id = p.user_id
            ORDER BY p.admin_xp DESC, p.completed_tasks DESC
            LIMIT $1
            """,
            int(limit),
        )
        return [_d(r) for r in rows]

    interval = {
        "today": "1 day",
        "week": "7 days",
        "month": "30 days",
    }.get(period, None)
    if not interval:
        return await admin_leaderboard(limit, "all")

    rows = await fetch(
        f"""
        SELECT a.admin_id AS user_id,
               COALESCE(SUM(a.xp_earned), 0) AS admin_xp,
               COUNT(*) AS activity_count,
               u.first_name, u.username,
               p.role_key, p.completed_tasks
        FROM admin_activity a
        LEFT JOIN users u ON u.user_id = a.admin_id
        LEFT JOIN admin_profiles p ON p.user_id = a.admin_id
        WHERE a.created_at >= NOW() - INTERVAL '{interval}'
        GROUP BY a.admin_id, u.first_name, u.username, p.role_key, p.completed_tasks
        ORDER BY admin_xp DESC, activity_count DESC
        LIMIT $1
        """,
        int(limit),
    )
    return [_d(r) for r in rows]


async def recent_admin_activity(admin_id: int = None, limit: int = 20):
    if admin_id:
        rows = await fetch(
            "SELECT * FROM admin_activity WHERE admin_id = $1 ORDER BY created_at DESC LIMIT $2",
            int(admin_id), int(limit),
        )
    else:
        rows = await fetch(
            "SELECT * FROM admin_activity ORDER BY created_at DESC LIMIT $1",
            int(limit),
        )
    return [_d(r) for r in rows]
