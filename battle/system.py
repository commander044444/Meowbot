# ==========================================
# ⚔️ Battle System
# - صف هماهنگ (دو نفر نبرد بزنند → با هم می‌جنگند)
# - در گروه: ریپلای + «جنگ میویی» → پذیرش/رد
# ==========================================

import random
import time

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from config import BATTLE_COOLDOWN, BATTLE_WIN_REWARD, BATTLE_LOSE_REWARD, MAX_GYM_LEVEL
from database.users import (
    get_user, create_user, get_gym_level,
    add_meow_coins, update_user,
)
from utils.keyboards import battle_home_kb, gym_kb, back_main_kb, glass

# صف سراسری: list of {user_id, first_name, ts}
_queue: list = []
# چالش گروهی: challenge_id -> {from_id, to_id, from_name, to_name, ts}
_challenges: dict = {}
_challenge_seq = 0

COOLDOWN_MSGS = [
    "🐱 هنوز خیلی خسته‌ای! یه کم استراحت کن 😴",
    "😼 گربه‌ات هنوز داره نفس می‌گیره...",
    "💤 انرژی جنگی در حال شارژه...",
]


def power_from_gym(level: int) -> int:
    return 10 + int(level) * 3


def fmt_cd(sec):
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}" if m else f"{s}ث"


def _kb(rows):
    kb = InlineKeyboardMarkup()
    row_num = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(InlineKeyboardButton(text=str(text), callback_data=str(data)), row=row_num)
        row_num += 1
    return kb


def battle_menu_kb():
    return _kb([
        [("⚔️ ورود به صف نبرد", "battle:queue")],
        [("🚪 خروج از صف", "battle:leave_queue")],
        [("🏋️ باشگاه", "battle:gym"), ("📊 آمار", "battle:home")],
        [("🔙 منو", "menu:main")],
    ])


async def battle_home_text(user_id):
    u = await get_user(user_id)
    if not u:
        await create_user(user_id)
        u = await get_user(user_id)
    gym = int(u.get("gym_level") or 1)
    wins = int(u.get("total_wins") or 0)
    losses = int(u.get("total_losses") or 0)
    battles = int(u.get("total_battles") or 0)
    last = float(u.get("last_battle") or 0)
    rem = BATTLE_COOLDOWN - (time.time() - last)
    cd = f"`{fmt_cd(rem)}`" if rem > 0 else "✅ آماده"
    in_q = any(x["user_id"] == int(user_id) for x in _queue)
    qinfo = f"🟢 تو صف هستی (نفرات صف: `{len(_queue)}`)" if in_q else f"سف: `{len(_queue)}` نفر منتظر"
    return (
        f"⚔️ **Battle Arena**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏋️ باشگاه: Level `{gym}` (قدرت `{power_from_gym(gym)}`)\n"
        f"🏆 برد: `{wins}` | ❌ باخت: `{losses}`\n"
        f"📊 کل نبردها: `{battles}`\n"
        f"⏱ Cooldown: {cd}\n"
        f"📋 {qinfo}\n"
        f"━━━━━━━━━━━━━━\n"
        f"• دکمه **ورود به صف**: با اولین نفر بعدی می‌جنگی\n"
        f"• در گروه: روی پیام طرف **ریپلای** کن و بنویس:\n"
        f"  `جنگ میویی`"
    )


async def _cooldown_check(user_id):
    u = await get_user(user_id)
    if not u:
        await create_user(user_id)
        u = await get_user(user_id)
    last = float(u.get("last_battle") or 0)
    rem = BATTLE_COOLDOWN - (time.time() - last)
    if rem > 0:
        return False, random.choice(COOLDOWN_MSGS) + f"\n⏳ `{fmt_cd(rem)}`"
    return True, u


async def resolve_fight(user_a: int, name_a: str, user_b: int, name_b: str):
    """اجرای نبرد بین دو کاربر واقعی. Returns result text."""
    ua = await get_user(user_a) or {}
    ub = await get_user(user_b) or {}
    pa = power_from_gym(int(ua.get("gym_level") or 1)) + random.randint(0, 8)
    pb = power_from_gym(int(ub.get("gym_level") or 1)) + random.randint(0, 8)

    if pa == pb:
        pa += 1  # tie-break

    if pa > pb:
        winner_id, winner_name = user_a, name_a or "A"
        loser_id, loser_name = user_b, name_b or "B"
        wp, lp = pa, pb
    else:
        winner_id, winner_name = user_b, name_b or "B"
        loser_id, loser_name = user_a, name_a or "A"
        wp, lp = pb, pa

    now = time.time()
    # winner
    wu = await get_user(winner_id) or {}
    await update_user(
        winner_id,
        total_wins=int(wu.get("total_wins") or 0) + 1,
        total_battles=int(wu.get("total_battles") or 0) + 1,
        last_battle=now,
    )
    await add_meow_coins(winner_id, BATTLE_WIN_REWARD)
    # loser
    lu = await get_user(loser_id) or {}
    await update_user(
        loser_id,
        total_losses=int(lu.get("total_losses") or 0) + 1,
        total_battles=int(lu.get("total_battles") or 0) + 1,
        last_battle=now,
    )
    await add_meow_coins(loser_id, BATTLE_LOSE_REWARD)

    return (
        f"⚔️ **نتیجه نبرد**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🦁 {name_a} (قدرت `{pa}`)\n"
        f"🐯 {name_b} (قدرت `{pb}`)\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 برنده: **{winner_name}** 🪙 +{BATTLE_WIN_REWARD}\n"
        f"💔 بازنده: **{loser_name}** 🪙 +{BATTLE_LOSE_REWARD}"
    )


async def join_queue(user_id, first_name=""):
    ok, info = await _cooldown_check(user_id)
    if not ok:
        return info, battle_menu_kb()

    uid = int(user_id)
    # already in queue?
    if any(x["user_id"] == uid for x in _queue):
        return f"⏳ تو صف هستی. منتظر حریف...\nنفرات صف: `{len(_queue)}`", battle_menu_kb()

    # find opponent in queue (not self)
    opponent = None
    for i, item in enumerate(list(_queue)):
        if item["user_id"] != uid:
            opponent = _queue.pop(i)
            break

    if opponent is None:
        _queue.append({"user_id": uid, "first_name": first_name or "بازیکن", "ts": time.time()})
        # cleanup old (>5 min)
        now = time.time()
        _queue[:] = [x for x in _queue if now - x["ts"] < 300]
        return (
            f"✅ وارد صف شدی!\n"
            f"وقتی یک نفر دیگر هم **نبرد** بزند، با هم می‌جنگید.\n"
            f"نفرات صف: `{len(_queue)}`",
            battle_menu_kb(),
        )

    # match found
    result = await resolve_fight(
        uid, first_name or "بازیکن",
        opponent["user_id"], opponent.get("first_name") or "حریف",
    )
    return f"🎯 حریف پیدا شد!\n\n{result}", battle_menu_kb()


async def leave_queue(user_id):
    uid = int(user_id)
    before = len(_queue)
    _queue[:] = [x for x in _queue if x["user_id"] != uid]
    if len(_queue) < before:
        return "🚪 از صف خارج شدی.", battle_menu_kb()
    return "در صف نبودی.", battle_menu_kb()


async def create_challenge(from_id, from_name, to_id, to_name):
    global _challenge_seq
    ok, info = await _cooldown_check(from_id)
    if not ok:
        return info, None
    if int(from_id) == int(to_id):
        return "❌ نمی‌تونی با خودت بجنگی!", None
    _challenge_seq += 1
    cid = str(_challenge_seq)
    _challenges[cid] = {
        "from_id": int(from_id),
        "to_id": int(to_id),
        "from_name": from_name or "A",
        "to_name": to_name or "B",
        "ts": time.time(),
    }
    text = (
        f"⚔️ **درخواست جنگ میویی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"از: **{from_name}**\n"
        f"به: **{to_name}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"قبول می‌کنی؟"
    )
    kb = _kb([
        [("✅ پذیرش", f"battle:accept:{cid}"), ("❌ رد", f"battle:reject:{cid}")],
    ])
    return text, kb


async def accept_challenge(cid: str, accepter_id: int):
    ch = _challenges.pop(cid, None)
    if not ch:
        return "❌ این چالش منقضی یا نامعتبر است.", battle_menu_kb()
    if int(accepter_id) != int(ch["to_id"]):
        # put back
        _challenges[cid] = ch
        return "⛔ فقط طرف مقابل می‌تواند بپذیرد.", battle_menu_kb()
    ok, info = await _cooldown_check(accepter_id)
    if not ok:
        return info, battle_menu_kb()
    result = await resolve_fight(
        ch["from_id"], ch["from_name"],
        ch["to_id"], ch["to_name"],
    )
    return result, battle_menu_kb()


async def reject_challenge(cid: str, rejecter_id: int):
    ch = _challenges.pop(cid, None)
    if not ch:
        return "❌ چالش پیدا نشد.", None
    if int(rejecter_id) != int(ch["to_id"]):
        _challenges[cid] = ch
        return "⛔ فقط طرف مقابل می‌تواند رد کند.", None
    return f"❌ {ch['to_name']} جنگ را رد کرد.", None


async def handle_battle_callback(user_id, data, first_name=""):
    if data == "battle:home":
        return await battle_home_text(user_id), battle_menu_kb()
    if data == "battle:queue":
        return await join_queue(user_id, first_name)
    if data == "battle:leave_queue":
        return await leave_queue(user_id)
    if data == "battle:fight":
        # سازگاری با دکمه قدیمی → صف
        return await join_queue(user_id, first_name)
    if data.startswith("battle:accept:"):
        cid = data.split(":")[-1]
        return await accept_challenge(cid, user_id)
    if data.startswith("battle:reject:"):
        cid = data.split(":")[-1]
        return await reject_challenge(cid, user_id)
    if data == "battle:gym":
        u = await get_user(user_id) or {}
        gym = int(u.get("gym_level") or 1)
        return (
            f"🏋️ **باشگاه**\nسطح فعلی: `{gym}` / `{MAX_GYM_LEVEL}`\n"
            f"قدرت: `{power_from_gym(gym)}`\n"
            f"از دستورات Owner برای ارتقا استفاده کن.",
            gym_kb() if 'gym_kb' in dir() else battle_menu_kb(),
        )
    return await battle_home_text(user_id), battle_menu_kb()


def is_battle_challenge_text(text: str) -> bool:
    t = (text or "").strip().lower()
    keys = ("جنگ میویی", "جنگ میو", "نبرد میویی", "challenge battle", "جنگ")
    # دقیق‌تر: جنگ میویی اصلی
    if "جنگ میویی" in (text or "") or "جنگ میو" in (text or ""):
        return True
    if t in ("جنگ", "نبرد", "battle challenge"):
        return True
    return False
