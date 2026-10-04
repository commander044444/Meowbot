# ==========================================
# ⚔️ Battle System (Async + Glass UI)
# ==========================================

import random
import time

from config import BATTLE_COOLDOWN, BATTLE_WIN_REWARD, BATTLE_LOSE_REWARD, MAX_GYM_LEVEL
from database.users import (
    get_user, create_user, get_gym_level, set_gym_level,
    add_meow_coins, get_last_battle, set_last_battle, update_user,
    get_top_users, fetch as _noop,
)
from database.pool import fetch
from utils.keyboards import battle_home_kb, gym_kb, back_main_kb

COOLDOWN_MSGS = [
    "🐱 هنوز خیلی خسته‌ای! یه کم استراحت کن 😴",
    "😼 گربه‌ات هنوز داره نفس می‌گیره...",
    "💤 انرژی جنگی در حال شارژه...",
    "🔥 هنوز وقت نبرد بعدی نرسیده!",
    "😴 MeowBot میگه: استراحت کن جنگجو!",
]


def power_from_gym(level: int) -> int:
    return 10 + int(level) * 3


def fmt_cd(sec):
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}" if m else f"{s}ث"


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
    return (
        f"⚔️ **Battle Arena**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏋️ باشگاه: Level `{gym}` (قدرت `{power_from_gym(gym)}`)\n"
        f"🏆 برد: `{wins}` | ❌ باخت: `{losses}`\n"
        f"📊 کل نبردها: `{battles}`\n"
        f"⏱ Cooldown: {cd}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎁 برد: +{BATTLE_WIN_REWARD}🪙 | باخت: +{BATTLE_LOSE_REWARD}🪙"
    )


async def start_random_battle(user_id, first_name=""):
    u = await get_user(user_id)
    if not u:
        await create_user(user_id, first_name=first_name)
        u = await get_user(user_id)

    last = float(u.get("last_battle") or 0)
    rem = BATTLE_COOLDOWN - (time.time() - last)
    if rem > 0:
        return random.choice(COOLDOWN_MSGS) + f"\n⏳ `{fmt_cd(rem)}`", battle_home_kb()

    my_gym = int(u.get("gym_level") or 1)
    my_power = power_from_gym(my_gym)

    # opponent: random from DB or bot
    rows = await fetch(
        "SELECT user_id, first_name, gym_level FROM users WHERE user_id != $1 ORDER BY RANDOM() LIMIT 1",
        int(user_id),
    )
    if rows:
        opp = dict(rows[0])
        opp_name = opp.get("first_name") or "حریف"
        opp_gym = int(opp.get("gym_level") or 1)
    else:
        opp_name = "ربات جنگجو"
        opp_gym = max(1, my_gym + random.randint(-2, 2))
    opp_power = power_from_gym(opp_gym)

    # simple combat rounds
    my_hp = 100 + my_gym * 2
    opp_hp = 100 + opp_gym * 2
    log = []
    for rnd in range(1, 4):
        dmg_me = max(5, int(my_power * random.uniform(0.7, 1.3)))
        dmg_opp = max(5, int(opp_power * random.uniform(0.7, 1.3)))
        opp_hp -= dmg_me
        my_hp -= dmg_opp
        log.append(f"راند {rnd}: تو `{dmg_me}` زد | حریف `{dmg_opp}` زد")
        if my_hp <= 0 or opp_hp <= 0:
            break

    won = my_hp >= opp_hp and my_hp > 0
    reward = BATTLE_WIN_REWARD if won else BATTLE_LOSE_REWARD
    await add_meow_coins(user_id, reward)
    await set_last_battle(user_id, time.time())

    battles = int(u.get("total_battles") or 0) + 1
    wins = int(u.get("total_wins") or 0) + (1 if won else 0)
    losses = int(u.get("total_losses") or 0) + (0 if won else 1)
    await update_user(user_id, total_battles=battles, total_wins=wins, total_losses=losses)

    result = "🏆 **برد!**" if won else "💀 **باخت...**"
    text = (
        f"⚔️ نبرد با **{opp_name}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"تو: باشگاه {my_gym} (⚡{my_power})\n"
        f"حریف: باشگاه {opp_gym} (⚡{opp_power})\n"
        f"━━━━━━━━━━━━━━\n"
        + "\n".join(log)
        + f"\n━━━━━━━━━━━━━━\n"
        f"{result}\n"
        f"❤️ HP نهایی تو: `{max(0, my_hp)}` | حریف: `{max(0, opp_hp)}`\n"
        f"🪙 +{reward} Meow Coin"
    )
    try:
        from database.missions import update_mission_progress
        from database.achievements import update_achievement_progress
        await update_mission_progress(user_id, "battles", 1)
        if won:
            await update_mission_progress(user_id, "wins", 1)
        await update_achievement_progress(user_id, "battles", battles)
        await update_achievement_progress(user_id, "wins", wins)
    except Exception:
        pass
    return text, battle_home_kb()


async def gym_status(user_id):
    gym = await get_gym_level(user_id)
    cost = gym * 15
    return (
        f"🏋️ **باشگاه میویی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"Level: `{gym}` / `{MAX_GYM_LEVEL}`\n"
        f"قدرت: `{power_from_gym(gym)}`\n"
        f"هزینه ارتقا: `{cost}` 🪙\n"
        f"━━━━━━━━━━━━━━"
    ), gym_kb()


async def gym_upgrade(user_id):
    from database.users import get_meow_coins, spend_meow_coins
    gym = await get_gym_level(user_id)
    if gym >= MAX_GYM_LEVEL:
        return "👑 حداکثر لول باشگاه!", gym_kb()
    cost = gym * 15
    if await get_meow_coins(user_id) < cost:
        return f"❌ نیاز به `{cost}` کوین.", gym_kb()
    if not await spend_meow_coins(user_id, cost):
        return "❌ خطا در برداشت.", gym_kb()
    await set_gym_level(user_id, gym + 1)
    return f"✅ باشگاه → Level **{gym + 1}**!\n🪙 -{cost}\n⚡ قدرت: {power_from_gym(gym + 1)}", gym_kb()


async def handle_battle_callback(user_id, data, first_name=""):
    if data == "battle:home":
        return await battle_home_text(user_id), battle_home_kb()
    if data == "battle:random":
        return await start_random_battle(user_id, first_name)
    if data == "battle:gym":
        return await gym_status(user_id)
    if data == "battle:gym_up":
        return await gym_upgrade(user_id)
    if data == "battle:stats":
        text = await battle_home_text(user_id)
        return text, battle_home_kb()
    return await battle_home_text(user_id), battle_home_kb()
