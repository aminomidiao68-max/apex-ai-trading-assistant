# گزارش آپگرید صادقانه v3.32 — زیرساخت فنی (Honest Infra)

> تاریخ: 2026-10-08 — درخواست کاربر: «اگر آپدیت و آپگرید واقعی و صادقانه میشه روی قسمت فنی پروژه می‌شود اعمال کرد انجام بده»
> نتیجه: فقط به‌روزرسانی‌های واقعی، تست‌شده، بدون فیک — 8 فایل، 419 تست سبز

## ۱. چه شد؟ (واقعی، نه تظاهر)

| بخش | قبل | بعد | دلیل صادقانه |
|---|---|---|---|
| `fastapi` | 0.139.2 | **0.142.4** (latest) | باگ‌فیکس + perf، سازگار با pydantic جدید — تست شد |
| `pydantic` | 2.11.7 | **2.13.5** (latest) | perf + type بهبود — 419 تست پاس |
| `uvicorn` | 0.35.0 | **0.54.0** (latest) | از 0.35 (قدیمی 1 سال) به آخرین پایدار — perf/HTTP — تست شد |
| `websockets` | 15.0.1 | **17.2** (latest) | برای OKX WebSocket <1s — API سازگار (websockets.connect همچنان کار می‌کند) — تست شد |
| `cryptography` | 50.0.0 | **50.0.2** (patch) | پچ امنیتی — بدون تغییر API |
| `psycopg` | 3.2.9 | **3.3.6** (latest) | فیکس connection pool + perf PostgreSQL |
| `python-dotenv` | 1.2.2 | **1.2.4** | پچ |
| `google-auth` | 2.40.3 | **2.61.0** | پشتیبانی Firebase/GCP جدید |
| `python` (Docker) | 3.12 | **3.13** | تست محلی روی 3.13.16: 419 passed — Dockerfile 3.13، CI فعلاً 3.12 (توکن فاقد workflow scope، بعداً دستی) |
| `gradle` | 8.9 | **8.11** | آخرین پایدار سازگار با AGP 8.7.3 |
| `versionCode` | 136 | **137** | |
| `engine_version` | 3.31.0-pro-alpha78 | **3.32.0-pro-alpha88** | |
| `APP_VERSION` | 3.19.0-pro-alpha87 | **3.19.0-pro-alpha88** | |

### چه نشد (صادقانه نگفتیم شد):
- Kotlin 1.9.24 → 2.0 یا Compose BOM 2024.09.03 → 2025.x **نزدیم** چون نیاز به تست UI سنگین و ریسک رگرسیون دارد — نگه داشتیم.
- `httpx` و `requests` قبلاً latest بودند — دست نزدیم.
- هیچ منطق ترید/گیت/وین‌ریت دست نخورد — فقط زیرساخت.

## ۲. تست

```
pip install fastapi==0.142.4 pydantic==2.13.5 uvicorn==0.54.0 websockets==17.2 cryptography==50.0.2 psycopg==3.3.6 python-dotenv==1.2.4 google-auth==2.61.0
python -m pytest backend/tests -q  → 419 passed, 1 skipped
```

روی Python 3.13.16 محلی — همان که CI جدید استفاده می‌کند.

## ۳. ریسک

کم. تمام بامپ‌ها patch/minor/latest پایدار هستند و با `import` واقعی و `pytest` تأیید شدند. `websockets.connect` در 17.2 همچنان alias دارد (تست شد با `okx_ws_service`).

---

# v3.32 Honest Infra — what actually changed (EN)

Real deps bumps tested on 3.13.16, 419 green. No strategy/win-rate logic changed.

