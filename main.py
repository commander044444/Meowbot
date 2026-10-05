# ==========================================
# 🐱 MeowBot v2.0 — Main (Glass UI + PostgreSQL)
# ==========================================

import logging
import time
import traceback

from bale import Bot, Message, CallbackQuery

from config import BOT_TOKEN, OWNER_ID, BOT_NAME, BOT_VERSION, MAX_GYM_LEVEL

from database import init_database
from database.users import (
    create_user, get_user,
    admin_set_meow_coins, admin_set_meow_points, admin_set_gym_level,
)
from database.groups import register_group, set_interaction
from database.admins import is_owner, has_permission
from database.logs import log_action
from database.achievements import seed_achievements
from database.missions import seed_missions
from database.inventory import seed_shop, get_shop_items, add_item
from database.users import spend_meow_coins, get_meow_coins

from core.meow import is_meow, is_allowed_group, register_meow
from core.menu import WELCOME, handle_menu_callback
from utils.keyboards import main_menu_kb, shop_kb, back_main_kb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("meowbot")

bot = Bot(token=BOT_TOKEN)
_start_time = time.time()


async def _edit_or_reply(target, text, kb=None):
    """Edit callback message or reply."""
    try:
        if hasattr(target, "edit") and kb is not None:
            await target.edit(text, components=kb)
            return
        if hasattr(target, "edit") and kb is None:
            await target.edit(text)
            return
        if hasattr(target, "edit_text"):
            if kb is not None:
                await target.edit_text(text, components=kb)
            else:
                await target.edit_text(text)
            return
    except Exception as e:
        logger.debug(f"edit failed: {e}")
    try:
        if hasattr(target, "reply"):
            if kb is not None:
                await target.reply(text, components=kb)
            else:
                await target.reply(text)
    except Exception as e:
        logger.warning(f"reply failed: {e}")


@bot.event
async def on_ready():
    print("=" * 55)
    print(f"🐱 {BOT_NAME} v{BOT_VERSION} ONLINE (Glass UI)")
    print("=" * 55)
    try:
        await init_database()
        await seed_achievements()
        await seed_missions()
        await seed_shop()
        print("✅ Database + seeds ready")
    except Exception as e:
        print(f"❌ Database init failed: {e}")
        traceback.print_exc()

    try:
        from guides.scheduler import start_guide_scheduler
        start_guide_scheduler(bot)
        print("✅ Auto Guide scheduler")
    except Exception as e:
        print(f"⚠️ Guide scheduler: {e}")

    try:
        from seasons.scheduler import start_season_scheduler
        start_season_scheduler(bot)
        print("✅ Season scheduler")
    except Exception as e:
        print(f"⚠️ Season scheduler: {e}")

    print(f"👑 Owner: {OWNER_ID}")
    print("=" * 55)


@bot.event
async def on_message(message: Message):
    try:
        text = message.text
        if not text:
            return
        text = text.strip()

        chat = message.chat
        chat_id = getattr(chat, "id", None)
        chat_username = getattr(chat, "username", None)
        chat_title = getattr(chat, "title", None) or ""
        author = message.author
        if not author:
            return

        user_id = int(author.id)
        first_name = getattr(author, "first_name", None) or "Unknown"
        username = getattr(author, "username", None) or ""
        # تشخیص PV: در بله ممکن است username داشته باشد؛ title فقط برای گروه/کانال است
        chat_type = str(getattr(chat, "type", None) or getattr(chat, "chat_type", None) or "").lower()
        if chat_type in ("private", "user", "pv", "dm"):
            private = True
        elif chat_type in ("group", "supergroup", "channel"):
            private = False
        else:
            # fallback: گروه معمولاً title دارد
            private = not bool(chat_title)

        if chat_id and (chat_title or chat_username):
            try:
                await register_group(chat_id, chat_title, chat_username or "")
            except Exception:
                pass

        try:
            await create_user(int(user_id), first_name=first_name, username=username, chat_id=chat_id)
        except Exception:
            pass

        # ---- Start / Menu (Glass) ----
        if text in ("/start", "start", "منو", "شروع", "/menu"):
            try:
                kb = main_menu_kb()
                await message.reply(WELCOME, components=kb)
            except Exception as e:
                logger.error(f"start menu kb error: {e}")
                # fallback without keyboard so user is not stuck
                await message.reply(
                    WELCOME + "\n\n⚠️ منوی دکمه‌ای موقتاً در دسترس نیست.\n"
                    f"خطا: `{type(e).__name__}`"
                )
            return

        # ---- Owner Panel ----
        if text in ("/owner", "owner", "پنل مالک", "👑") and await is_owner(user_id):
            from admin.panel import show_owner_panel
            await show_owner_panel(message)
            return

        # ---- تنظیمات گروه (ادمین گروه در PV) ----
        if private and text in (
            "تنظیم گروه", "تنظیمات گروه", "/groupsettings", "/group",
            "groupsettings", "تنظیمات ربات",
        ):
            from core.group_settings import show_group_list
            txt, kb = await show_group_list(int(user_id))
            await message.reply(txt, components=kb)
            return

        # ---- Pet name input (همیشه اگر awaiting — حتی اگر تشخیص PV اشتباه باشد) ----
        try:
            from pet.system import handle_name_input, try_call_pet
            name_text, name_kb = await handle_name_input(int(user_id), text)
            if name_text is not None:
                try:
                    if name_kb is not None:
                        await message.reply(name_text, components=name_kb)
                    else:
                        await message.reply(name_text)
                except Exception as e:
                    logger.error(f"pet name reply failed: {e}")
                    await message.reply(name_text)
                return
            if private:
                call = await try_call_pet(int(user_id), text)
                if call:
                    await message.reply(call)
                    return
        except Exception as e:
            logger.error(f"pet name handler error: {e}")
            import traceback as _tb
            _tb.print_exc()
            # به Owner خطا را نشان بده تا silent نماند
            try:
                if int(user_id) == int(OWNER_ID):
                    await message.reply(f"⚠️ pet name error: `{e}`")
            except Exception:
                pass

        # ---- Owner pending text (broadcast, add admin, economy, ...) ----
        if await is_owner(user_id):
            from admin.panel import handle_owner_text
            handled = await handle_owner_text(bot, message, int(user_id), text)
            if handled:
                return

        # ---- Admin economy ----
        lower = text.lower()
        for p in ("/addcoin", "/addpoint", "/addgym", "addcoin", "addpoint", "addgym"):
            if lower.startswith(p + " ") or lower == p:
                if not await is_owner(user_id):
                    await message.reply("⛔ فقط Owner.")
                    return
                parts = text[len(p):].strip().split()
                if len(parts) != 2:
                    await message.reply("❌ `/addcoin USER_ID AMOUNT`")
                    return
                try:
                    tid, delta = int(parts[0]), int(parts[1])
                except ValueError:
                    await message.reply("❌ عدد نامعتبر.")
                    return
                target = await get_user(tid)
                if not target:
                    await message.reply(f"❌ کاربر `{tid}` نیست.")
                    return
                cmd = p.lstrip("/").lower()
                if cmd == "addcoin":
                    old = int(target.get("meow_coins") or 0)
                    ok, o, n = await admin_set_meow_coins(tid, max(0, old + delta))
                    field = "🪙"
                elif cmd == "addpoint":
                    old = int(target.get("meow_points") or 0)
                    ok, o, n = await admin_set_meow_points(tid, max(0, old + delta))
                    field = "⭐"
                else:
                    old = int(target.get("gym_level") or 1)
                    ok, o, n = await admin_set_gym_level(tid, max(1, min(MAX_GYM_LEVEL, old + delta)))
                    field = "🏋️"
                await log_action(user_id, cmd, str(tid), {"delta": delta, "old": o, "new": n})
                await message.reply(f"✅ {field} `{tid}`\n{o} → {n}", components=main_menu_kb())
                return


        # ---- Bank pending amount ----
        from economy.bank_ui import handle_amount_input
        bank_text, bank_kb = await handle_amount_input(user_id, text)
        if bank_text is not None:
            if bank_kb:
                await message.reply(bank_text, components=bank_kb)
            else:
                await message.reply(bank_text)
            return

        # ---- Games guess input ----
        from games.system import handle_guess_input
        g_text, g_kb = await handle_guess_input(user_id, text)
        if g_text is not None:
            if g_kb:
                await message.reply(g_text, components=g_kb)
            else:
                await message.reply(g_text)
            return

        # ---- Meow ----
        if is_meow(text):
            if not private and not is_allowed_group(chat_id, chat_username):
                return
            # در گروه: اگر ادمین گروه میو را خاموش کرده، جواب نده
            if not private and chat_id is not None:
                try:
                    from database.groups import get_meow_enabled
                    if not await get_meow_enabled(chat_id):
                        return
                except Exception:
                    pass
            ok, msg, pts = await register_meow(int(user_id), first_name, username, chat_id)
            # در گروه کیبورد اصلی شلوغ است — بدون منو جواب بده
            if private:
                await message.reply(msg, components=main_menu_kb())
            else:
                await message.reply(msg)
            return

        # ---- Text shortcuts (still open glass menu) ----
        shortcuts = {
            "پروفایل": "menu:profile", "profile": "menu:profile", "/profile": "menu:profile",
            "رنکینگ": "menu:rank", "رتبه": "menu:rank", "ranking": "menu:rank",
            "راهنما": "menu:guide", "help": "menu:guide", "/help": "menu:guide",
            "پت": "pet:home", "pet": "pet:home",
            "بتل": "battle:home", "battle": "battle:home", "نبرد": "battle:home",
            "بانک": "bank:home", "bank": "bank:home",
            "فروشگاه": "shop:home", "shop": "shop:home",
            "بازی": "games:home", "games": "games:home",
            "روزانه": "menu:daily", "daily": "menu:daily",
        }
        key = text.lower() if text.isascii() else text
        if key in shortcuts or text in shortcuts:
            data = shortcuts.get(text) or shortcuts.get(key)
            await _route_callback_data(message, user_id, data, first_name, username)
            return

        # Interaction toggle
        if text in ("interaction on", "اینترکشن روشن", "/interaction_on"):
            if await has_permission(user_id, "groups.edit") or await is_owner(user_id):
                await set_interaction(chat_id, True)
                await message.reply("✅ Interaction روشن شد.", components=main_menu_kb())
            return
        if text in ("interaction off", "اینترکشن خاموش", "/interaction_off"):
            if await has_permission(user_id, "groups.edit") or await is_owner(user_id):
                await set_interaction(chat_id, False)
                await message.reply("🔇 Interaction خاموش (Guide مستقل است).", components=main_menu_kb())
            return

    except Exception as e:
        logger.error(f"on_message: {e}")
        traceback.print_exc()
        try:
            if int(getattr(message.author, "id", 0)) == int(OWNER_ID):
                await message.reply(f"⚠️ {e}")
        except Exception:
            pass


async def _route_callback_data(message, user_id, data, first_name="", username=""):
    """Route as if callback pressed (from text shortcut)."""
    text, kb = await _dispatch(user_id, data, first_name, username)
    if kb is not None:
        await message.reply(text, components=kb)
    else:
        await message.reply(text)


async def _dispatch(user_id, data: str, first_name="", username=""):
    # Menu
    if data.startswith("menu:") or data.startswith("act:") or data.startswith("rank:"):
        return await handle_menu_callback(user_id, data, first_name)

    # Pet
    if data.startswith("pet:"):
        from pet.system import handle_pet_callback
        return await handle_pet_callback(user_id, data, first_name, username)

    # Battle
    if data.startswith("battle:"):
        from battle.system import handle_battle_callback
        return await handle_battle_callback(user_id, data, first_name)

    # Bank
    if data.startswith("bank:"):
        from economy.bank_ui import handle_bank_callback
        return await handle_bank_callback(user_id, data)

    # Games
    if data.startswith("games:"):
        from games.system import handle_games_callback
        return await handle_games_callback(user_id, data)

    # Shop
    if data == "shop:home":
        items = await get_shop_items()
        if not items:
            return "🛒 فروشگاه خالی است.", back_main_kb()
        lines = ["🛒 **فروشگاه میویی**\n━━━━━━━━━━━━━━"]
        for it in items:
            lines.append(f"• {it.get('name')} — `{it.get('price')}`🪙 ({it.get('rarity')})")
        return "\n".join(lines), shop_kb(items)

    if data.startswith("shop:buy:"):
        item_id = data.split(":", 2)[-1]
        items = await get_shop_items()
        item = next((i for i in items if i["item_id"] == item_id), None)
        if not item:
            return "❌ آیتم پیدا نشد.", back_main_kb()
        price = int(item["price"])
        if await get_meow_coins(user_id) < price:
            return f"❌ کوین کافی نیست. قیمت: `{price}`", shop_kb(items)
        if not await spend_meow_coins(user_id, price):
            return "❌ خطا در پرداخت.", shop_kb(items)
        await add_item(user_id, item_id, item.get("item_type") or "item", 1, item.get("effect") or {})
        return f"✅ **{item.get('name')}** خریدی!\n🪙 -{price}", shop_kb(items)

    if data == "shop:inv":
        from database.inventory import get_inventory
        inv = await get_inventory(user_id)
        if not inv:
            return "🎒 اینونتوری خالی است.", back_main_kb()
        lines = ["🎒 **اینونتوری**\n━━━━━━━━━━━━━━"]
        for it in inv:
            lines.append(f"• {it.get('item_id')} ×{it.get('quantity')}")
        return "\n".join(lines), back_main_kb()

    return WELCOME, main_menu_kb()


@bot.event
async def on_callback(callback: CallbackQuery):
    try:
        data = (callback.data or "").strip()
        user = callback.from_user
        if not user:
            return
        user_id = user.id
        first_name = getattr(user, "first_name", None) or ""
        username = getattr(user, "username", None) or ""
        msg = callback.message

        # Group settings (group admins)
        if data.startswith("gset:"):
            from core.group_settings import handle_gset_callback
            text, kb = await handle_gset_callback(bot, int(user_id), data)
            await _edit_or_reply(msg, text, kb)
            try:
                await callback.answer()
            except Exception:
                pass
            return

        # Owner panel
        if data.startswith("owner:"):
            if not await is_owner(user_id):
                await callback.answer("⛔ فقط Owner", show_alert=True)
                return
            from admin.panel import handle_owner_callback
            await handle_owner_callback(bot, callback, data)
            return

        text, kb = await _dispatch(user_id, data, first_name, username)
        await _edit_or_reply(msg, text, kb)
        try:
            await callback.answer()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"callback: {e}")
        traceback.print_exc()
        try:
            await callback.answer("خطا!", show_alert=True)
        except Exception:
            pass


if __name__ == "__main__":
    print(f"Starting {BOT_NAME} v{BOT_VERSION}...")
    bot.run()
