# ==========================================
# 🐱 MeowBot - Main
# ==========================================

from bale import Bot, Message

from config import (
    BOT_TOKEN,
    ALLOWED_GROUP,
    OWNER_ID,
)

from database import (
    init_database,
    add_meow_points_to_all,
    add_meow_coins_to_all,
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
)

from profile import (
    format_profile,
)

from coins import (
    parse_transfer_command,
    transfer_coins,
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


# ==========================================
# Ready
# ==========================================

@bot.event
async def on_ready():

    print("=" * 55)
    print("🐱 MEOWBOT ONLINE")
    print("=" * 55)

    print(
        f"🎀 Group: {ALLOWED_GROUP}"
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

    print("=" * 55)


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
                amount = int(point_command)

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
                amount = int(coin_command)

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

        broadcast_text = text[len("همگانی"):].strip()

        # اگر متن داخل کوتیشن باشد
        if (
            len(broadcast_text) >= 2
            and broadcast_text[0] in {'"', "«", "'"}
            and broadcast_text[-1] in {'"', "»", "'"}
        ):
            broadcast_text = broadcast_text[1:-1].strip()

        if not broadcast_text:

            await message.reply(
                "📢🐱 متن همگانی خالیه!\n\n"
                "مثال:\n"
                'همگانی "سلام بچه‌ها 🐱💗"'
            )

            return

        await message.reply(
            broadcast_text
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
                    "😂🪙 نمی‌تونی به خودت Meow Coin انتقال بدی!"
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

            if result.get("reason") == "self_battle":

                await message.reply(
                    "😂🐱 نمی‌تونی با خودت بجنگی!"
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
            f"{attacker_level}\n\n"
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
                f"هنوز توی رنکینگ نیستی!\n"
                f"یه میو بزن تا وارد رقابت بشی 🐾✨"
            )

            return

        await message.reply(
            f"🏆🎀 رتبه تو\n\n"
            f"🐱 {first_name}\n\n"
            f"🥇 رتبه: #{rank['rank']}\n"
            f"🐾 Meow Point: {rank['meow_points']}\n"
            f"🏋️ Gym Level: {rank['gym_level']}\n\n"
            f"ادامه بده، شاید قهرمان میویی بشی! ✨"
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
                f"🌸 به آخرین Level رسیدی!\n"
                f"دیگه قوی‌تر از این نمی‌شه شد 😭💗"
            )

        else:

            await message.reply(
                f"🎀🏋️‍♀️ باشگاه میویی\n\n"
                f"🐱 {first_name}\n\n"
                f"✨ Level: {status['level']} / 100\n"
                f"⚡ قدرت: {status['power']}\n"
                f"🐾 Meow Point: {status['points']}\n\n"
                f"⬆️ ارتقای بعدی: "
                f"Level {status['level'] + 1}\n"
                f"💸 هزینه: "
                f"{status['upgrade_cost']} Meow Point\n\n"
                f"برای ارتقا بنویس:\n"
                f"💪 ارتقا باشگاه"
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
                f"👑🏋️‍♀️ وااای!\n\n"
                f"🐱 {first_name}، "
                f"باشگاهت به Level 100 رسیده!\n\n"
                f"✨ Level: 100 / 100\n"
                f"⚡ قدرت: {result['power']}\n\n"
                f"دیگه رسماً استاد میویی هستی 😭🎀"
            )

            return

        if result["reason"] == "not_enough_points":

            needed = (
                result["cost"]
                - result["points"]
            )

            await message.reply(
                f"🥺🎀 اوپس!\n\n"
                f"برای ارتقای باشگاهت "
                f"Meow Point کافی نداری.\n\n"
                f"🐾 موجودی: {result['points']}\n"
                f"💸 نیاز: {result['cost']}\n"
                f"🌸 کمبود: {needed}\n\n"
                f"برو چندتا میوی خوشگل بکن 🐱💗"
            )

            return

        await message.reply(
            f"🎀✨ LEVEL UP! ✨🎀\n\n"
            f"🐱 {first_name}\n\n"
            f"🏋️‍♀️ Level: "
            f"{result['level']} → "
            f"{result['new_level']}\n\n"
            f"⚡ قدرت جدید: "
            f"{result['power']}\n\n"
            f"🐾 Meow Point باقی‌مانده: "
            f"{result['points']}\n\n"
            f"تو قوی‌تر شدییی 😭💗"
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
            f"🎀 وایسا کوچولو 🐱💗\n\n"
            f"میوی بعدیت هنوز آماده نیست!\n"
            f"⏰ {remaining} دیگه می‌تونی میو کنی ✨"
        )

        return

    points = result["points"]
    earned = result["earned"]

    await message.reply(
        f"🐱✨ میوووو!\n\n"
        f"🎀 {first_name}، خوش‌شانس بودی!\n\n"
        f"🐾 جایزه این میو: +{earned}\n"
        f"🌸 مجموع Meow Point: {points}\n"
        f"💗 میوی بعدی: ۵ دقیقه دیگه"
    )


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":
    bot.run()