# ==========================================
# 🏦 Bank UI (Glass)
# ==========================================

import random
from database.bank import (
    get_bank, create_bank, update_bank_balance, set_bank_pending,
    get_bank_pending, clear_bank_pending, get_bank_by_card, bank_transfer,
)
from database.users import get_meow_coins, spend_meow_coins, add_meow_coins, get_user
from database.economy import record_transaction, get_user_transactions
from utils.keyboards import bank_home_kb, bank_cancel_kb, back_main_kb


async def bank_home(user_id):
    bank = await get_bank(user_id)
    coins = await get_meow_coins(user_id)
    if not bank:
        return (
            "🏦 **بانک میویی**\n"
            "━━━━━━━━━━━━━━\n"
            "حساب نداری!\n"
            f"🪙 کیف پول: `{coins}`\n"
            "━━━━━━━━━━━━━━\n"
            "با دکمه زیر حساب باز کن."
        ), bank_home_kb(False)
    return (
        f"🏦 **بانک میویی**\n"
        f"━━━━━━━━━━━━━━\n"
        f"💳 کارت: `{bank.get('card_number')}`\n"
        f"💰 موجودی بانک: `{bank.get('balance', 0)}`\n"
        f"🪙 کیف پول: `{coins}`\n"
        f"━━━━━━━━━━━━━━"
    ), bank_home_kb(True)


async def open_bank(user_id):
    bank = await get_bank(user_id)
    if bank:
        return await bank_home(user_id)
    card = "".join(str(random.randint(0, 9)) for _ in range(12))
    await create_bank(user_id, card)
    return (
        f"✅ حساب باز شد!\n"
        f"💳 شماره کارت: `{card}`\n"
        f"این شماره را برای انتقال نگه دار."
    ), bank_home_kb(True)


async def start_deposit(user_id):
    await set_bank_pending(user_id, "deposit")
    return "📥 مقدار واریز را به عدد بفرست:\n(از کیف پول به بانک)", bank_cancel_kb()


async def start_withdraw(user_id):
    await set_bank_pending(user_id, "withdraw")
    return "📤 مقدار برداشت را به عدد بفرست:\n(از بانک به کیف پول)", bank_cancel_kb()


async def start_transfer(user_id):
    await set_bank_pending(user_id, "transfer")
    return (
        "💸 انتقال کارت‌به‌کارت\n"
        "فرمت:\n`شماره_کارت مقدار`\n"
        "مثال:\n`123456789012 50`"
    ), bank_cancel_kb()


async def handle_amount_input(user_id, text: str):
    pending = await get_bank_pending(user_id)
    if not pending:
        return None, None
    action = pending.get("action")
    bank = await get_bank(user_id)
    if not bank and action != "transfer":
        await clear_bank_pending(user_id)
        return "❌ اول حساب باز کن.", bank_home_kb(False)

    if action == "transfer":
        parts = text.strip().split()
        if len(parts) != 2:
            return "❌ فرمت: `شماره_کارت مقدار`", bank_cancel_kb()
        card, amt_s = parts[0], parts[1]
        try:
            amount = int(amt_s)
        except ValueError:
            return "❌ مقدار باید عدد باشد.", bank_cancel_kb()
        if amount <= 0:
            return "❌ مقدار نامعتبر.", bank_cancel_kb()
        target = await get_bank_by_card(card)
        if not target:
            return "❌ کارت مقصد پیدا نشد.", bank_cancel_kb()
        if int(target["user_id"]) == int(user_id):
            return "❌ نمی‌تونی به خودت بزنی.", bank_cancel_kb()
        ok = await bank_transfer(user_id, int(target["user_id"]), amount)
        await clear_bank_pending(user_id)
        if not ok:
            return "❌ موجودی بانک کافی نیست.", bank_home_kb(True)
        await record_transaction(user_id, "transfer_out", -amount, meta={"to": card})
        await record_transaction(int(target["user_id"]), "transfer_in", amount, meta={"from": bank.get("card_number") if bank else ""})
        return f"✅ `{amount}` به کارت `{card}` منتقل شد.", bank_home_kb(True)

    try:
        amount = int(text.strip())
    except ValueError:
        return "❌ یک عدد بفرست.", bank_cancel_kb()
    if amount <= 0:
        return "❌ مقدار باید مثبت باشد.", bank_cancel_kb()

    if action == "deposit":
        coins = await get_meow_coins(user_id)
        if coins < amount:
            return f"❌ کیف پول کافی نیست (`{coins}`).", bank_cancel_kb()
        if not await spend_meow_coins(user_id, amount):
            return "❌ خطا.", bank_cancel_kb()
        await update_bank_balance(user_id, amount)
        await clear_bank_pending(user_id)
        await record_transaction(user_id, "deposit", amount)
        return f"✅ `{amount}` به بانک واریز شد.", bank_home_kb(True)

    if action == "withdraw":
        ok = await update_bank_balance(user_id, -amount)
        if not ok:
            return "❌ موجودی بانک کافی نیست.", bank_cancel_kb()
        await add_meow_coins(user_id, amount)
        await clear_bank_pending(user_id)
        await record_transaction(user_id, "withdraw", amount)
        return f"✅ `{amount}` به کیف پول منتقل شد.", bank_home_kb(True)

    await clear_bank_pending(user_id)
    return None, None


async def bank_history(user_id):
    txs = await get_user_transactions(user_id, 10)
    if not txs:
        return "📋 تاریخچه‌ای نیست.", bank_home_kb(True)
    lines = ["📋 **آخرین تراکنش‌ها**\n━━━━━━━━━━━━━━"]
    for t in txs:
        lines.append(f"• {t.get('type')} | {t.get('amount')}")
    return "\n".join(lines), bank_home_kb(True)


async def handle_bank_callback(user_id, data):
    if data == "bank:home":
        await clear_bank_pending(user_id)
        return await bank_home(user_id)
    if data == "bank:open":
        return await open_bank(user_id)
    if data == "bank:deposit":
        return await start_deposit(user_id)
    if data == "bank:withdraw":
        return await start_withdraw(user_id)
    if data == "bank:transfer":
        return await start_transfer(user_id)
    if data == "bank:history":
        return await bank_history(user_id)
    if data == "bank:card":
        bank = await get_bank(user_id)
        if not bank:
            return "❌ حساب نداری.", bank_home_kb(False)
        return f"💳 کارت شما:\n`{bank.get('card_number')}`", bank_home_kb(True)
    return await bank_home(user_id)
