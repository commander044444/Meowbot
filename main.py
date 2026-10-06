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
from database.admins import is_owner, is_admin, has_permission, get_admin
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
    """Edit message if possible, otherwise reply. Never silent."""
    if text is None:
        text = "…"
    text = str(text)
    # 1) try edit
    for method_name in ("edit_text", "edit"):
        method = getattr(target, method_name, None)
        if not callable(method):
            continue
        try:
            if kb is not None:
                await method(text, components=kb)
            else:
                await method(text)
            return True
        except TypeError:
            try:
                # some versions: edit(content=..., components=...)
                if kb is not None:
                    await method(content=text, components=kb)
                else:
                    await method(content=text)
                return True
            except Exception as e:
                logger.debug(f"{method_name} type fallback: {e}")
        except Exception as e:
            logger.debug(f"{method_name} failed: {e}")
    # 2) reply on same message object
    try:
        if hasattr(target, "reply") and callable(target.reply):
            if kb is not None:
                await target.reply(text, components=kb)
            else:
                await target.reply(text)
            return True
    except Exception as e:
        logger.warning(f"reply on target failed: {e}")
    # 3) bot.send_message via chat
    try:
        chat = getattr(target, "chat", None)
        chat_id = getattr(chat, "id", None) if chat else None
        if chat_id is not None:
            if kb is not None:
                await bot.send_message(chat_id, text, components=kb)
            else:
                await bot.send_message(chat_id, text)
            return True
    except Exception as e:
        logger.warning(f"send_message fallback failed: {e}")
    return False




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
        text = getattr(message, 'text', None) or getattr(message, 'content', None)
        if not text:
            return
        text = str(text).strip()

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

        # ثبت گروه + عضویت کاربر در گروه (برای لیست تنظیمات گروه)
        if chat_id and not private:
            try:
                from database.groups import register_group, register_group_user
                await register_group(chat_id, chat_title, chat_username or "")
                await register_group_user(int(user_id), chat_id)
            except Exception as e:
                logger.debug(f"register group/user: {e}")

        try:
            await create_user(int(user_id), first_name=first_name, username=username, chat_id=chat_id)
        except Exception:
            pass

        # ---- بن: فقط پشتیبانی ----
        try:
            from database.bans import is_banned, get_active_ban
            if await is_banned(int(user_id)):
                from core.support import (
                    support_kb, support_home_text, handle_sup_text, is_sup_pending,
                )
                # اجازه تیکت و دستورات پشتیبانی
                if is_sup_pending(int(user_id)):
                    if await handle_sup_text(bot, message, int(user_id), text):
                        return
                if text in ("/start", "start", "منو", "پشتیبانی", "تیکت", "/support", "support"):
                    ban = await get_active_ban(int(user_id))
                    await message.reply(support_home_text(ban), components=support_kb())
                    return
                # بقیه دستورات مسدود
                ban = await get_active_ban(int(user_id))
                await message.reply(
                    "🚫 حساب شما بن است.\n"
                    f"کد پیگیری: `{(ban or {}).get('tracking_code') or '—'}`\n"
                    "فقط بخش **🎫 پشتیبانی** در دسترس است.\n"
                    "بنویس: `پشتیبانی`",
                    components=support_kb(),
                )
                return
        except Exception as e:
            logger.debug(f"ban check: {e}")


        # ---- Start / Menu (Glass) ----
        if text in ("/start", "start", "منو", "شروع", "/menu"):
            try:
                from utils.keyboards import set_panel_owner, reset_panel_owner
                _tok = set_panel_owner(int(user_id))
                try:
                    kb = main_menu_kb()
                finally:
                    reset_panel_owner(_tok)
                await message.reply(WELCOME, components=kb)
            except Exception as e:
                logger.error(f"start menu kb error: {e}")
                # fallback without keyboard so user is not stuck
                await message.reply(
                    WELCOME + "\n\n⚠️ منوی دکمه‌ای موقتاً در دسترس نیست.\n"
                    f"خطا: `{type(e).__name__}`"
                )
            return


        # ---- پنل ادمین / مالک ----
        if text in ("/admin", "admin", "پنل ادمین", "/panel", "پنل", "/mod"):
            try:
                from admin.admin_panel import show_admin_panel
                await show_admin_panel(message)
                return
            except Exception as e:
                logger.error(f"/admin error: {e}")
                import traceback as _tb
                _tb.print_exc()
                await message.reply(f"⚠️ خطا در پنل ادمین:\n`{type(e).__name__}: {e}`")
                return

        
        
        # ---- Owner Panel ----
        if text in ("/owner", "owner", "پنل مالک", "👑"):
            try:
                if await is_owner(user_id):
                    from admin.panel import show_owner_panel
                    await show_owner_panel(message)
                else:
                    await message.reply("⛔ فقط Owner.")
            except Exception as e:
                logger.error(f"/owner error: {e}")
                await message.reply(f"⚠️ /owner: `{e}`")
            return


        # ---- لینک دستی گروه برای تنظیمات ----
        if private and (text.startswith("/addgroup") or text.startswith("addgroup")):
            parts = text.split()
            if len(parts) < 2:
                await message.reply(
                    "فرمت:\n`/addgroup CHAT_ID`\n"
                    "آیدی گروه را بفرست تا به لیست تنظیماتت اضافه شود.\n"
                    "ربات باید داخل آن گروه باشد."
                )
                return
            gid = parts[1].strip()
            try:
                from database.groups import register_group, register_group_user
                await register_group(gid, title="", username="")
                await register_group_user(int(user_id), gid)
                from core.group_settings import show_group_list
                txt, kb = await show_group_list(int(user_id))
                await message.reply(
                    f"✅ گروه `{gid}` به لیستت اضافه شد.\n\n" + txt,
                    components=kb,
                )
            except Exception as e:
                await message.reply(f"❌ خطا: `{e}`")
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


        # ---- گزارش باگ (pending) ----
        try:
            from core.reports import is_pending, submit_report
            if is_pending(int(user_id)):
                if text in ("لغو", "cancel", "/cancel"):
                    from core.reports import cancel_report
                    from core.menu import handle_menu_callback
                    prev = await cancel_report(int(user_id))
                    txt, kb = await handle_menu_callback(int(user_id), prev or "menu:main", first_name, private=True)
                    await message.reply(txt, components=kb)
                    return
                txt, kb = await submit_report(bot, int(user_id), text, username, first_name)
                await message.reply(txt, components=kb)
                return
        except Exception as e:
            logger.error(f"report pending: {e}")

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
            # صدا زدن Pet در گروه و پیوی → پنل شیشه‌ای (قفل برای همین کاربر)
            from utils.keyboards import set_panel_owner, reset_panel_owner
            _tok = set_panel_owner(int(user_id))
            try:
                call = await try_call_pet(int(user_id), text)
            finally:
                try:
                    reset_panel_owner(_tok)
                except Exception:
                    pass
            if call:
                if isinstance(call, tuple):
                    call_text, call_kb = call[0], call[1] if len(call) > 1 else None
                    if call_kb is not None:
                        await message.reply(call_text, components=call_kb)
                    else:
                        await message.reply(call_text)
                else:
                    await message.reply(str(call))
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

        # ---- Owner/Admin pending text ----
        if await is_owner(user_id) or await is_admin(user_id):
            if await is_owner(user_id):
                from admin.owner_tasks import handle_ot_text, has_ot_pending
                if has_ot_pending(int(user_id)):
                    if await handle_ot_text(bot, message, int(user_id), text):
                        return
                from admin.perms_mgmt import handle_ap_text, has_ap_pending
                if has_ap_pending(int(user_id)):
                    if await handle_ap_text(message, int(user_id), text):
                        return
            from admin.users_mgmt import handle_um_text, has_um_pending
            if has_um_pending(int(user_id)):
                if await handle_um_text(bot, message, int(user_id), text):
                    return
            from admin.tickets_panel import handle_tk_text, has_tk_pending
            if has_tk_pending(int(user_id)):
                if await handle_tk_text(bot, message, int(user_id), text):
                    return
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

        
        # ---- جنگ میویی با ریپلای در گروه ----
        if not private and chat_id is not None:
            try:
                from battle.system import is_battle_challenge_text, create_challenge
                if is_battle_challenge_text(text):
                    reply = getattr(message, "reply_to_message", None) or getattr(message, "replied_message", None)
                    target_user = None
                    target_name = ""
                    if reply is not None:
                        ta = getattr(reply, "author", None) or getattr(reply, "from_user", None)
                        if ta is not None:
                            target_user = int(getattr(ta, "id", 0) or 0)
                            target_name = getattr(ta, "first_name", None) or "حریف"
                    if not target_user:
                        await message.reply(
                            "⚔️ برای جنگ میویی، روی **پیام حریف ریپلای** کن و بنویس:\n"
                            "`جنگ میویی`"
                        )
                        return
                    if target_user == int(user_id):
                        await message.reply("❌ با خودت نمی‌تونی بجنگی!")
                        return
                    msg_text, kb = await create_challenge(
                        int(user_id), first_name, target_user, target_name
                    )
                    if kb is None:
                        await message.reply(msg_text)
                    else:
                        await message.reply(msg_text, components=kb)
                    return
            except Exception as e:
                logger.error(f"battle challenge: {e}")

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


async def _dispatch(user_id, data: str, first_name="", username="", chat_id=None, private=True):
    # Menu
    if data.startswith("menu:") or data.startswith("act:") or data.startswith("rank:"):
        return await handle_menu_callback(user_id, data, first_name, chat_id=chat_id, private=private)

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
        lines = [
            "🛒 **فروشگاه Pet**",
            "━━━━━━━━━━━━━━",
            "برای غذا / بازی / خواب باید از اینجا بخری.",
            "هر آیتم معمولاً **۲۰ بار** قابل استفاده است.",
            "",
        ]
        for it in items:
            import json as _json
            eff = it.get("effect") or {}
            if isinstance(eff, str):
                try:
                    eff = _json.loads(eff)
                except Exception:
                    eff = {}
            uses = eff.get("max_uses") or 20
            lines.append(
                f"• {it.get('name')} — `{it.get('price')}`🪙 "
                f"| {uses}× | {it.get('item_type')}"
            )
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
        import json as _json
        effect = item.get("effect") or {}
        if isinstance(effect, str):
            try:
                effect = _json.loads(effect)
            except Exception:
                effect = {}
        effect = dict(effect)
        max_uses = int(effect.get("max_uses") or 20)
        effect["max_uses"] = max_uses
        effect["uses_left"] = max_uses
        await add_item(
            user_id,
            item_id,
            item.get("item_type") or "item",
            1,
            effect,
        )
        return (
            f"✅ **{item.get('name')}** خریدی!\n"
            f"🪙 -{price}\n"
            f"🔋 تعداد استفاده: `{max_uses}`\n"
            f"📦 برو Pet و استفاده کن!",
            shop_kb(items),
        )

    if data == "shop:inv":
        from database.inventory import get_inventory
        import json as _json
        inv = await get_inventory(user_id)
        if not inv:
            return "🎒 اینونتوری خالی است.\nاز فروشگاه برای Pet بخر!", back_main_kb()
        lines = ["🎒 **اینونتوری Pet**", "━━━━━━━━━━━━━━"]
        for it in inv:
            meta = it.get("meta") or {}
            if isinstance(meta, str):
                try:
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            uses = meta.get("uses_left")
            max_u = meta.get("max_uses")
            if uses is not None:
                lines.append(
                    f"• `{it.get('item_id')}` ({it.get('item_type')}) "
                    f"— 🔋 {uses}/{max_u or uses}"
                )
            else:
                lines.append(f"• `{it.get('item_id')}` ×{it.get('quantity')}")
        return "\n".join(lines), back_main_kb()

    return WELCOME, main_menu_kb()


@bot.event
async def on_callback(callback: CallbackQuery):
    """هندلر دکمه‌های شیشه‌ای — همیشه پاسخ می‌دهد."""
    data = ""
    user_id = 0
    _owner_token = None
    try:
        data = (getattr(callback, "data", None) or "").strip()
        # کاربر
        user = (
            getattr(callback, "from_user", None)
            or getattr(callback, "user", None)
            or getattr(callback, "author", None)
        )
        if user is None:
            logger.warning("callback without user")
            try:
                await callback.answer("⚠️ کاربر نامشخص", show_alert=True)
            except Exception:
                pass
            return

        user_id = int(getattr(user, "id", 0) or 0)
        first_name = getattr(user, "first_name", None) or ""
        username = getattr(user, "username", None) or ""
        msg = getattr(callback, "message", None)

        logger.info(f"callback user={user_id} data={data!r}")

        # بن: فقط پشتیبانی
        try:
            from database.bans import is_banned
            if await is_banned(int(user_id)) and not data.startswith("sup:"):
                try:
                    await callback.answer("🚫 بن هستید — فقط پشتیبانی", show_alert=True)
                except Exception:
                    pass
                from core.support import support_home_text, support_kb
                from database.bans import get_active_ban
                ban = await get_active_ban(int(user_id))
                await _edit_or_reply(msg, support_home_text(ban), support_kb())
                return
        except Exception:
            pass

        # قفل پنل: فقط صاحب پنل
        from utils.panel_lock import parse_data, deny_message
        from utils.keyboards import set_panel_owner, reset_panel_owner
        clean_data, panel_owner = parse_data(data)
        data = clean_data

        # تشخیص گروه از message
        is_group_panel = False
        try:
            chat = getattr(msg, "chat", None) if msg else None
            title = getattr(chat, "title", None) if chat else None
            is_group_panel = bool(title)
        except Exception:
            pass

        if panel_owner is not None and int(panel_owner) != int(user_id):
            try:
                deny = await deny_message(panel_owner)
                await callback.answer(deny.replace("**", ""), show_alert=True)
            except Exception:
                try:
                    await callback.answer("⛔ این پنل مال تو نیست!", show_alert=True)
                except Exception:
                    pass
            # پیام هم در گروه نشان بده
            try:
                if msg is not None and is_group_panel:
                    deny = await deny_message(panel_owner)
                    await msg.reply(deny)
            except Exception:
                pass
            return

        # از این به بعد کیبوردهای ساخته‌شده با owner همین کاربر تگ می‌شوند
        _owner_token = set_panel_owner(user_id)

        # اول answer تا لودینگ دکمه قطع شود
        try:
            await callback.answer()
        except Exception as e:
            logger.debug(f"callback.answer: {e}")

        if not data:
            if msg is not None:
                await _edit_or_reply(msg, "⚠️ دکمه بدون داده.", main_menu_kb())
            return

        # ثبت کاربر
        try:
            await create_user(user_id, first_name=first_name, username=username)
        except Exception:
            pass




        if data.startswith("adm:"):
            if not (await is_owner(user_id) or await is_admin(user_id)):
                try:
                    await callback.answer("⛔ ادمین", show_alert=True)
                except Exception:
                    pass
                return
            from admin.admin_panel import handle_admin_callback
            text, kb = await handle_admin_callback(bot, callback, data, user_id)
            await _edit_or_reply(msg, text, kb)
            return

        if data.startswith("ot:"):
            if not await is_owner(user_id):
                try:
                    await callback.answer("⛔ فقط Owner", show_alert=True)
                except Exception:
                    pass
                return
            from admin.owner_tasks import handle_ot_callback
            text, kb = await handle_ot_callback(bot, data, user_id)
            await _edit_or_reply(msg, text, kb)
            return

        if data.startswith("ap:"):
            if not (await is_owner(user_id) or await is_admin(user_id)):
                try:
                    await callback.answer("⛔ ادمین", show_alert=True)
                except Exception:
                    pass
                return
            # فقط owner یا admins.manage
            from admin.perms_mgmt import handle_ap_callback, require_perm
            if not await is_owner(user_id) and not await require_perm(user_id, "admins.manage"):
                try:
                    await callback.answer("⛔ مجوز مدیریت ادمین ندارید", show_alert=True)
                except Exception:
                    pass
                return
            text, kb = await handle_ap_callback(data, user_id, bot=bot)
            await _edit_or_reply(msg, text, kb)
            return

        if data.startswith("um:"):
            if not (await is_owner(user_id) or await is_admin(user_id)):
                try:
                    await callback.answer("⛔ ادمین", show_alert=True)
                except Exception:
                    pass
                return
            from admin.perms_mgmt import require_perm
            parts_um = data.split(":")
            um_cmd = parts_um[1] if len(parts_um) > 1 else ""
            need = "users.view"
            if um_cmd in ("ban", "ban_d", "unban"):
                need = "users.ban"
            elif um_cmd in ("coin_add", "coin_sub", "pt_add", "pt_sub", "gym", "msg"):
                need = "users.edit"
            if not await require_perm(user_id, need):
                try:
                    await callback.answer(f"⛔ مجوز {need} ندارید", show_alert=True)
                except Exception:
                    pass
                return
            from admin.users_mgmt import handle_um_callback
            text, kb = await handle_um_callback(bot, callback, data, user_id)
            await _edit_or_reply(msg, text, kb)
            return

        if data.startswith("tk:"):
            if not (await is_owner(user_id) or await is_admin(user_id)):
                try:
                    await callback.answer("⛔ ادمین", show_alert=True)
                except Exception:
                    pass
                return
            from admin.perms_mgmt import require_perm
            if not await require_perm(user_id, "tickets.manage"):
                try:
                    await callback.answer("⛔ مجوز تیکت ندارید", show_alert=True)
                except Exception:
                    pass
                return
            from admin.tickets_panel import handle_tk_callback
            text, kb = await handle_tk_callback(bot, data, user_id)
            await _edit_or_reply(msg, text, kb)
            return

        if data.startswith("sup:"):
            from core.support import handle_sup_callback
            text, kb = await handle_sup_callback(bot, user_id, data)
            await _edit_or_reply(msg, text, kb)
            return

        # Bug reports (user + admin)
        if data.startswith("report:"):
            from core.reports import (
                cancel_report, admin_list_text, admin_view_report, admin_resolve,
            )
            from core.menu import handle_menu_callback
            parts = data.split(":")
            cmd = parts[1] if len(parts) > 1 else ""
            if cmd == "cancel":
                prev = await cancel_report(user_id)
                text, kb = await handle_menu_callback(user_id, prev or "menu:main", first_name, private=True)
                await _edit_or_reply(msg, text, kb)
                return
            # admin actions
            if cmd in ("admin_list", "view", "resolve"):
                # owner or admin
                from database.admins import get_admin
                adm = await get_admin(user_id)
                is_adm = await is_owner(user_id) or (adm and adm.get("enabled", True))
                if not is_adm:
                    try:
                        await callback.answer("⛔ فقط ادمین", show_alert=True)
                    except Exception:
                        pass
                    return
            if cmd == "admin_list":
                st = parts[2] if len(parts) > 2 else "open"
                text, kb = await admin_list_text(st)
                await _edit_or_reply(msg, text, kb)
                return
            if cmd == "view" and len(parts) > 2:
                text, kb = await admin_view_report(int(parts[2]))
                await _edit_or_reply(msg, text, kb)
                return
            if cmd == "resolve" and len(parts) > 2:
                text, kb = await admin_resolve(int(parts[2]), user_id, bot)
                await _edit_or_reply(msg, text, kb)
                return
            if cmd == "noop":
                return
            return

        # Group settings
        if data.startswith("gset:"):
            from core.group_settings import handle_gset_callback
            text, kb = await handle_gset_callback(bot, user_id, data)
            ok = await _edit_or_reply(msg, text, kb)
            if not ok:
                await bot.send_message(user_id, text, components=kb)
            return

        # Owner / Admin panel
        if data.startswith("owner:"):
            if not (await is_owner(user_id) or await is_admin(user_id)):
                try:
                    await callback.answer("⛔ فقط ادمین/مالک", show_alert=True)
                except Exception:
                    pass
                return
            # محدودیت دسترسی برای ادمین (نه Owner)
            if not await is_owner(user_id):
                from admin.perms_mgmt import require_perm
                act = data.split(":", 1)[-1].split(":")[0] if ":" in data else ""
                # owner:eco_all_coin -> eco_all_coin
                perm_map = {
                    "um_list": "users.view",
                    "users": "users.view",
                    "user_find": "users.view",
                    "tickets": "tickets.manage",
                    "bc_groups": "broadcast.send",
                    "bc_users": "broadcast.send",
                    "bc_admins": "broadcast.send",
                    "broadcast": "broadcast.send",
                    "economy": "economy.view",
                    "eco_all_coin": "economy.edit",
                    "eco_all_point": "economy.edit",
                    "eco_one_coin": "economy.edit",
                    "eco_one_point": "economy.edit",
                    "eco_one_gym": "economy.edit",
                    "admins": "admins.view",
                    "admin_add": "admins.manage",
                    "admin_remove": "admins.manage",
                    "admin_toggle": "admins.manage",
                    "logs": "logs.view",
                    "backup": "database.backup",
                    "backup_create": "database.backup",
                    "groups": "groups.view",
                    "group_set": "groups.edit",
                    "seasons": "seasons.manage",
                    "season_start": "seasons.manage",
                    "season_end": "seasons.manage",
                    "events": "events.manage",
                    "guides": "guides.view",
                    "guide_on_all": "guides.edit",
                    "guide_off_all": "guides.edit",
                    "maint": "maintenance.manage",
                    "settings": "settings.manage",
                }
                need = perm_map.get(act)
                if need and not await require_perm(user_id, need):
                    try:
                        await callback.answer(f"⛔ مجوز {need} ندارید", show_alert=True)
                    except Exception:
                        pass
                    return
            from admin.panel import handle_owner_callback
            await handle_owner_callback(bot, callback, data)
            return

        # بقیه منوها
        chat_id = None
        private = True
        try:
            chat = getattr(msg, "chat", None) if msg else None
            if chat is not None:
                chat_id = getattr(chat, "id", None)
                title = getattr(chat, "title", None) or ""
                private = not bool(title)
        except Exception:
            pass
        result = await _dispatch(user_id, data, first_name, username, chat_id=chat_id, private=private)
        if isinstance(result, tuple) and len(result) >= 2:
            text, kb = result[0], result[1]
        elif isinstance(result, tuple) and len(result) == 1:
            text, kb = result[0], main_menu_kb()
        elif isinstance(result, str):
            text, kb = result, main_menu_kb()
        else:
            text, kb = WELCOME, main_menu_kb()

        ok = await _edit_or_reply(msg, text, kb)
        if not ok:
            # آخرین تلاش: پیام جدید به کاربر
            try:
                await bot.send_message(user_id, text, components=kb)
            except Exception as e:
                logger.error(f"final send failed: {e}")

        try:
            reset_panel_owner(_owner_token)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"callback error: {e}")
        traceback.print_exc()
        try:
            await callback.answer(f"خطا: {type(e).__name__}", show_alert=True)
        except Exception:
            pass
        try:
            if user_id:
                await bot.send_message(user_id, f"⚠️ خطا در دکمه `{data}`:\n`{e}`")
        except Exception:
            pass




# پشتیبانی از هر دو سبک event و handler (نسخه‌های مختلف bale)
try:
    from bale.handlers import CallbackQueryHandler
    @bot.handle(CallbackQueryHandler())
    async def _callback_handler_fallback(callback: CallbackQuery):
        # اگر event on_callback قبلاً جواب داده، دوباره اجرا می‌شود — ایرادی ندارد
        await on_callback(callback)
except Exception as _e:
    logger.debug(f"CallbackQueryHandler not registered: {_e}")


if __name__ == "__main__":
    print(f"Starting {BOT_NAME} v{BOT_VERSION}...")
    bot.run()
