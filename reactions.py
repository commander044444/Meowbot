# ==========================================
# 🗿 MeowBot - Reaction System
# ==========================================
# واکنش‌های بامزه نسل‌زدی در گروه — مستقل از دستورات
# ==========================================

import random
import re
import time
from collections import defaultdict


# ==========================================
# تنظیمات احتمال و کول‌داون (قابل تغییر)
# ==========================================

PROB = {
    "moai": 1.0,           # 🗿
    "laugh": 1.0,          # 😂🤣😆
    "names": 1.0,          # اسم سازنده / استدیو
    "bye": 1.0,            # خداحافظی
    "hello": 1.0,          # سلام
    "ajab": 1.0,           # عجب → رجب
    "aa": 1.0,             # عا / بع / باع
    "swear_joke": 1.0,     # کس/کص/کث/نچ/نوچ/کونی (شوخی)
    "chetori": 1.0,        # چطوری
    "reply_to_bot": 1.0,   # ریپلای روی پیام ربات
    "bot_call": 1.0,       # بات / ربات / میوبات
    "random_chat": 0.03,   # پیام تصادفی بدون تریگر (کم بماند تا اسپم نشود)
}

# کول‌داون کلی واکنش در هر گروه (ثانیه)
GROUP_REACTION_COOLDOWN = 0

# کول‌داون پیام تصادفی در هر گروه (ثانیه) — حدود چند بار در ساعت
RANDOM_CHAT_COOLDOWN = 20 * 60

# کول‌داون per-user برای جلوگیری از اسپم یک نفر
USER_REACTION_COOLDOWN = 0


# ==========================================
# پاسخ‌ها
# ==========================================

RESPONSES = {
    "moai": [
        "🗿🗿🗿",
        "🗿",
        "هه 🗿",
        "🗿؟",
        "یاشاسین دارکنایت استدیو 🗿",
    ],
    "laugh": [
        "😂",
        "خخخ 😂",
        "🤣",
        "ب چی میخندی 🗿",
        "کسنمک🗿😂",
        "خخخخخ 🫠",
    ],
    "names": [
        "داری سازنده منو صدا می‌زنی؟ 🗿",
        "آهااا استدیو؟ 👀",
        "دارکنایت استدیو در جریانه 🗿✨",
        "سازنده؟ همون که منو ساخته؟ 🤓",
        "اسمش اومد گوشم تیز شد 🗿",
        "استدیو کجا بودیم 🫠",
        "Dark Knight Studio 🗿🖤",
    ],
    "bye": [
        "خدافظ 👋",
        "فعلاً 🗿",
        "بای بای 👋",
        "برو دیگه 🫠",
        "خداحافظ رفیق 🗿",
        "سیک دیگ 👋🗿",
    ],
    "hello": [
        "سلام 🗿",
        "سالام 😂",
        "سلام سلام 👋",
        "سلامعلیکم 🗿",
        " سلام 🫠",
        "سلام داداش 🗿",
        "سلام اوومدی؟ 👋",
    ],
    "ajab": [
        "رجب 🗿",
        " رژب🗿",
        "رژب 😂",
        "عجببب 🗿",
    ],
    "aa": [
        "عاااا🗿",
        "عااا 🗿",
        "بع 🗿",
        "عا؟ 🫠",
        "عاااااا 🗿",
    ],
    "swear_joke": [
        "عه 😳",
        "اِ اِ 🗿",
        "حواست هست چی گفتی؟ 😂",
        "اوووف 🗿",
        "کونی 😳😂",
        "دنبال چیی🗿",
        "نچ نچ🗿",
        "نوچ 😂",
        "نههه 🗿",
        "ای ژقی بدیخت🫠",
        "الان به پدرت زنگ میزنم صبر کن.. 🗿",
    ],
    "chetori": [
        "اینجوری 🗿🥹",
        "خوب خوب 🗿",
        "اینجوری دیگه 🫠",
        "🗿",
        "بتوچه😂",
    ],
    "reply_to_bot": [
        "تو اجازه گزفتی رو من ریپ میزنی؟",
        "چ عجب رو ما یه ریپی زدی",
        "روم کراشییی ریپ میزنی هی🥹🥹🥹؟",
        "کسخل😂",
        "جونزم براز ؟ ریپ زدی؟",
        "بله🥹🥹؟",
        "چیشد 🗿؟",
    ],
    # بار اول صدا زدن
    "bot_call_first_bat": [
        "بات خودتی🦦 من میو هسم🙄",
    ],
    "bot_call_first_robat": [
        "بلههههههههههه",
        "بلههههه 🗿",
        "جااان؟ 🦦",
        "بنالللل خووووو",
    ],
    # بارهای ۲ و ۳ در همان ۱ دقیقه
    "bot_call_repeat": [
        "هاااااا",
        "خب بگوووووو",
        "بگو خب حرملهههههه",
        "چیشد دوباره؟ 🗿",
        "جانم بگو 🦦",
        "گوشم با توست بگو 🫠",
        "ها بگو دیگه 🗿",
        "من اینجام بگو 🐱",
    ],
    # بار ۴ به بعد در همان ۱ دقیقه
    "bot_call_angry": [
        "خب نالههه کنننن گاییدی مغزمو",
        "د اخه خارک... حیف بابام گفته فحش ندم🙄 چند بار میگی باتتتت",
        "گایدیییییییی منممم صبرییی دارممممممم",
    ],
    "random_chat": [
        "مشT نمی‌خوای یه میو کنی؟ 🗿",
        "هعییی چرا کسی با من بازی نمی‌کنه 🫠🥹",
        "یکی با من میو کنه دیگه 🗿",
        "حوصلم پکید 🤓",
        "راستی تو چنل دارکنایت استدیو عضو شدییی؟؟؟؟",
        "ببین اینجا چی داریممم🙄 بزن روش ```کسخلی😂😂😂```",
        "یه میو بزن حال بیاد 🐱",
        "کسالت باره اینجا 🫠",
        "کسی هست اصلاً؟ 🗿",
        "بیاید میو کنیم دیگه 🐱🗿",
        "عجب حال تخمیی منو گرفت🦦"
    ],
}


# ==========================================
# State (in-memory anti-spam)
# ==========================================

_last_group_reaction = defaultdict(float)   # chat_id -> timestamp
_last_user_reaction = defaultdict(float)    # (chat_id, user_id) -> timestamp
_last_random_chat = defaultdict(float)      # chat_id -> timestamp

# صدا زدن بات/ربات: تعداد در پنجره ۱ دقیقه‌ای per (chat, user)
_bot_call_times = defaultdict(list)  # key -> [timestamps]
BOT_CALL_WINDOW = 60  # ثانیه
BOT_CALL_IGNORE_AFTER = 4  # از بار ۴ به بعد قهر می‌کند


# ==========================================
# Text helpers
# ==========================================

def _normalize(text: str) -> str:
    if not text:
        return ""
    t = str(text)
    t = t.replace("\u200c", " ").replace("\u200d", "")
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _chance(p: float) -> bool:
    return random.random() < float(p)


def _pick(key: str) -> str:
    opts = RESPONSES.get(key) or ["🗿"]
    return random.choice(opts)


# --- triggers ---

_MOAI = "🗿"

_LAUGH_EMOJIS = ("😂", "🤣", "😆", "😹")

_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"آرتین",
        r"ارتین",
        r"commander",
        r"کوماندر",
        r"کماندر",
        r"دارک\s*نایت\s*استدیو",
        r"dark\s*knight\s*studio",
        r"دارک\s*نایت",
        r"dark\s*knight",
        r"دارکنایت",
        r"استدیو",
        r"\bstudio\b",
        r"دارک",
        r"\bdark\b",
    ]
]

_BYE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(^|\s)من\s*برم(\s|$)",
        r"(^|\s)من\s*رفتم(\s|$)",
        r"(^|\s)میرم(\s|$)",
        r"(^|\s)می‌رم(\s|$)",
        r"خدا?\s*حافظ",
        r"(^|\s)خدافظ(\s|$)",
        r"(^|\s)بای(\s|$)",
        r"(^|\s)bye(\s|$)",
        r"(^|\s)goodbye(\s|$)",
    ]
]

# سلام با تحمل غلط املایی رایج
_HELLO_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(^|\s)س+ل+ا+م+(\s|$|[!.،,؟?])",
        r"(^|\s)س+ا+ل+ا+م+(\s|$|[!.،,؟?])",
        r"(^|\s)س+ا+ل+م+(\s|$|[!.،,؟?])",
        r"(^|\s)ث+ل+ا+م+(\s|$|[!.،,؟?])",
        r"(^|\s)س+ل+و+م+(\s|$|[!.،,؟?])",
        r"(^|\s)salam+(\s|$|[!.،,؟?])",
        r"(^|\s)hello+(\s|$|[!.،,؟?])",
        r"(^|\s)hi+(\s|$|[!.،,؟?])",
        r"(^|\s)درود(\s|$|[!.،,؟?])",
    ]
]

_AJAB = re.compile(r"(^|\s)عجب(\s|$|[!.،,؟?])")

# عا / عاا / بع / باع / ع
_AA_PATTERNS = [
    re.compile(p)
    for p in [
        r"(^|\s)ع+ا+(\s|$|[!.،,؟?🗿])",
        r"(^|\s)باع+(\s|$|[!.،,؟?])",
        r"(^|\s)بع+(\s|$|[!.،,؟?])",
        r"(^|\s)ع+(\s|$|[!.،,؟?])",
    ]
]

# کلمات شوخی — مرز کلمه تا حد ممکن
# کس / کص / کث / نچ / نوچ / نه / کونی
_SWEAR = re.compile(
    r"(?:^|[\s.!،,؟?\u200c])(?:کس|کص|کث|نچ|نوچ|نه+|کونی)(?:$|[\s.!،,؟?\u200c])"
)

_CHETORI = re.compile(
    r"(چی?طوری|چیجوری|چجوری|چه\s*جوری)",
    re.IGNORECASE,
)

# بات / ربات / میوبات / bot (مرز کلمه)
_BOT_CALL = re.compile(
    r"(?:^|[\s.!،,؟?\u200c])(?:ربات|بات|میوبات|میو\s*بات|meow\s*bot|\bbot\b)(?:$|[\s.!،,؟?\u200c])",
    re.IGNORECASE,
)


def _bot_call_kind(norm: str, raw: str) -> str | None:
    """برمی‌گرداند: 'robat' | 'bat' | None"""
    if not _BOT_CALL.search(norm) and not _BOT_CALL.search(raw):
        return None
    # اولویت با «ربات» چون شامل «بات» هم می‌شود از نظر حروف
    if re.search(r"ربات", norm) or re.search(r"robot", norm, re.I):
        return "robat"
    if re.search(r"میو\s*بات|میوبات|meow\s*bot", norm, re.I):
        return "bat"
    if re.search(r"(?:^|[\s])بات(?:$|[\s])", norm) or re.search(r"\bbot\b", norm, re.I):
        return "bat"
    if re.search(r"بات", norm):
        return "bat"
    return "robat"


def _bot_call_count(chat_id, user_id) -> int:
    """تعداد صدا زدن در ۶۰ ثانیه اخیر (بعد از ثبت فعلی)."""
    key = (str(chat_id), int(user_id))
    now = time.time()
    window = BOT_CALL_WINDOW
    times = [t for t in _bot_call_times[key] if now - t < window]
    times.append(now)
    _bot_call_times[key] = times
    return len(times)


def _response_for_bot_call(kind: str, count: int) -> str:
    if count >= BOT_CALL_IGNORE_AFTER:
        return _pick("bot_call_angry")
    if count == 1:
        if kind == "bat":
            return _pick("bot_call_first_bat")
        return _pick("bot_call_first_robat")
    # 2 یا 3
    return _pick("bot_call_repeat")


def _is_on_cooldown(chat_id, user_id) -> bool:
    now = time.time()
    chat_key = str(chat_id)
    if now - _last_group_reaction[chat_key] < GROUP_REACTION_COOLDOWN:
        return True
    if now - _last_user_reaction[(chat_key, int(user_id))] < USER_REACTION_COOLDOWN:
        return True
    return False


def _mark_reacted(chat_id, user_id):
    now = time.time()
    chat_key = str(chat_id)
    _last_group_reaction[chat_key] = now
    _last_user_reaction[(chat_key, int(user_id))] = now


def _random_chat_ready(chat_id) -> bool:
    chat_key = str(chat_id)
    return (time.time() - _last_random_chat[chat_key]) >= RANDOM_CHAT_COOLDOWN


def _mark_random_chat(chat_id):
    _last_random_chat[str(chat_id)] = time.time()


# ==========================================
# Engine
# ==========================================

def try_react(
    text: str,
    *,
    chat_id,
    user_id,
    is_group: bool,
    is_bot_message: bool = False,
    reply_to_bot: bool = False,
):
    """
    اگر باید واکنش نشان داده شود، متن پاسخ را برمی‌گرداند؛ وگرنه None.

    فقط برای پیام کاربران در گروه.
    یک پیام حداکثر یک واکنش.
    """
    if not is_group:
        return None
    if is_bot_message:
        return None
    if not text or not str(text).strip():
        return None
    if chat_id is None or user_id is None:
        return None

    # ریپلای روی پیام ربات — اولویت بالا
    if reply_to_bot and _chance(PROB["reply_to_bot"]):
        if not _is_on_cooldown(chat_id, user_id):
            _mark_reacted(chat_id, user_id)
            return _pick("reply_to_bot")

    if _is_on_cooldown(chat_id, user_id):
        # هنوز ممکن است random_chat جدا باشد؛ ولی برای اسپم کمتر همان cooldown کلی را رعایت می‌کنیم
        return None

    raw = str(text)
    norm = _normalize(raw)

    # صدا زدن بات/ربات — با اسکار سیستم پله‌ای در ۱ دقیقه
    if _chance(PROB.get("bot_call", 1.0)):
        kind = _bot_call_kind(norm, raw)
        if kind:
            count = _bot_call_count(chat_id, user_id)
            _mark_reacted(chat_id, user_id)
            return _response_for_bot_call(kind, count)

    # ترتیب اولویت تریگرها
    checks = [
        ("moai", lambda: _MOAI in raw and _chance(PROB["moai"])),
        ("laugh", lambda: any(e in raw for e in _LAUGH_EMOJIS) and _chance(PROB["laugh"])),
        ("names", lambda: any(p.search(norm) or p.search(raw) for p in _NAME_PATTERNS) and _chance(PROB["names"])),
        ("bye", lambda: any(p.search(norm) for p in _BYE_PATTERNS) and _chance(PROB["bye"])),
        ("hello", lambda: any(p.search(norm) for p in _HELLO_PATTERNS) and _chance(PROB["hello"])),
        ("ajab", lambda: bool(_AJAB.search(norm)) and _chance(PROB["ajab"])),
        ("aa", lambda: any(p.search(norm) for p in _AA_PATTERNS) and _chance(PROB["aa"])),
        ("swear_joke", lambda: bool(_SWEAR.search(norm)) and _chance(PROB["swear_joke"])),
        ("chetori", lambda: bool(_CHETORI.search(norm)) and _chance(PROB["chetori"])),
    ]

    for key, cond in checks:
        try:
            if cond():
                _mark_reacted(chat_id, user_id)
                return _pick(key)
        except Exception:
            continue

    # پیام تصادفی بدون تریگر (احتمال خیلی کم + کول‌داون جدا)
    if _random_chat_ready(chat_id) and _chance(PROB["random_chat"]):
        _mark_reacted(chat_id, user_id)
        _mark_random_chat(chat_id)
        return _pick("random_chat")

    return None


def is_message_from_bot(message, bot) -> bool:
    """آیا نویسنده پیام خود ربات است؟"""
    author = getattr(message, "author", None) or getattr(message, "from_user", None)
    if not author:
        return False
    bot_user = getattr(bot, "user", None) or getattr(bot, "me", None)
    if not bot_user:
        return False
    try:
        return int(author.id) == int(bot_user.id)
    except Exception:
        return False


def is_reply_to_bot(message, bot) -> bool:
    """آیا این پیام، ریپلای روی پیام خود ربات است؟"""
    reply = getattr(message, "reply_to_message", None)
    if not reply:
        return False
    return is_message_from_bot(reply, bot)
