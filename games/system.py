# ==========================================
# 🎮 Mini Games — همیشه قابل بازی؛ جایزه هر ۳ ساعت یک‌بار
# ==========================================

import random
import time

from database.users import add_meow_coins, get_user, create_user, update_user
from utils.keyboards import glass, games_kb, back_main_kb

REWARD_COOLDOWN = 3 * 3600  # ۳ ساعت
_pending = {}  # user_id -> game state


def games_home_text():
    return (
        "🎮 **بازی‌ها**\n"
        "━━━━━━━━━━━━━━\n"
        "همیشه می‌تونی بازی کنی.\n"
        "🎁 جایزه (سکه/XP) فقط **هر ۳ ساعت یک‌بار** داده می‌شود.\n"
        "━━━━━━━━━━━━━━"
    )


def fmt_cd(sec):
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}س {m}د"
    return f"{m}:{s:02d}" if m else f"{s}ث"


async def can_reward(user_id: int):
    """(allowed, remaining_seconds)"""
    u = await get_user(user_id)
    if not u:
        await create_user(user_id)
        return True, 0
    last = float(u.get("last_game_reward") or 0)
    rem = REWARD_COOLDOWN - (time.time() - last)
    if rem > 0:
        return False, rem
    return True, 0


async def give_reward(user_id: int, coins: int = 0, note: str = ""):
    ok, rem = await can_reward(user_id)
    if not ok:
        return (
            f"🎮 بازی ثبت شد، ولی جایزه فعلاً نیست.\n"
            f"⏳ جایزه بعدی تا `{fmt_cd(rem)}` دیگر\n"
            f"(هر ۳ ساعت یک‌بار سکه می‌گیری)"
        )
    event_note = ""
    try:
        from database.events import apply_coin_bonus
        coins, _m, event_note = await apply_coin_bonus(int(coins or 0))
    except Exception:
        pass
    if coins:
        await add_meow_coins(user_id, coins)
    try:
        await update_user(user_id, last_game_reward=time.time())
    except Exception as e:
        try:
            from database.pool import execute
            await execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS last_game_reward DOUBLE PRECISION DEFAULT 0
                """
            )
            await execute(
                "UPDATE users SET last_game_reward = $2 WHERE user_id = $1",
                int(user_id), time.time(),
            )
        except Exception as e2:
            print(f"give_reward meta: {e2}")
    msg = f"🎁 +{coins}🪙"
    if event_note:
        msg += f" {event_note}"
    if note:
        msg += f"\n{note}"
    return msg


async def start_guess(user_id):
    answer = random.randint(1, 10)
    _pending[user_id] = {"game": "guess", "answer": answer, "tries": 3}
    return (
        "🎲 **حدس عدد**\nعدد بین ۱ تا ۱۰ را حدس بزن (۳ شانس).",
        glass([("❌ انصراف", "games:home")]),
    )


async def start_quiz(user_id):
    qs = [
        ("گربه‌ها چند انگشت در پنجه جلو دارند؟", ["۴", "۵", "۳"], 1),
        ("میو به انگلیسی؟", ["Bark", "Meow", "Roar"], 1),
        ("چند ساعت خواب روزانه گربه؟", ["۸", "۱۲", "۱۶"], 2),
        ("به بچه گربه چه می‌گویند؟", ["Puppy", "Kitten", "Cub"], 1),
    ]
    q, opts, ans = random.choice(qs)
    _pending[user_id] = {"game": "quiz", "answer": ans}
    rows = [[(f"{i+1}. {o}", f"games:quizans:{i}")] for i, o in enumerate(opts)]
    rows.append([("❌ انصراف", "games:home")])
    return f"❓ **کوییز**\n\n{q}", glass(*rows)


async def handle_quiz_answer(user_id, idx: int):
    p = _pending.pop(user_id, None)
    if not p or p.get("game") != "quiz":
        return "❌ بازی فعالی نیست.", games_kb()
    if idx == p["answer"]:
        reward_msg = await give_reward(user_id, 15)
        return f"✅ درست بود!\n{reward_msg}", games_kb()
    return "❌ اشتباه! دوباره می‌تونی بازی کنی (جایزه طبق قانون ۳ ساعته).", games_kb()


async def handle_guess_input(user_id, text: str):
    p = _pending.get(user_id)
    if not p or p.get("game") != "guess":
        return None, None
    try:
        n = int(text.strip())
    except ValueError:
        return "❌ یک عدد بفرست.", glass([("❌ انصراف", "games:home")])
    if n == p["answer"]:
        _pending.pop(user_id, None)
        reward_msg = await give_reward(user_id, 20)
        return f"🎉 درست! عدد `{n}` بود.\n{reward_msg}", games_kb()
    p["tries"] -= 1
    if p["tries"] <= 0:
        ans = p["answer"]
        _pending.pop(user_id, None)
        return f"💀 تموم شد! جواب `{ans}` بود.\nدوباره بازی کن (جایزه هر ۳ ساعت).", games_kb()
    hint = "بزرگ‌تر" if n < p["answer"] else "کوچک‌تر"
    return f"❌ نه... `{hint}` امتحان کن. شانس: {p['tries']}", glass([("❌ انصراف", "games:home")])


async def handle_games_callback(user_id, data):
    if data == "games:home":
        _pending.pop(user_id, None)
        ok, rem = await can_reward(user_id)
        extra = "✅ جایزه آماده است" if ok else f"⏳ جایزه تا `{fmt_cd(rem)}`"
        return games_home_text() + f"\n{extra}", games_kb()
    if data == "games:guess":
        return await start_guess(user_id)
    if data in ("games:quiz", "games:catquiz"):
        return await start_quiz(user_id)
    if data.startswith("games:quizans:"):
        try:
            idx = int(data.split(":")[-1])
        except ValueError:
            idx = -1
        return await handle_quiz_answer(user_id, idx)
    if data == "games:reaction":
        reward_msg = await give_reward(user_id, 5)
        return f"⚡ واکنش ثبت شد!\n{reward_msg}", games_kb()
    return games_home_text(), games_kb()
