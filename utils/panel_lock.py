# ==========================================
# قفل پنل گروهی: فقط صاحب پنل بتواند دکمه بزند
# ==========================================

from database.users import get_user

# callback_data به شکل: action#u123456
OWNER_SEP = "#u"


def tag_data(data: str, owner_id: int) -> str:
    if owner_id is None:
        return str(data)
    d = str(data)
    if OWNER_SEP in d:
        d = d.split(OWNER_SEP)[0]
    return f"{d}{OWNER_SEP}{int(owner_id)}"


def parse_data(data: str):
    """Returns (clean_data, owner_id|None)"""
    if not data or OWNER_SEP not in data:
        return data, None
    base, _, oid = data.rpartition(OWNER_SEP)
    try:
        return base, int(oid)
    except ValueError:
        return data, None


async def deny_message(owner_id: int) -> str:
    name = "کاربر"
    try:
        u = await get_user(int(owner_id))
        if u and u.get("first_name"):
            name = u["first_name"]
    except Exception:
        pass
    return (
        f"⛔ این پنل مال تو نیست!\n"
        f"فقط مخصوص **{name}** است."
    )
