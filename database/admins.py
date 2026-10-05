# ==========================================
# Admin / Permissions Repository
# ==========================================

from .pool import fetchrow, fetch, execute, fetchval
import json


def _d(row):
    if row is None:
        return None
    d = dict(row)
    perms = d.get("permissions")
    if isinstance(perms, str):
        try:
            d["permissions"] = json.loads(perms)
        except Exception:
            d["permissions"] = []
    elif perms is None:
        d["permissions"] = []
    return d


ALL_PERMISSIONS = [
    "users.view", "users.edit", "users.ban",
    "groups.view", "groups.edit",
    "economy.view", "economy.edit",
    "pets.view", "pets.edit",
    "battles.manage",
    "guides.view", "guides.edit",
    "missions.manage", "achievements.manage",
    "events.manage", "seasons.manage",
    "broadcast.send",
    "admins.view", "admins.manage",
    "database.backup", "database.restore",
    "logs.view", "settings.manage",
    "maintenance.manage",
    "tickets.manage",
]


async def get_admin(user_id: int):
    try:
        return _d(await fetchrow(
            "SELECT * FROM admins WHERE user_id = $1", int(user_id)
        ))
    except Exception as e:
        print(f"get_admin error: {e}")
        return None


async def is_owner(user_id: int) -> bool:
    from config import OWNER_ID
    try:
        if int(user_id) == int(OWNER_ID):
            return True
    except Exception:
        return False
    a = await get_admin(user_id)
    return bool(a and str(a.get("role") or "").upper() == "OWNER" and a.get("enabled"))


async def is_admin(user_id: int) -> bool:
    """Owner یا هر ادمین فعال در جدول admins."""
    from config import OWNER_ID
    try:
        if int(user_id) == int(OWNER_ID):
            return True
    except Exception:
        pass
    a = await get_admin(user_id)
    if not a:
        return False
    # enabled می‌تواند True یا از DB بیاید
    enabled = a.get("enabled")
    if enabled is None:
        enabled = True
    return bool(enabled)


async def has_permission(user_id: int, perm: str) -> bool:
    from config import OWNER_ID
    if int(user_id) == int(OWNER_ID):
        return True
    a = await get_admin(user_id)
    if not a or not a.get("enabled", True):
        return False
    if str(a.get("role") or "").upper() in ("OWNER", "SUPER_ADMIN"):
        return True
    perms = a.get("permissions") or []
    if "*" in perms:
        return True
    return perm in perms


async def add_admin(user_id: int, role: str = "ADMIN", permissions=None, added_by=None, note=""):
    if permissions is None:
        permissions = [
            "users.view", "users.edit", "users.ban",
            "groups.view", "economy.view", "logs.view",
            "tickets.manage", "broadcast.send",
        ]
    role = (role or "ADMIN").upper()
    await execute(
        """
        INSERT INTO admins (user_id, role, permissions, enabled, added_by, note)
        VALUES ($1, $2, $3::jsonb, TRUE, $4, $5)
        ON CONFLICT (user_id) DO UPDATE SET
            role = EXCLUDED.role,
            permissions = EXCLUDED.permissions,
            enabled = TRUE,
            added_by = EXCLUDED.added_by,
            note = EXCLUDED.note,
            updated_at = NOW()
        """,
        int(user_id), role, json.dumps(list(permissions)),
        int(added_by) if added_by is not None else None,
        note or "",
    )
    return await get_admin(user_id)


async def remove_admin(user_id: int):
    from config import OWNER_ID
    if int(user_id) == int(OWNER_ID):
        return False
    await execute(
        "DELETE FROM admins WHERE user_id = $1 AND UPPER(COALESCE(role,'')) != 'OWNER'",
        int(user_id),
    )
    return True


async def set_admin_enabled(user_id: int, enabled: bool):
    from config import OWNER_ID
    if int(user_id) == int(OWNER_ID):
        return False
    await execute(
        "UPDATE admins SET enabled = $2, updated_at = NOW() WHERE user_id = $1",
        int(user_id), bool(enabled),
    )
    return True


async def update_admin_permissions(user_id: int, permissions: list):
    await execute(
        "UPDATE admins SET permissions = $2::jsonb, updated_at = NOW() WHERE user_id = $1",
        int(user_id), json.dumps(list(permissions or [])),
    )


async def update_admin_role(user_id: int, role: str):
    from config import OWNER_ID
    if int(user_id) == int(OWNER_ID):
        return False
    await execute(
        "UPDATE admins SET role = $2, updated_at = NOW() WHERE user_id = $1",
        int(user_id), (role or "ADMIN").upper(),
    )
    return True


async def list_admins():
    try:
        rows = await fetch("SELECT * FROM admins ORDER BY role, user_id")
        return [_d(r) for r in rows]
    except Exception as e:
        print(f"list_admins: {e}")
        return []
