# ==========================================
# Bot key-value settings (GLOBAL_MEOW_GROUP etc.)
# ==========================================

from .pool import fetchrow, execute, fetchval


async def get_setting(key: str, default=None):
    val = await fetchval("SELECT value FROM bot_settings WHERE key = $1", key)
    if val is None:
        return default
    return val


async def set_setting(key: str, value: str):
    await execute(
        """
        INSERT INTO bot_settings (key, value, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
        key, str(value),
    )


async def get_global_meow_group():
    """
    Returns dict: chat_id, invite_link, title
    """
    chat_id = await get_setting("global_meow_group_id", "")
    invite = await get_setting("global_meow_invite", "")
    title = await get_setting("global_meow_title", "گروه میو")
    if not chat_id:
        return None
    return {"chat_id": chat_id, "invite_link": invite, "title": title}


async def set_global_meow_group(chat_id: str, invite_link: str = "", title: str = ""):
    await set_setting("global_meow_group_id", str(chat_id))
    if invite_link:
        await set_setting("global_meow_invite", invite_link)
    if title:
        await set_setting("global_meow_title", title)
