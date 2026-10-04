# ==========================================
# 🎮 Mini Games (Glass UI)
# ==========================================

import random
from utils.keyboards import games_kb, glass, back_main_kb
from database.users import add_meow_coins, get_user, create_user
from database.pool import execute, fetchrow

# simple in-memory pending games (per user) — for production can move to Redis/DB
_pending = {}


def games_home_text():
    return (
        "🎮 **Arcade میویی**\n"
        "━━━━━━━━━━━━━━\n"
        "یکی از بازی‌ها را انتخاب کن و کوین ببر!\n"
        "━━━━━━━━━━━━━━"
    )


async def start_guess(user_id):
    num = random.randint(1, 10)
    _pending[user_id] = {"game": "guess", "answer": num, "tries": 3}
    return (
        "🎲 **حدس عدد**\n"
        "عددی بین ۱ تا ۱۰ انتخاب کردم.\n"
        "۳ شانس داری. عدد را بفرست!"
    ), glass([("❌ انصراف", "games:home")])


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


async def start_catquiz(user_id):
    return await start_quiz(user_id)


async def handle_quiz_answer(user_id, idx: int):
    p = _pending.pop(user_id, None)
    if not p or p.get("game") != "quiz":
        return "❌ بازی فعالی نیست.", games_kb()
    if idx == p["answer"]:
        await add_meow_coins(user_id, 15)
        return "✅ درست بود! 🪙 +15", games_kb()
    return "❌ اشتباه! دوباره امتحان کن.", games_kb()


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
        await add_meow_coins(user_id, 20)
        return f"🎉 درست! عدد `{n}` بود.\n🪙 +20", games_kb()
    p["tries"] -= 1
    if p["tries"] <= 0:
        ans = p["answer"]
        _pending.pop(user_id, None)
        return f"💀 تموم شد! جواب `{ans}` بود.", games_kb()
    hint = "بزرگ‌تر" if n < p["answer"] else "کوچک‌تر"
    return f"❌ نه... `{hint}` امتحان کن. شانس: {p['tries']}", glass([("❌ انصراف", "games:home")])


async def handle_games_callback(user_id, data):
    if data == "games:home":
        _pending.pop(user_id, None)
        return games_home_text(), games_kb()
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
        await add_meow_coins(user_id, 5)
        return "⚡ سریع بودی! 🪙 +5 (نسخه ساده)", games_kb()
    return games_home_text(), games_kb()
