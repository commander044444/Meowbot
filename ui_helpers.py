# ==========================================
# 🐱 MeowBot - UI Helpers (Studio Button)
# ==========================================
# دکمه شیشه‌ای «دارک نایت استدیو» زیر تمام پیام‌های ربات
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton


STUDIO_BUTTON_TEXT = "🌑 دارک نایت استدیو"
STUDIO_BUTTON_URL = "https://ble.ir/join/FetpvYjpGQ"


def studio_button():
    """دکمه URL دارک نایت استدیو."""
    return InlineKeyboardButton(
        text=STUDIO_BUTTON_TEXT,
        url=STUDIO_BUTTON_URL,
    )


def with_studio(components=None):
    """
    کیبورد موجود را حفظ می‌کند و دکمه استدیو را در ردیف آخر اضافه می‌کند.
    اگر components خالی باشد، فقط همان یک دکمه برگردانده می‌شود.
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


def patch_bot_messaging(bot):
    """
    تمام مسیرهای ارسال/ویرایش پیام ربات را طوری wrap می‌کند
    که همیشه دکمه استدیو زیر پیام باشد.
    """
    # --- bot.send_message ---
    if not getattr(bot, "_studio_send_patched", False):
        _orig_send = bot.send_message

        async def send_with_studio(chat_id, text, *args, components=None, **kwargs):
            components = with_studio(components)
            return await _orig_send(
                chat_id, text, *args, components=components, **kwargs
            )

        bot.send_message = send_with_studio
        bot._studio_send_patched = True

    # --- Message.reply / edit ---
    try:
        from bale import Message
    except ImportError:
        return

    if not getattr(Message, "_studio_reply_patched", False):
        _orig_reply = Message.reply

        async def reply_with_studio(self, text, *args, components=None, **kwargs):
            components = with_studio(components)
            return await _orig_reply(
                self, text, *args, components=components, **kwargs
            )

        Message.reply = reply_with_studio
        Message._studio_reply_patched = True

    if not getattr(Message, "_studio_edit_patched", False):
        if hasattr(Message, "edit"):
            _orig_edit = Message.edit

            async def edit_with_studio(self, text, *args, components=None, **kwargs):
                components = with_studio(components)
                return await _orig_edit(
                    self, text, *args, components=components, **kwargs
                )

            Message.edit = edit_with_studio

        if hasattr(Message, "edit_text"):
            _orig_edit_text = Message.edit_text

            async def edit_text_with_studio(self, text, *args, components=None, **kwargs):
                components = with_studio(components)
                return await _orig_edit_text(
                    self, text, *args, components=components, **kwargs
                )

            Message.edit_text = edit_text_with_studio

        Message._studio_edit_patched = True
