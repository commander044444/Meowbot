# ==========================================
# 🧠🎯💡 MeowBot - Truth / Dare / Fact
# ==========================================

import random
import re

from database import (
    get_seen_content_indices,
    mark_content_seen,
    create_user,
    get_user,
)

from truths import TRUTHS
from dares import DARES
from facts import FACTS


# ------------------------------------------
# Types
# ------------------------------------------

TYPE_TRUTH = "truth"
TYPE_DARE = "dare"
TYPE_FACT = "fact"

CONTENT_MAP = {
    TYPE_TRUTH: TRUTHS,
    TYPE_DARE: DARES,
    TYPE_FACT: FACTS,
}

DONE_MESSAGES = {
    TYPE_TRUTH: "😹 تو دیگه همه حقیقت‌ها رو دیدی!",
    TYPE_DARE: "😹 تو دیگه همه جرأت‌ها رو دیدی!",
    TYPE_FACT: "😹 تو دیگه همه فکت‌ها رو دیدی!",
}

HEADERS = {
    TYPE_TRUTH: "🧠 حقیقت",
    TYPE_DARE: "🎯 جرأت",
    TYPE_FACT: "💡 فکت",
}


# ------------------------------------------
# Normalize / match
# ------------------------------------------

def _normalize_trigger(text):
    if not text:
        return ""
    text = str(text).replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", "", text)
    return text.strip().lower()


# exact triggers only (after normalize)
TRIGGERS = {
    "حقیقت": TYPE_TRUTH,
    "جرأت": TYPE_DARE,
    "جرات": TYPE_DARE,
    "فکت": TYPE_FACT,
    "fact": TYPE_FACT,
}


def detect_tdf_type(text):
    """
    Returns content type if message is an exact trigger, else None.
    Does not match phrases like «حقیقت جالب» or «جرأت یا حقیقت؟».
    """
    if not text:
        return None
    # Must be essentially only the trigger word (allow surrounding spaces)
    stripped = str(text).strip()
    # Reject if extra words
    if re.search(r"\s", stripped.replace("\u200c", " ").replace("\u200d", " ")):
        # has whitespace between tokens after basic cleanup
        cleaned = re.sub(r"[\u200c\u200d]", "", stripped)
        if re.search(r"\s+", cleaned.strip()):
            return None
    key = _normalize_trigger(text)
    return TRIGGERS.get(key)


# ------------------------------------------
# Core
# ------------------------------------------

def _pick_unseen(user_id, content_type):
    items = CONTENT_MAP.get(content_type) or []
    total = len(items)
    if total == 0:
        return None, True

    seen = set(get_seen_content_indices(user_id, content_type))
    available = [i for i in range(total) if i not in seen]

    if not available:
        return None, True

    idx = random.choice(available)
    return idx, False


def handle_tdf(user_id, text, first_name="", username=""):
    """
    If text is a TDF trigger, return reply string.
    Otherwise return None.
    """
    content_type = detect_tdf_type(text)
    if not content_type:
        return None

    # Ensure user row exists (global account)
    if not get_user(user_id):
        create_user(
            user_id=user_id,
            first_name=first_name or "",
            username=username or "",
        )

    idx, exhausted = _pick_unseen(user_id, content_type)

    if exhausted or idx is None:
        return DONE_MESSAGES[content_type]

    items = CONTENT_MAP[content_type]
    item_text = items[idx]

    mark_content_seen(user_id, content_type, idx)

    display_name = (first_name or "").strip() or "کاربر"
    if username:
        who = f"@{username}"
    else:
        who = display_name

    header = HEADERS[content_type]
    if content_type == TYPE_FACT:
        return f"{header}:\n\n«{item_text}»"
    return f"{header} برای {who}:\n\n«{item_text}»"
