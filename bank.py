# ==========================================
# 🏦 MeowBot - Meow Bank System
# ==========================================

import random
import re

from bale import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    get_bank,
    create_bank,
    card_number_exists,
    update_bank_balance,
    set_bank_pending,
    get_bank_pending,
    clear_bank_pending,
    bank_transfer,
    get_user,
    create_user,
    get_meow_coins,
    spend_meow_coins,
    add_meow_coins,
)


BANK_CREATE_COST = 40

CB_BANK_CREATE = "bank:create"
CB_BANK_DEPOSIT = "bank:deposit"
CB_BANK_WITHDRAW = "bank:withdraw"
CB_BANK_HOME = "bank:home"


def is_bank_callback(data):
    if not data:
        return False
    return str(data).startswith("bank:")


def normalize_bank_text(text):
    if not text:
        return ""
    text = str(text).replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_bank_command(text):
    n = normalize_bank_text(text)
    return n in {
        "بانک میویی",
        "بانک میو",
        "بانک",
        "bank",
    }


def parse_card_transfer(text):
    """
    کارت به کارت میویی 100
    Returns amount or None.
    """
    n = normalize_bank_text(text)
    n = n.replace("‌", "")
    patterns = [
        r"^کارت\s*به\s*کارت\s*میویی\s+(\d+)$",
        r"^کارت\s*به\s*کارت\s*میو\s+(\d+)$",
        r"^کارت\s*به\s*کارت\s+(\d+)$",
        r"^کارت‌به‌کارت\s*میویی\s+(\d+)$",
    ]
    for p in patterns:
        m = re.match(p, n)
        if m:
            try:
                amount = int(m.group(1))
            except ValueError:
                return None
            if amount > 0:
                return amount
    return None


def generate_unique_card():
    for _ in range(80):
        num = f"{random.randint(100000, 999999)}"
        if not card_number_exists(num):
            return num
    # fallback longer search
    for i in range(100000, 1000000):
        num = f"{i}"
        if not card_number_exists(num):
            return num
    return None


def no_bank_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            text=f"🏦 ساخت بانک ({BANK_CREATE_COST} کوین)",
            callback_data=CB_BANK_CREATE,
        ),
        row=1,
    )
    return markup


def bank_home_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="💵 واریز پول", callback_data=CB_BANK_DEPOSIT),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="💸 برداشت پول", callback_data=CB_BANK_WITHDRAW),
        row=1,
    )
    markup.add(
        InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data=CB_BANK_HOME),
        row=2,
    )
    return markup


def format_bank_card(bank, first_name="", username=""):
    owner = f"@{username}" if username else (first_name or "کاربر")
    card = bank["card_number"]
    balance = int(bank["balance"] or 0)
    return (
        "🏦 بانک میویی\n"
        "\n"
        f"👤 صاحب: {owner}\n"
        f"💳 شماره کارت: `{card}`\n"
        f"💰 موجودی بانک: {balance} Meow Coin\n"
        "\n"
        "از دکمه‌های زیر برای واریز یا برداشت استفاده کن."
    )


def format_no_bank():
    return (
        "🏦 هنوز بانک میویی نداری!\n"
        "\n"
        f"برای ساخت حساب بانکی {BANK_CREATE_COST} Meow Coin لازم است.\n"
        "با ساخت بانک یک شماره کارت ۶ رقمی یکتا می‌گیری."
    )


def action_create_bank(user_id, first_name="", username=""):
    user_id = int(user_id)
    if not get_user(user_id):
        create_user(
            user_id=user_id,
            first_name=first_name or "",
            username=username or "",
        )

    existing = get_bank(user_id)
    if existing:
        return format_bank_card(existing, first_name, username), bank_home_keyboard()

    coins = get_meow_coins(user_id)
    if coins < BANK_CREATE_COST:
        return (
            f"🥺 کوین کافی برای ساخت بانک نداری.\n"
            f"هزینه: {BANK_CREATE_COST} Meow Coin\n"
            f"موجودی کیف پول: {coins} Meow Coin",
            no_bank_keyboard(),
        )

    card = generate_unique_card()
    if not card:
        return "❌ خطا در ساخت شماره کارت. دوباره تلاش کن.", no_bank_keyboard()

    if not spend_meow_coins(user_id, amount=BANK_CREATE_COST):
        return (
            f"❌ پرداخت انجام نشد.\nموجودی: {get_meow_coins(user_id)}",
            no_bank_keyboard(),
        )

    bank = create_bank(user_id, card)
    if not bank:
        # refund
        add_meow_coins(user_id, amount=BANK_CREATE_COST)
        return "❌ ساخت بانک ناموفق بود. کوین برگشت داده شد.", no_bank_keyboard()

    text = (
        "✅ بانک میویی با موفقیت ساخته شد!\n"
        "\n"
        f"💳 شماره کارت: `{card}`\n"
        f"🪙 هزینه: -{BANK_CREATE_COST} Meow Coin\n"
        "\n"
        f"{format_bank_card(bank, first_name, username)}"
    )
    return text, bank_home_keyboard()


def get_bank_page(user_id, first_name="", username=""):
    bank = get_bank(user_id)
    if not bank:
        return format_no_bank(), no_bank_keyboard()
    return (
        format_bank_card(bank, first_name, username),
        bank_home_keyboard(),
    )


def handle_bank_callback(data, user_id, first_name="", username=""):
    data = str(data or "")
    user_id = int(user_id)

    if data == CB_BANK_CREATE:
        return action_create_bank(user_id, first_name, username)

    if data == CB_BANK_HOME:
        clear_bank_pending(user_id)
        return get_bank_page(user_id, first_name, username)

    bank = get_bank(user_id)
    if not bank:
        return format_no_bank(), no_bank_keyboard()

    if data == CB_BANK_DEPOSIT:
        set_bank_pending(user_id, "deposit")
        return (
            "💵 واریز به بانک\n"
            "\n"
            "مبلغ را به صورت عدد بفرست (از موجودی کیف پول Meow Coin).\n"
            "مثال: 50",
            bank_home_keyboard(),
        )

    if data == CB_BANK_WITHDRAW:
        set_bank_pending(user_id, "withdraw")
        return (
            "💸 برداشت از بانک\n"
            "\n"
            "مبلغ را به صورت عدد بفرست (به کیف پول Meow Coin واریز می‌شود).\n"
            "مثال: 30",
            bank_home_keyboard(),
        )

    return get_bank_page(user_id, first_name, username)


def try_handle_bank_amount(user_id, text, first_name="", username=""):
    """
    If user has pending deposit/withdraw and sent a number, process it.
    Returns reply text or None.
    """
    pending = get_bank_pending(user_id)
    if not pending:
        return None

    raw = str(text or "").strip().replace(",", "").replace("،", "")
    if not re.fullmatch(r"\d+", raw):
        return None

    amount = int(raw)
    if amount <= 0:
        clear_bank_pending(user_id)
        return "❌ مبلغ باید بیشتر از صفر باشد."

    action = pending["action"]
    bank = get_bank(user_id)
    if not bank:
        clear_bank_pending(user_id)
        return "❌ بانکی پیدا نشد."

    if action == "deposit":
        wallet = get_meow_coins(user_id)
        if wallet < amount:
            clear_bank_pending(user_id)
            return (
                f"🥺 موجودی کیف پول کافی نیست.\n"
                f"موجودی: {wallet} | درخواست: {amount}"
            )
        if not spend_meow_coins(user_id, amount=amount):
            clear_bank_pending(user_id)
            return "❌ واریز انجام نشد."
        updated = update_bank_balance(user_id, amount)
        clear_bank_pending(user_id)
        if not updated:
            add_meow_coins(user_id, amount=amount)
            return "❌ خطا در واریز. کوین برگشت."
        return (
            f"✅ {amount} Meow Coin به بانک واریز شد.\n"
            f"💰 موجودی بانک: {int(updated['balance'])}\n"
            f"🪙 کیف پول: {get_meow_coins(user_id)}"
        )

    if action == "withdraw":
        bal = int(bank["balance"] or 0)
        if bal < amount:
            clear_bank_pending(user_id)
            return (
                f"🥺 موجودی بانک کافی نیست.\n"
                f"موجودی بانک: {bal} | درخواست: {amount}"
            )
        updated = update_bank_balance(user_id, -amount)
        if not updated:
            clear_bank_pending(user_id)
            return "❌ برداشت انجام نشد."
        add_meow_coins(user_id, amount=amount)
        clear_bank_pending(user_id)
        return (
            f"✅ {amount} Meow Coin از بانک برداشت شد.\n"
            f"💰 موجودی بانک: {int(updated['balance'])}\n"
            f"🪙 کیف پول: {get_meow_coins(user_id)}"
        )

    clear_bank_pending(user_id)
    return None


def handle_card_to_card(
    sender_id,
    receiver_id,
    amount,
    sender_name="",
    receiver_name="",
):
    result = bank_transfer(sender_id, receiver_id, amount)
    if not result.get("success"):
        reason = result.get("reason")
        if reason == "sender_no_bank":
            return "❌ تو بانک نداری! اول با «بانک میویی» حساب بساز."
        if reason == "receiver_no_bank":
            return "❌ طرف مقابل بانک نداره."
        if reason == "not_enough_balance":
            bal = result.get("balance", 0)
            return (
                f"🥺 موجودی بانک کافی نیست.\n"
                f"موجودی بانک تو: {bal}\n"
                f"مبلغ انتقال: {amount}"
            )
        if reason == "self_transfer":
            return "😂 نمی‌تونی به خودت کارت‌به‌کارت کنی!"
        if reason == "invalid_amount":
            return "❌ مبلغ نامعتبر است."
        return "❌ انتقال انجام نشد."

    # تراکنش خیالی شیک
    return (
        "🧾 تراکنش بانک میویی\n"
        "━━━━━━━━━━━━━━\n"
        f"📤 از: {sender_name or 'فرستنده'}\n"
        f"💳 کارت: {result['sender_card']}\n"
        f"📥 به: {receiver_name or 'گیرنده'}\n"
        f"💳 کارت: {result['receiver_card']}\n"
        f"💰 مبلغ: {amount} Meow Coin\n"
        "━━━━━━━━━━━━━━\n"
        f"✅ موجودی بانک فرستنده: {result['sender_balance']}\n"
        f"✅ موجودی بانک گیرنده: {result['receiver_balance']}\n"
        "━━━━━━━━━━━━━━\n"
        "🐱 Meow Bank • تراکنش موفق"
    )
