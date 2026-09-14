# ==========================================
# 🐱 MeowBot - Main
# ==========================================

from bale import Bot, Message, CallbackQuery

from config import (
    BOT_TOKEN,
    ALLOWED_GROUP,
    OWNER_ID,
    MAX_GYM_LEVEL,
)

from database import (
    init_database,
    register_group,
    get_all_groups,
    add_meow_points_to_all,
    add_meow_coins_to_all,
    get_user as db_get_user,
    admin_set_meow_points,
    admin_set_meow_coins,
    admin_set_gym_level,
)

from meow import (
    is_meow,
    is_allowed_group,
    register_meow,
    format_cooldown,
)

from gym import (
    get_gym_status,
    upgrade_gym,
)

from ranking import (
    format_ranking,
    get_user_rank,
)

from battle import (
    start_battle,
    format_battle_cooldown,
)

from profile import (
    format_profile,
)

from coins import (
    parse_transfer_command,
    transfer_coins,
)

from guide import (
    is_guide_command,
    get_guide,
)

from menu import (
    is_start_command,
    is_menu_callback,
    WELCOME_TEXT,
    main_menu_keyboard,
    get_menu_page,
)

from pet import (
    is_pet_callback,
    is_private_chat,
    handle_pet_callback,
    try_handle_pet_name_input,
    try_call_pet,
    try_random_behavior,
    get_or_prompt_pet,
)

from tdf import handle_tdf

from bank import (
    is_bank_command,
    is_bank_callback,
    get_bank_page,
    handle_bank_callback,
    try_handle_bank_amount,
    parse_card_transfer,
    handle_card_to_card,
)

from seasons import (
    is_season_command,
    handle_season_command,
    start_season_scheduler,
)

from ui_helpers import (
    patch_bot_messaging,
    send_message as studio_send_message,
)


# ==========================================
# Database
# ==========================================

init_database()


# ==========================================
# Bot
# ==========================================

bot = Bot(
    token=BOT_TOKEN
)

# دکمه استدیو زیر تمام پیام‌ها (send / reply / edit)
patch_bot_messaging(bot)


# ==========================================
# Ready
# ==========================================

@bot.event
async def on_ready():

    print("=" * 55)
    print("🐱 MEOWBOT ONLINE")
    print("=" * 55)

    print(
        f"🎀 Legacy Group Config: {ALLOWED_GROUP}"
    )

    print(
        "🐾 Meow System: ON"
    )

    print(
        "🏋️ Gym System: ON"
    )

    print(
        "🏆 Ranking System: ON"
    )

    print(
        "⚔️ Battle System: ON"
    )

    print(
        "🪙 Coin System: ON"
    )

    print(
        "👤 Profile System: ON"
    )

    print(
        "📢 Broadcast System: ON"
    )

    print(
        "📖 Guide System: ON"
    )

    print(
        "🐱 Pet Meow System: ON"
    )

    print(
        "📅 Seasons System: ON"
    )

    print(
        "🎮 Admin Economy Commands: ON"
    )

    print(
        "🌑 Studio Button: ON"
    )

    print(
        "📢 Echo System: ON"
    )

    print("=" * 55)

    # Start season midnight scheduler (Tehran)
    try:
        start_season_scheduler(bot)
    except Exception as e:
        print(f"❌ Season scheduler start failed: {e}")


# ==========================================
# Messages
# ==========================================

@bot.event
async def on_message(message: Message):

    # ======================================
    # Message Text
    # ======================================

    text = message.text

    if not text:
        return

    text = text.strip()

    # ======================================
    # Chat
    # ======================================

    chat = message.chat

    chat_id = getattr(
        chat,
        "id",
        None
    )

    chat_username = getattr(
        chat,
        "username",
        None
    )

    chat_title = (
        getattr(
            chat,
            "title",
            None
        )
        or ""
    )

    # ======================================
    # Register Group
    # ======================================

    # فقط چت‌هایی که title دارند یا username گروهی دارند
    # در لیست Broadcast ثبت می‌شوند.
    #
    # این کار باعث می‌شود چت خصوصی وارد Broadcast نشود.

    if chat_id is not None:

        if chat_title or chat_username:

            try:

                register_group(
                    chat_id=chat_id,
                    title=chat_title,
                    username=chat_username or ""
                )

            except Exception as e:

                print(
                    f"❌ Group registration failed for {chat_id}: {e}"
                )

    # ======================================
    # Allowed Group
    # ======================================

    if not is_allowed_group(
        chat_id=chat_id,
        chat_username=chat_username
    ):
        return

    # ======================================
    # Author
    # ======================================

    author = message.author

    if not author:
        return

    user_id = author.id

    first_name = (
        getattr(
            author,
            "first_name",
            None
        )
        or "Unknown"
    )

    username = (
        getattr(
            author,
            "username",
            None
        )
        or ""
    )

    normalized_text = text.lower()

    private_chat = is_private_chat(chat)


    # ======================================
    # 🐱 Start / Main Menu
    # ======================================

    if is_start_command(text):

        await message.reply(
            WELCOME_TEXT,
            components=main_menu_keyboard()
        )

        return


    # ======================================
    # 📅 Season Admin Commands (Private + Owner only)
    # ======================================

    if is_season_command(text):
        handled = await handle_season_command(
            bot=bot,
            message=message,
            text=text,
            user_id=user_id,
            private_chat=private_chat,
        )
        if handled:
            return


    # ======================================
    # 🎮 Admin Economy: /addcoin /addpoint /addgym
    # ======================================

    admin_prefixes = (
        "/addcoin",
        "/addpoint",
        "/addgym",
        "addcoin",
        "addpoint",
        "addgym",
    )
    admin_cmd_raw = text.strip()
    admin_cmd_lower = admin_cmd_raw.lower()

    matched_admin = None
    args_part = ""
    for p in admin_prefixes:
        if admin_cmd_lower.startswith(p + " ") or admin_cmd_lower == p:
            matched_admin = p.lstrip("/").lower()
            args_part = admin_cmd_raw[len(p):].strip()
            break

    if matched_admin is not None:

        if int(user_id) != int(OWNER_ID):
            await message.reply(
                "⛔ فقط ادمین ربات می‌تواند از دستورات مدیریت اقتصاد استفاده کند."
            )
            return

        parts = args_part.split()
        if len(parts) != 2:
            await message.reply(
                "❌ فرمت نادرست.\n\n"
                "مثال:\n"
                "/addcoin 123456789 500\n"
                "/addpoint 123456789 -100\n"
                "/addgym 123456789 2"
            )
            return

        try:
            target_id = int(parts[0])
            delta = int(parts[1])
        except ValueError:
            await message.reply(
                "❌ ID و مقدار باید عدد صحیح باشند.\n\n"
                "مثال: /addcoin 123456789 500"
            )
            return

        target = db_get_user(target_id)
        if not target:
            await message.reply(
                f"❌ بازیکن با ID `{target_id}` در دیتابیس پیدا نشد."
            )
            return

        name = target["first_name"] or "Unknown"
        uname = target["username"] or ""
        label = f"@{uname}" if uname else name

        if matched_admin == "addcoin":
            old_val = int(target["meow_coins"] or 0)
            new_val = max(0, old_val + delta)
            ok, old_v, new_v = admin_set_meow_coins(target_id, new_val)
            field = "🪙 Meow Coin"
        elif matched_admin == "addpoint":
            old_val = int(target["meow_points"] or 0)
            new_val = max(0, old_val + delta)
            ok, old_v, new_v = admin_set_meow_points(target_id, new_val)
            field = "⭐ Meow Point"
        else:
            old_val = int(target["gym_level"] or 1)
            new_val = max(1, min(int(MAX_GYM_LEVEL), old_val + delta))
            ok, old_v, new_v = admin_set_gym_level(
                target_id, new_val, min_level=1, max_level=int(MAX_GYM_LEVEL)
            )
            field = "🏋️ Gym Level"

        if not ok:
            await message.reply("❌ ذخیره در دیتابیس ناموفق بود.")
            return

        sign = "+" if delta >= 0 else ""
        print(
            f"🎮 ADMIN {matched_admin} | by={user_id} target={target_id} "
            f"delta={delta} {old_v}->{new_v}"
        )

        await message.reply(
            "✅ تغییر با موفقیت اعمال شد.\n\n"
            "━━━━━━━━━━━━━━\n"
            f"👤 بازیکن: {label}\n"
            f"🆔 ID: `{target_id}`\n"
            f"📊 فیلد: {field}\n"
            f"Δ تغییر: {sign}{delta}\n"
            f"📌 قبل: {old_v}\n"
            f"📌 بعد: {new_v}\n"
            "━━━━━━━━━━━━━━"
        )
        return


    # ======================================
    # 📢 اکو (Echo)
    # ======================================
    # اکو سلام  →  ربات می‌نویسد: سلام
    # اگر ادمین باشد پیام کاربر را پاک می‌کند
    # اگر روی پیام کسی ریپلای شده باشد، ربات هم همان‌جا ریپلای می‌کند

    echo_prefixes = ("اکو ", "اکو\u200c", "اکو\n", "اکو\t", "echo ")
    echo_text = None
    stripped = text.strip()
    lower_stripped = stripped.lower()

    for pref in echo_prefixes:
        if stripped.startswith(pref) or lower_stripped.startswith(pref.lower()):
            # طول پیشوند را از روی نسخهٔ اصلی برش بزن
            # برای echo از lower استفاده می‌کنیم
            if pref.lower().startswith("echo"):
                if lower_stripped.startswith("echo "):
                    echo_text = stripped[5:].strip()
                break
            else:
                # اکو + جداکننده
                if stripped.startswith("اکو"):
                    rest = stripped[3:].lstrip(" \t\n\u200c")
                    echo_text = rest
                break

    # فقط «اکو» بدون متن → نادیده
    if echo_text is not None and echo_text == "":
        echo_text = None

    if echo_text is not None:
        # هدف ریپلای: پیام اصلی‌ای که کاربر روی آن ریپلای کرده
        reply_target = getattr(message, "reply_to_message", None)
        reply_to_id = None
        if reply_target is not None:
            reply_to_id = getattr(reply_target, "message_id", None) or getattr(
                reply_target, "id", None
            )

        # تلاش برای پاک کردن پیام کاربر (فقط اگر ربات ادمین باشد موفق می‌شود)
        try:
            if hasattr(message, "delete"):
                await message.delete()
            else:
                mid = getattr(message, "message_id", None) or getattr(message, "id", None)
                if mid is not None and chat_id is not None:
                    await bot.delete_message(chat_id, mid)
        except Exception as del_err:
            # ادمین نیست یا دسترسی حذف ندارد → بدون پاک کردن ادامه بده
            print(f"ℹ️ echo delete skipped: {del_err}")

        # ارسال متن اکو
        try:
            kwargs = {}
            if reply_to_id is not None:
                kwargs["reply_to_message_id"] = reply_to_id

            await studio_send_message(bot, chat_id, echo_text, **kwargs)
        except Exception as send_err:
            print(f"❌ echo send failed: {send_err}")
            # fallback: reply به همان پیام کاربر (اگر پاک نشده باشد)
            try:
                await message.reply(echo_text)
            except Exception:
                pass

        return


    # ======================================
    # 🐱 Pet Meow — نام‌گذاری / صدا زدن
    # ======================================

    # نام‌گذاری فقط در PV
    if private_chat:

        name_text, name_kb = try_handle_pet_name_input(
            user_id=user_id,
            text=text,
        )

        if name_text is not None:

            if name_kb is not None:
                await message.reply(
                    name_text,
                    components=name_kb,
                )
            else:
                await message.reply(name_text)

            return

    # صدا زدن Pet (PV و گروه — کارت وضعیت + امتیاز ساعتی در گروه)
    call_reply = try_call_pet(
        user_id=user_id,
        text=text,
        in_group=not private_chat,
        first_name=first_name,
        username=username,
    )

    if call_reply:

        await message.reply(call_reply)
        return

    # رفتار تصادفی فقط در PV (کم‌تکرار) — غیرمسدودکننده
    if private_chat:

        random_msg = try_random_behavior(
            user_id=user_id,
            in_group=False,
        )

        if random_msg:
            try:
                await message.reply(random_msg)
            except Exception:
                pass
            # ادامه نده تا پیام عادی کاربر دوباره پردازش نشود
            return


    # ======================================
    # 📖 Guide
    # ======================================

    if is_guide_command(text):

        await message.reply(
            get_guide()
        )

        return


    # ======================================
    # 🧠🎯💡 حقیقت / جرأت / فکت (فقط گروه)
    # ======================================

    if not private_chat:

        tdf_reply = handle_tdf(
            user_id=user_id,
            text=text,
            first_name=first_name,
            username=username,
        )

        if tdf_reply:

            await message.reply(tdf_reply)
            return


    # ======================================
    # 🏦 بانک میویی
    # ======================================

    # مبلغ واریز/برداشت در انتظار (گروه یا PV)
    bank_amount_reply = try_handle_bank_amount(
        user_id=user_id,
        text=text,
        first_name=first_name,
        username=username,
    )
    if bank_amount_reply is not None:
        await message.reply(bank_amount_reply)
        return

    if is_bank_command(text):
        bank_text, bank_kb = get_bank_page(
            user_id=user_id,
            first_name=first_name,
            username=username,
        )
        await message.reply(bank_text, components=bank_kb)
        return

    # کارت به کارت (ریپلای + مبلغ)
    card_amount = parse_card_transfer(text)
    if card_amount is not None:
        reply_message = getattr(message, "reply_to_message", None)
        if not reply_message:
            await message.reply(
                "💳 برای کارت‌به‌کارت باید روی پیام شخص ریپلای کنی.\n"
                "مثال: کارت به کارت میویی ۱۰۰"
            )
            return

        receiver = getattr(reply_message, "author", None)
        if not receiver:
            await message.reply("❌ شخص گیرنده پیدا نشد.")
            return

        receiver_id = receiver.id
        receiver_name = (
            getattr(receiver, "first_name", None) or "Unknown"
        )
        r_username = getattr(receiver, "username", None) or ""
        if r_username:
            receiver_label = f"@{r_username}"
        else:
            receiver_label = receiver_name

        sender_label = f"@{username}" if username else first_name

        tx_text = handle_card_to_card(
            sender_id=user_id,
            receiver_id=receiver_id,
            amount=card_amount,
            sender_name=sender_label,
            receiver_name=receiver_label,
        )
        await message.reply(tx_text)
        return


    # ======================================
    # 📢 Global / Admin Commands
    # ======================================

    if normalized_text.startswith("همگانی"):

        # ----------------------------------
        # Permission
        # ----------------------------------

        if int(user_id) != int(OWNER_ID):

            await message.reply(
                "⛔🐱 فقط مالک MeowBot می‌تونه "
                "از دستورات همگانی استفاده کنه."
            )

            return


        # ----------------------------------
        # Meow Point
        # ----------------------------------

        point_prefixes = (
            "همگانی میو پوینت ",
            "همگانی میو پوینت‌",
        )

        point_command = None

        for prefix in point_prefixes:

            if normalized_text.startswith(prefix):

                point_command = text[len(prefix):].strip()

                break


        if point_command is not None:

            try:

                amount = int(
                    point_command
                )

            except ValueError:

                await message.reply(
                    "❌ مقدار Meow Point باید یک عدد صحیح باشد.\n\n"
                    "مثال:\n"
                    "همگانی میو پوینت 100"
                )

                return


            if amount <= 0:

                await message.reply(
                    "❌ مقدار باید بیشتر از صفر باشد."
                )

                return


            try:

                affected_users = add_meow_points_to_all(
                    chat_id=chat_id,
                    amount=amount
                )

                await message.reply(
                    "📢🐾 همگانی Meow Point انجام شد!\n\n"
                    "━━━━━━━━━━━━━━\n"
                    f"🐾 مقدار برای هر نفر: +{amount}\n"
                    f"👥 تعداد کاربران: {affected_users}\n"
                    "━━━━━━━━━━━━━━\n\n"
                    "🐱✨ Points با موفقیت اضافه شد!"
                )

            except Exception:

                await message.reply(
                    "❌ هنگام اضافه کردن Meow Point "
                    "خطایی رخ داد."
                )

            return


        # ----------------------------------
        # Meow Coin
        # ----------------------------------

        coin_prefixes = (
            "همگانی میو کوین ",
            "همگانی میو کوین‌",
        )

        coin_command = None

        for prefix in coin_prefixes:

            if normalized_text.startswith(prefix):

                coin_command = text[len(prefix):].strip()

                break


        if coin_command is not None:

            try:

                amount = int(
                    coin_command
                )

            except ValueError:

                await message.reply(
                    "❌ مقدار Meow Coin باید یک عدد صحیح باشد.\n\n"
                    "مثال:\n"
                    "همگانی میو کوین 500"
                )

                return


            if amount <= 0:

                await message.reply(
                    "❌ مقدار باید بیشتر از صفر باشد."
                )

                return


            try:

                affected_users = add_meow_coins_to_all(
                    chat_id=chat_id,
                    amount=amount
                )

                await message.reply(
                    "📢🪙 همگانی Meow Coin انجام شد!\n\n"
                    "━━━━━━━━━━━━━━\n"
                    f"🪙 مقدار برای هر نفر: +{amount}\n"
                    f"👥 تعداد کاربران: {affected_users}\n"
                    "━━━━━━━━━━━━━━\n\n"
                    "🐱✨ Coinها با موفقیت اضافه شدند!"
                )

            except Exception:

                await message.reply(
                    "❌ هنگام اضافه کردن Meow Coin "
                    "خطایی رخ داد."
                )

            return


        # ----------------------------------
        # Text Broadcast
        # ----------------------------------

        broadcast_text = text[
            len("همگانی"):
        ].strip()


        if (
            len(broadcast_text) >= 2
            and broadcast_text[0] in {'"', "«", "'"}
            and broadcast_text[-1] in {'"', "»", "'"}
        ):

            broadcast_text = broadcast_text[
                1:-1
            ].strip()


        if not broadcast_text:

            await message.reply(
                "📢🐱 متن همگانی خالیه!\n\n"
                "مثال:\n"
                'همگانی "سلام بچه‌ها 🐱💗"'
            )

            return


        # ----------------------------------
        # Get Registered Groups
        # ----------------------------------

        try:

            groups = get_all_groups()

        except Exception as e:

            print(
                f"❌ Failed to load groups: {e}"
            )

            await message.reply(
                "❌ نتونستم لیست گروه‌ها رو از دیتابیس بگیرم."
            )

            return


        # ----------------------------------
        # No Groups
        # ----------------------------------

        if not groups:

            await message.reply(
                "📢🐱 هنوز هیچ گروهی برای Broadcast "
                "در دیتابیس ثبت نشده."
            )

            return


        # ----------------------------------
        # Send To All Groups
        # ----------------------------------

        sent = 0
        failed = 0

        total_groups = len(
            groups
        )


        for group in groups:

            group_id = group["chat_id"]

            try:

                await studio_send_message(bot, 
                    group_id,
                    broadcast_text
                )

                sent += 1

                print(
                    f"✅ Broadcast sent -> {group_id}"
                )

            except Exception as e:

                failed += 1

                print(
                    f"❌ Broadcast failed -> "
                    f"{group_id}: {e}"
                )


        # ----------------------------------
        # Broadcast Report
        # ----------------------------------

        await message.reply(
            "📢🐱 همگانی ارسال شد!\n\n"
            "━━━━━━━━━━━━━━\n"
            f"👥 کل گروه‌های ثبت‌شده: {total_groups}\n"
            f"✅ ارسال موفق: {sent}\n"
            f"❌ ارسال ناموفق: {failed}\n"
            "━━━━━━━━━━━━━━"
        )

        return


    # ======================================
    # 👤 Profile
    # ======================================

    if normalized_text in {
        "پروفایل",
        "پروفایل میویی",
        "profile",
        "me",
    }:

        target_user = author

        reply_message = getattr(
            message,
            "reply_to_message",
            None
        )


        if reply_message:

            replied_author = getattr(
                reply_message,
                "author",
                None
            )

            if replied_author:

                target_user = replied_author


        target_user_id = target_user.id

        target_first_name = (
            getattr(
                target_user,
                "first_name",
                None
            )
            or "Unknown"
        )

        target_username = (
            getattr(
                target_user,
                "username",
                None
            )
            or ""
        )


        profile_text = format_profile(
            user_id=target_user_id,
            chat_id=chat_id,
            first_name=target_first_name,
            username=target_username
        )


        await message.reply(
            profile_text
        )

        return


    # ======================================
    # 🪙 Coin Transfer
    # ======================================

    amount = parse_transfer_command(
        normalized_text
    )


    if amount is not None:

        reply_message = getattr(
            message,
            "reply_to_message",
            None
        )


        if not reply_message:

            await message.reply(
                "🪙🐱 برای انتقال Meow Coin باید "
                "روی پیام شخص موردنظر ریپلای کنی.\n\n"
                "مثال:\n"
                "انتقال میویی 10"
            )

            return


        receiver = getattr(
            reply_message,
            "author",
            None
        )


        if not receiver:

            await message.reply(
                "❌ نتونستم شخص موردنظر رو پیدا کنم."
            )

            return


        receiver_id = receiver.id

        receiver_name = (
            getattr(
                receiver,
                "first_name",
                None
            )
            or "Unknown"
        )


        result = transfer_coins(
            sender_id=user_id,
            receiver_id=receiver_id,
            chat_id=chat_id,
            amount=amount
        )


        if not result["success"]:

            reason = result.get(
                "reason"
            )


            if reason == "self_transfer":

                await message.reply(
                    "😂🪙 نمی‌تونی به خودت "
                    "Meow Coin انتقال بدی!"
                )

                return


            if reason == "not_enough_coins":

                current_coins = result.get(
                    "sender_coins",
                    0
                )

                await message.reply(
                    "🥺🪙 موجودی Meow Coin کافی نیست.\n\n"
                    f"💰 موجودی تو: {current_coins}\n"
                    f"📤 مبلغ انتقال: {amount}\n"
                    f"❌ کمبود: "
                    f"{amount - current_coins}"
                )

                return


            if reason == "sender_not_found":

                await message.reply(
                    "❌ اطلاعات حساب تو پیدا نشد."
                )

                return


            if reason == "receiver_not_found":

                await message.reply(
                    "❌ این شخص هنوز حساب MeowBot نداره."
                )

                return


            await message.reply(
                "❌ انتقال انجام نشد.\n"
                "لطفاً دوباره تلاش کن."
            )

            return


        await message.reply(
            "🪙✨ انتقال موفق بود!\n\n"
            "━━━━━━━━━━━━━━\n"
            f"👤 گیرنده: {receiver_name}\n"
            f"💸 مبلغ انتقال: {amount} Meow Coin\n"
            "━━━━━━━━━━━━━━\n\n"
            f"💰 موجودی تو: "
            f"{result['sender_coins']}\n"
            f"💰 موجودی گیرنده: "
            f"{result['receiver_coins']}\n\n"
            "🐱💗 انتقال با موفقیت انجام شد!"
        )

        return


    # ======================================
    # ⚔️ Battle
    # ======================================

    if normalized_text in {
        "جنگ میویی",
        "جنگ میویی!",
        "جنگ میو",
        "جنگ",
        "meow battle",
        "battle",
    }:

        reply_message = getattr(
            message,
            "reply_to_message",
            None
        )


        if not reply_message:

            await message.reply(
                "⚔️🐱 برای جنگ میویی باید "
                "روی پیام حریف ریپلای کنی!"
            )

            return


        defender = getattr(
            reply_message,
            "author",
            None
        )


        if not defender:

            await message.reply(
                "❌ نتونستم صاحب این پیام رو پیدا کنم."
            )

            return


        defender_id = defender.id


        result = start_battle(
            attacker_id=user_id,
            defender_id=defender_id,
            chat_id=chat_id
        )


        if not result["success"]:

            if result.get(
                "reason"
            ) == "self_battle":

                await message.reply(
                    "😂🐱 نمی‌تونی با خودت بجنگی!"
                )

                return

            if result.get(
                "reason"
            ) == "cooldown":

                remaining_text = format_battle_cooldown(
                    result["remaining"]
                )
                cooldown_msg = result.get(
                    "message",
                    "🐱 هنوز خیلی خسته‌ای! یه کم استراحت کن 😴"
                )

                await message.reply(
                    f"{cooldown_msg}\n\n"
                    f"⏳ زمان باقی‌مانده:\n"
                    f"{remaining_text}"
                )

                return


            await message.reply(
                "❌ جنگ میویی انجام نشد."
            )

            return


        winner_name = result["winner_name"]
        loser_name = result["loser_name"]

        winner_reward = result["winner_reward"]
        loser_reward = result["loser_reward"]

        attacker_level = result["attacker_level"]
        defender_level = result["defender_level"]


        await message.reply(
            "⚔️🐱 نبرد میویی!\n\n"
            "━━━━━━━━━━━━━━\n"
            f"👤 مهاجم: "
            f"{result['attacker_name']}\n"
            f"🏋️ Level: "
            f"{attacker_level}\n"
            f"🛡️ مدافع: "
            f"{result['defender_name']}\n"
            f"🏋️ Level: "
            f"{defender_level}\n"
            "━━━━━━━━━━━━━━\n\n"
            f"🏆 برنده: {winner_name}\n"
            f"💥 بازنده: {loser_name}\n\n"
            f"🪙 پاداش برنده: "
            f"+{winner_reward} Meow Coin\n"
            f"🪙 پاداش بازنده: "
            f"+{loser_reward} Meow Coin\n\n"
            "🐱⚡ نبرد به پایان رسید!"
        )

        return


    # ======================================
    # 🏆 Ranking
    # ======================================

    if normalized_text in {
        "رنکینگ",
        "رنکینگ میویی",
        "رتبه بندی",
        "رتبه‌بندی",
        "ranking",
        "rank",
    }:

        ranking_text = format_ranking(
            chat_id=chat_id
        )


        await message.reply(
            ranking_text
        )

        return


    # ======================================
    # 👤 My Rank
    # ======================================

    if normalized_text in {
        "رتبه من",
        "رنک من",
        "my rank",
        "my ranking",
    }:

        rank = get_user_rank(
            user_id=user_id,
            chat_id=chat_id
        )


        if not rank:

            await message.reply(
                f"🐱🎀 {first_name}\n\n"
                "هنوز توی رنکینگ نیستی!\n"
                "یه میو بزن تا وارد رقابت بشی 🐾✨"
            )

            return


        await message.reply(
            f"🏆🎀 رتبه تو\n\n"
            f"🐱 {first_name}\n\n"
            f"🥇 رتبه: #{rank['rank']}\n"
            f"🐾 Meow Point: {rank['meow_points']}\n"
            f"🏋️ Gym Level: {rank['gym_level']}\n\n"
            "ادامه بده، شاید قهرمان میویی بشی! ✨"
        )

        return


    # ======================================
    # 🏋️ Meow Gym
    # ======================================

    if normalized_text in {
        "باشگاه میویی",
        "باشگاه میو",
        "باشگاه",
        "gym",
        "meow gym",
    }:

        status = get_gym_status(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )


        if status["max_level"]:

            await message.reply(
                f"🎀🏋️‍♀️ باشگاه میویی {first_name}\n\n"
                f"✨ Level: {status['level']} / 100\n"
                f"⚡ قدرت: {status['power']}\n"
                f"🐾 Meow Point: {status['points']}\n\n"
                "🌸 به آخرین Level رسیدی!\n"
                "دیگه قوی‌تر از این نمی‌شه شد 😭💗"
            )

        else:

            await message.reply(
                "🎀🏋️‍♀️ باشگاه میویی\n\n"
                f"🐱 {first_name}\n\n"
                f"✨ Level: {status['level']} / 100\n"
                f"⚡ قدرت: {status['power']}\n"
                f"🐾 Meow Point: {status['points']}\n\n"
                f"⬆️ ارتقای بعدی: "
                f"Level {status['level'] + 1}\n"
                f"💸 هزینه: "
                f"{status['upgrade_cost']} Meow Point\n\n"
                "برای ارتقا بنویس:\n"
                "💪 ارتقا باشگاه"
            )

        return


    # ======================================
    # ⬆️ Gym Upgrade
    # ======================================

    if normalized_text in {
        "ارتقا باشگاه",
        "ارتقای باشگاه",
        "ارتقا",
        "upgrade gym",
        "gym upgrade",
    }:

        result = upgrade_gym(
            user_id=user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username
        )


        if result["reason"] == "max_level":

            await message.reply(
                "👑🏋️‍♀️ وااای!\n\n"
                f"🐱 {first_name}، "
                "باشگاهت به Level 100 رسیده!\n\n"
                "✨ Level: 100 / 100\n"
                f"⚡ قدرت: {result['power']}\n\n"
                "دیگه رسماً استاد میویی هستی 😭🎀"
            )

            return


        if result["reason"] == "not_enough_points":

            needed = (
                result["cost"]
                - result["points"]
            )

            await message.reply(
                "🥺🎀 اوپس!\n\n"
                "برای ارتقای باشگاهت "
                "Meow Point کافی نداری.\n\n"
                f"🐾 موجودی: {result['points']}\n"
                f"💸 نیاز: {result['cost']}\n"
                f"🌸 کمبود: {needed}\n\n"
                "برو چندتا میوی خوشگل بکن 🐱💗"
            )

            return


        await message.reply(
            "🎀✨ LEVEL UP! ✨🎀\n\n"
            f"🐱 {first_name}\n\n"
            f"🏋️‍♀️ Level: "
            f"{result['level']} → "
            f"{result['new_level']}\n\n"
            f"⚡ قدرت جدید: "
            f"{result['power']}\n\n"
            f"🐾 Meow Point باقی‌مانده: "
            f"{result['points']}\n\n"
            "تو قوی‌تر شدییی 😭💗"
        )

        return


    # ======================================
    # 🐾 Meow
    # ======================================

    if not is_meow(text):
        return


    result = register_meow(
        user_id=user_id,
        chat_id=chat_id,
        first_name=first_name,
        username=username
    )


    if not result["success"]:

        remaining = format_cooldown(
            result["remaining"]
        )

        await message.reply(
            "🎀 وایسا کوچولو 🐱💗\n\n"
            "میوی بعدیت هنوز آماده نیست!\n"
            f"⏰ {remaining} دیگه می‌تونی میو کنی ✨"
        )

        return


    points = result["points"]
    earned = result["earned"]


    await message.reply(
        "🐱✨ میوووو!\n\n"
        f"🎀 {first_name}، خوش‌شانس بودی!\n"
        f"🐾 جایزه این میو: +{earned}\n"
        f"🌸 مجموع Meow Point: {points}\n"
        "💗 میوی بعدی: ۵ دقیقه دیگه"
    )


# ==========================================
# Callback Queries (Main Menu)
# ==========================================

@bot.event
async def on_callback(callback: CallbackQuery):

    data = getattr(callback, "data", None)
    user = getattr(callback, "from_user", None) or getattr(callback, "user", None)
    cb_message = getattr(callback, "message", None)

    try:
        if hasattr(callback, "answer"):
            await callback.answer()
    except Exception:
        pass

    if not user:
        return

    user_id = getattr(user, "id", None)
    if user_id is None:
        return

    first_name = getattr(user, "first_name", None) or ""
    username = getattr(user, "username", None) or ""

    # --------------------------------------
    # Pet callbacks
    # --------------------------------------
    if is_pet_callback(data):

        text, keyboard = handle_pet_callback(
            data=data,
            user_id=user_id,
            first_name=first_name,
            username=username,
        )

        if not cb_message:
            return

        try:
            if hasattr(cb_message, "edit"):
                await cb_message.edit(
                    text,
                    components=keyboard
                )
            elif hasattr(cb_message, "edit_text"):
                await cb_message.edit_text(
                    text,
                    components=keyboard
                )
            else:
                await studio_send_message(bot, 
                    getattr(cb_message.chat, "id", user_id),
                    text,
                    components=keyboard
                )
        except Exception as e:
            print(f"❌ Pet callback edit failed: {e}")
            try:
                chat_id = getattr(
                    getattr(cb_message, "chat", None), "id", None
                )
                if chat_id is None:
                    chat_id = user_id
                await studio_send_message(bot, 
                    chat_id,
                    text,
                    components=keyboard
                )
            except Exception as send_error:
                print(f"❌ Pet callback send failed: {send_error}")

        return

    # --------------------------------------
    # Bank callbacks
    # --------------------------------------
    if is_bank_callback(data):

        text, keyboard = handle_bank_callback(
            data=data,
            user_id=user_id,
            first_name=first_name,
            username=username,
        )

        if not cb_message:
            return

        try:
            if hasattr(cb_message, "edit"):
                await cb_message.edit(
                    text,
                    components=keyboard
                )
            elif hasattr(cb_message, "edit_text"):
                await cb_message.edit_text(
                    text,
                    components=keyboard
                )
            else:
                await studio_send_message(bot, 
                    getattr(cb_message.chat, "id", user_id),
                    text,
                    components=keyboard
                )
        except Exception as e:
            print(f"❌ Bank callback edit failed: {e}")
            try:
                chat_id = getattr(
                    getattr(cb_message, "chat", None), "id", None
                )
                if chat_id is None:
                    chat_id = user_id
                await studio_send_message(bot, 
                    chat_id,
                    text,
                    components=keyboard
                )
            except Exception as send_error:
                print(f"❌ Bank callback send failed: {send_error}")

        return

    # --------------------------------------
    # Main menu callbacks
    # --------------------------------------
    if not is_menu_callback(data):
        return

    text, keyboard = get_menu_page(data, user)

    if not cb_message:
        return

    try:
        if hasattr(cb_message, "edit"):
            await cb_message.edit(
                text,
                components=keyboard
            )
        elif hasattr(cb_message, "edit_text"):
            await cb_message.edit_text(
                text,
                components=keyboard
            )
        else:
            await studio_send_message(bot, 
                getattr(cb_message.chat, "id", user.id),
                text,
                components=keyboard
            )
    except Exception as e:
        print(f"❌ Menu callback edit failed: {e}")
        try:
            chat_id = getattr(getattr(cb_message, "chat", None), "id", None)
            if chat_id is None:
                chat_id = user.id
            await studio_send_message(bot, 
                chat_id,
                text,
                components=keyboard
            )
        except Exception as send_error:
            print(f"❌ Menu callback send failed: {send_error}")


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":
    bot.run()
