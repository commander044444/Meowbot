# 🐱 MeowBot v2.0

Social Game / Entertainment / Community Bot برای **Bale**  
آماده برای استقرار روی **Railway.com** با **PostgreSQL**

## ویژگی‌های اصلی

- 🐱 سیستم Meow با XP/Point، Cooldown، Anti-Spam و Anti-Repetition
- 🤖 Interaction ON/OFF مستقل برای هر گروه
- 💡 Auto Guide هوشمند (مستقل از Interaction)
- 🐾 Pet System کامل
- 💰 Economy + Bank + Shop + Inventory
- ⚔️ Battle
- 🎮 Mini Games
- 🎯 Missions + 🏆 Achievements
- 📅 Season System (فقط رنکینگ فصل ریست می‌شود؛ داده‌های دائمی حفظ می‌شوند)
- 🎉 Events
- 👑 Owner Panel حرفه‌ای + Permission System
- 💾 Backup / Health Check / Monitoring
- 🗄 PostgreSQL با Connection Pool

## ساختار

```
MeowBot/
├── main.py
├── config.py
├── requirements.txt
├── database/          # PostgreSQL layer
├── core/              # Meow, facts, truths, dares
├── admin/             # Owner Panel
├── guides/            # Auto Guide scheduler
├── seasons/           # Season scheduler
├── economy/ pet/ battle/ games/ ...
└── utils/
```

## نصب و اجرا (Railway)

### 1. PostgreSQL
در Railway یک PostgreSQL Plugin اضافه کنید.  
متغیر `DATABASE_URL` به‌صورت خودکار ست می‌شود.

### 2. Environment Variables
| Variable | توضیح |
|----------|--------|
| `BOT_TOKEN` | توکن ربات بله (یا از config) |
| `DATABASE_URL` | از Railway PostgreSQL |
| `OWNER_ID` | آیدی عددی مالک |

### 3. Deploy
- Root Directory: پوشه پروژه
- Start Command: `python main.py`
- Python version: 3.11+

### 4. Local
```bash
pip install -r requirements.txt
# DATABASE_URL را ست کنید
export DATABASE_URL=postgresql://user:pass@localhost:5432/meowbot
python main.py
```

## Season Reset — قانون مهم

وقتی فصل تمام می‌شود:
- ✅ فقط `meow_points` (رنکینگ فصل) ریست می‌شود
- ❌ سکه، Pet، Inventory، Achievement، Level دائمی، Profile پاک نمی‌شوند
- تاریخچه فصل‌های قبلی در `season_results` نگه داشته می‌شود

## Owner Panel

در PV ربات بفرستید:
```
/owner
```
یا `پنل مالک`

بخش‌ها: Dashboard، System Status، Tests، Users، Groups، Admins، Logs، Backup و ...

## Interaction vs Auto Guide

| سیستم | مستقل؟ | پیش‌فرض |
|--------|--------|---------|
| Interaction | بله | ON |
| Auto Guide | بله | ON هر ۱ ساعت |

خاموش کردن Interaction، Auto Guide را خاموش **نمی‌کند**.

## دستورات سریع

| دستور | کار |
|--------|-----|
| میو | امتیاز |
| پروفایل | وضعیت |
| رنکینگ | رتبه فصل |
| /owner | پنل مالک |
| /addcoin ID N | اضافه کردن کوین (Owner) |
| /addpoint ID N | اضافه کردن پوینت (Owner) |
| /addgym ID N | تغییر لول باشگاه (Owner) |

## امنیت

- Permission checks برای تمام عملیات حساس
- Owner قابل حذف نیست
- Audit log برای عملیات ادمین
- SQL injection protection با asyncpg parameters

## عیب‌یابی

1. **DB connection fail** → `DATABASE_URL` را چک کنید (باید `postgresql://` باشد)
2. **Bot offline** → `BOT_TOKEN` را در Environment یا config چک کنید
3. **Guide ارسال نمی‌شود** → `guide_enabled` و `guide_interval` گروه را ببینید

## نسخه

`2.0.0` — Upgrade از SQLite به PostgreSQL + معماری ماژولار

مقادیر واقعی config (Token، Owner ID، تنظیمات) حفظ شده‌اند.
