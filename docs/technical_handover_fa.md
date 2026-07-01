# تحویل فنی پروژه APEX AI

## تکنولوژی‌ها
### موبایل
- Kotlin
- Jetpack Compose
- Navigation Compose
- Retrofit
- OkHttp / WebSocket
- Firebase Messaging foundation

### بک‌اند
- FastAPI
- Pydantic
- SQLite
- httpx
- notification foundation

## ماژول‌های کلیدی بک‌اند
- `signal_engine.py`
- `risk_engine.py`
- `backtest_service.py`
- `storage_service.py`
- `notification_service.py`
- connector services

## ماژول‌های کلیدی اندروید
- `ui/TradingAiApp.kt`
- `ui/dashboard/`
- `ui/signals/`
- `ui/chart/`
- `ui/journal/`
- `ui/backtest/`
- `ui/analytics/`
- `ui/broker/`
- `ui/settings/`

## مواردی که برای production باید کامل شوند
- Firebase production config
- keystore واقعی
- دامنه و HTTPS
- bridge واقعی MT5
- session واقعی cTrader
- secrets management

## ریسک‌های فنی فعلی
- برخی connectorها هنوز foundation-only هستند
- SQLite برای تولید سنگین مناسب نیست و در آینده بهتر است PostgreSQL یا DB production-grade جایگزین شود
- برخی تست‌ها smoke-level هستند و هنوز integration/e2e کامل نشده‌اند
