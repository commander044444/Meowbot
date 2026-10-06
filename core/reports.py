# ==========================================
# گزارش باگ / مشکل (کاربر + ادمین)
# ==========================================

from bale import InlineKeyboardMarkup, InlineKeyboardButton
from database.reports import create_report, list_reports, get_report, resolve_report, count_open_reports
from database.admins import list_admins
from config import OWNER_ID
from utils.keyboards import glass, main_menu_kb, back_main_kb

# user_id -> previous menu callback or "menu:main"
_report_pending: dict = {}
_prev_menu: dict = {}


def _kb(rows):
    kb = InlineKeyboardMarkup()
    row_num = 1
    for row in rows:
        if not row:
            continue
        for text, data in row:
            kb.add(InlineKeyboardButton(text=str(text), callback_data=str(data)), row=row_num)
        row_num += 1
    return kb


def report_start_kb(prev: str = "menu:main"):
    return _kb([
        [("❌ لغو و بازگشت", f"report:cancel:{prev}")],
    ])


def reports_list_kb(reports):
    rows = []
    for r in reports[:15]:
        rid = r["id"]
        st = "🟢" if r.get("status") == "open" else "✅"
        preview = (r.get("body") or "")[:30].replace("\n", " ")
        rows.append([(f"{st} #{rid} {preview}", f"report:view:{rid}")])
    rows.append([("🔄 بازها", "report:admin_list:open"), ("📋 همه", "report:admin_list:all")])
    rows.append([("🔙 منوی Owner", "owner:home")])
    return _kb(rows)


def report_detail_kb(report_id: int, user_id: int, status: str):
    rows = []
    if status == "open":
        rows.append([("✅ حل شد / بستن", f"report:resolve:{report_id}")])
    rows.append([(f"💬 رفتن به پیوی کاربر", f"report:noop")])  # informational
    rows.append([("🔙 لیست گزارش‌ها", "report:admin_list:open")])
    return _kb(rows)


async def start_report_flow(user_id: int, prev: str = "menu:main"):
    _report_pending[user_id] = True
    _prev_menu[user_id] = prev or "menu:main"
    text = (
        "🐛 **گزارش باگ / مشکل**\n"
        "━━━━━━━━━━━━━━\n"
        "مشکل یا باگ را در یک پیام بنویس.\n"
        "گزارش برای **همه ادمین‌ها** ارسال می‌شود.\n\n"
        "برای انصراف دکمه **لغو** را بزن."
    )
    return text, report_start_kb(prev)


async def cancel_report(user_id: int):
    prev = _prev_menu.pop(user_id, "menu:main")
    _report_pending.pop(user_id, None)
    return prev


def is_pending(user_id: int) -> bool:
    return bool(_report_pending.get(user_id))


async def submit_report(bot, user_id: int, text: str, username: str = "", first_name: str = ""):
    _report_pending.pop(user_id, None)
    prev = _prev_menu.pop(user_id, "menu:main")
    rid = await create_report(user_id, text, username, first_name)

    # notify all admins + owner
    notify = (
        f"🐛 **گزارش جدید #{rid}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 {first_name or '—'} (`{user_id}`)\n"
        f"@{username or '—'}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{text[:1500]}"
    )
    kb = _kb([
        [("✅ حل شد", f"report:resolve:{rid}")],
        [("📋 لیست گزارش‌ها", "report:admin_list:open")],
    ])
    targets = {int(OWNER_ID)}
    try:
        for a in await list_admins() or []:
            if a.get("enabled", True):
                targets.add(int(a["user_id"]))
    except Exception:
        pass

    for aid in targets:
        try:
            await bot.send_message(aid, notify, components=kb)
        except Exception:
            pass

    return (
        f"✅ گزارش **#{rid}** ثبت شد.\n"
        f"ادمین‌ها بررسی می‌کنند. ممنون 🙏",
        main_menu_kb(),
    )


async def admin_list_text(status: str = "open"):
    reports = await list_reports(status=status if status != "all" else "all", limit=20)
    n = await count_open_reports()
    lines = [
        f"🐛 **گزارش‌ها** (باز: `{n}`)",
        "━━━━━━━━━━━━━━",
    ]
    if not reports:
        lines.append("خالی است.")
    else:
        for r in reports:
            st = "🟢 باز" if r.get("status") == "open" else "✅ حل‌شده"
            lines.append(
                f"{st} **#{r['id']}** — `{r.get('user_id')}` "
                f"{(r.get('first_name') or '')[:12]}\n"
                f"   {(r.get('body') or '')[:60]}"
            )
    return "\n".join(lines), reports_list_kb(reports)


async def admin_view_report(report_id: int):
    r = await get_report(report_id)
    if not r:
        return "❌ گزارش پیدا نشد.", _kb([[("🔙", "report:admin_list:open")]])
    text = (
        f"🐛 **گزارش #{r['id']}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"وضعیت: `{r.get('status')}`\n"
        f"👤 {r.get('first_name')} (`{r.get('user_id')}`)\n"
        f"@{r.get('username') or '—'}\n"
        f"🕒 {r.get('created_at')}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{r.get('body')}\n"
        f"━━━━━━━━━━━━━━\n"
        f"برای پیام به کاربر، در پیوی ربات برایش پیام بفرست "
        f"(آیدی: `{r.get('user_id')}`)."
    )
    return text, report_detail_kb(r["id"], r["user_id"], r.get("status") or "open")


async def admin_resolve(report_id: int, resolver_id: int, bot=None):
    r = await get_report(report_id)
    if not r:
        return "❌ پیدا نشد.", _kb([[("🔙", "report:admin_list:open")]])
    await resolve_report(report_id, resolver_id)
    try:
        from database.admin_system import record_admin_activity
        await record_admin_activity(
            resolver_id, "report_resolve", target=str(report_id),
            unique_key=f"report_resolve:{report_id}",
        )
    except Exception as e:
        print(f"activity report: {e}")
    # notify user
    if bot:
        try:
            await bot.send_message(
                int(r["user_id"]),
                f"✅ گزارش باگ **#{report_id}** بررسی و **بسته** شد.\nممنون از گزارشت 🐱",
            )
        except Exception:
            pass
    return (
        f"✅ گزارش **#{report_id}** حل شد و بسته شد.",
        _kb([[("📋 لیست گزارش‌ها", "report:admin_list:open")], [("🔙 Owner", "owner:home")]]),
    )
