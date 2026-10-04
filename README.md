# 🐱 MeowBot v2.0 (Glass UI)

ربات اجتماعی / بازی برای **Bale** — آماده **Railway + PostgreSQL**

## UI شیشه‌ای 🪟

تقریباً همه کارها با **دکمه اینلاین** انجام می‌شود:

- منوی اصلی چندردیفه
- Pet / Battle / Bank / Shop / Games / Ranking
- Owner Panel کامل با دکمه
- پروفایل، مأموریت، دستاورد، جایزه روزانه

`/start` بزن و از دکمه‌ها استفاده کن.

## راه‌اندازی Railway

1. PostgreSQL اضافه کن
2. متغیرها:
   - `DATABASE_URL` → از پلاگین PostgreSQL (خودت می‌ذاری)
   - اختیاری: `BOT_TOKEN` / `OWNER_ID`
3. Start: `python main.py`

در `config.py` مقدار پیش‌فرض `DATABASE_URL` هست؛ روی Railway با env جایگزین می‌شود.

## دستورات متنی (اختیاری)

| متن | کار |
|-----|-----|
| میو | امتیاز |
| /start | منوی شیشه‌ای |
| /owner | پنل مالک |
| پروفایل / رنکینگ / پت / بتل / بانک | میانبر منو |

## Season

فقط `meow_points` ریست می‌شود. سکه، Pet، Achievement و Level دائمی حفظ می‌شوند.

## ساختار اصلی

```
main.py
config.py
database/     # PostgreSQL async
core/         # meow + menu
pet/system.py
battle/system.py
economy/bank_ui.py
games/system.py
admin/panel.py
guides/ + seasons/ schedulers
utils/keyboards.py   # Glass UI
```

نسخه: **2.0.0**
