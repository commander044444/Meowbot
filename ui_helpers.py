# ==========================================
# 🐱 MeowBot - UI Helpers (Studio Button)
# ==========================================
# دکمه شیشه‌ای «دارک نایت استدیو» زیر تمام پیام‌های ربات
# Bot.send_message در python-bale-bot فقط‌خواندنی است؛
# بنابراین از helper و پچ کلاس Message استفاده می‌کنیم.
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton


STUDIO_BUTTON_TEXT = "🌑 دارک نایت استدیو"
STUDIO_BUTTON_URL = "https://ble.ir/join/FetpvYjpGQ"

_message_patched = False


def studio_button():
    """دکمه URL دارک نایت استدیو."""
    return InlineKeyboardButton(
        text=STUDIO_BUTTON_TEXT,
        url=STUDIO_BUTTON_URL,
    )


def with_studio(components=None):
    """
    کیبورد موجود را حفظ می‌کند و دکمه استدیو را در ردیف آخر اضافه می‌کند.
    """
    markup = InlineKeyboardMarkup()
    max_row = 0

    if components is not None:
        keyboards = getattr(components, "keyboards", None)
        if keyboards:
            for item in keyboards:
                btn = getattr(item, "item", item)
                row = getattr(item, "row", None) or 1
                try:
                    row = int(row)
                except (TypeError, ValueError):
                    row = 1
                if row > max_row:
                    max_row = row
                markup.add(btn, row=row)

    markup.add(studio_button(), row=max_row + 1)
    return markup


async def send_message(bot, chat_id, text, components=None, **kwargs):
    """
    جایگزین امن برای bot.send_message با دکمه استدیو.
    در تمام کد به‌جای bot.send_message از این تابع استفاده شود.
    """
    components = with_studio(components)
    return await bot.send_message(
        chat_id, text, components=components, **kwargs
    )


def patch_bot_messaging(bot=None):
    """
    Message.reply / edit / edit_text را در سطح کلاس wrap می‌کند
    تا همه message.replyها خودکار دکمه استدیو بگیرند.

    bot.send_message را دست نمی‌زنیم (read-only است).
    برای send از ui_helpers.send_message استفاده شود.
    """
    global _message_patched
    if _message_patched:
        return

    try:
        from bale import Message
    except ImportError:
        print("⚠️ ui_helpers: bale.Message not available")
        return

    # --- reply ---
    if hasattr(Message, "reply"):
        _orig_reply = Message.reply

        async def reply_with_studio(self, text, *args, components=None, **kwargs):
            components = with_studio(components)
            return await _orig_reply(
                self, text, *args, components=components, **kwargs
            )

        try:
            Message.reply = reply_with_studio
        except Exception as e:
            print(f"⚠️ Could not patch Message.reply: {e}")

    # --- edit ---
    if hasattr(Message, "edit"):
        _orig_edit = Message.edit

        async def edit_with_studio(self, text, *args, components=None, **kwargs):
            components = with_studio(components)
            return await _orig_edit(
                self, text, *args, components=components, **kwargs
            )

        try:
            Message.edit = edit_with_studio
        except Exception as e:
            print(f"⚠️ Could not patch Message.edit: {e}")

    # --- edit_text ---
    if hasattr(Message, "edit_text"):
        _orig_edit_text = Message.edit_text

        async def edit_text_with_studio(self, text, *args, components=None, **kwargs):
            components = with_studio(components)
            return await _orig_edit_text(
                self, text, *args, components=components, **kwargs
            )

        try:
            Message.edit_text = edit_text_with_studio
        except Exception as e:
            print(f"⚠️ Could not patch Message.edit_text: {e}")

    _message_patched = True
    print("✅ Studio button: Message.reply/edit patched")
