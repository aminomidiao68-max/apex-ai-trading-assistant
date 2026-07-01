<p align="center">
  <img src="docs/assets/apex_ai_logo.png" alt="APEX AI Logo" width="120" />
</p>

# APEX AI / ایپکس AI

## English
APEX AI is a mobile-first crypto & forex trading assistant with:
- Android app (Kotlin + Compose)
- FastAPI backend
- Signal analysis workflows
- Risk management
- Trade journal
- Backtesting, sweep, and walk-forward analysis
- Execution preview and broker foundations

### Quick Start
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Android project:
```text
project/android
```

Demo login:
- Email: `demo@apexai.app`
- Password: `Demo12345!`

### Notes
- No guaranteed profit
- Use demo/testnet first
- Add `google-services.json` for full Firebase push

---

## فارسی
APEX AI یک دستیار معاملاتی موبایل‌محور برای کریپتو و فارکس است که شامل این بخش‌هاست:
- اپ اندروید با Kotlin و Compose
- بک‌اند FastAPI
- جریان تحلیل و بررسی سیگنال
- مدیریت ریسک
- ژورنال معاملات
- بک‌تست، sweep و walk-forward
- پیش‌نمایش اجرای سفارش و foundation بروکرها

### اجرای سریع
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

پروژه اندروید را از این مسیر باز کن:
```text
project/android
```

ورود دمو:
- Email: `demo@apexai.app`
- Password: `Demo12345!`

### نکات مهم
- سود تضمینی وجود ندارد
- ابتدا از demo / testnet استفاده کن
- برای Push واقعی باید `google-services.json` را اضافه کنی

---

## Useful Docs / اسناد مهم
- `docs/run_on_your_system_fa.md`
- `docs/release_checklist_fa.md`
- `docs/deployment_guide_fa.md`
- `docs/firebase_setup_fa.md`
- `docs/connector_setup_fa.md`
