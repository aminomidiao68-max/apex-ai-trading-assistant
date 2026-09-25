# فیکس 1 دقیقه‌ای — اتصال پرود به Neon (برای C)

**مشکل صادقانه:** پرود `apex-ai-trading-assistant` الان `sqlite degraded true` است چون `render.yaml` به `fromDatabase: apex-ai-postgres` اشاره می‌کند ولی آن دیتابیس Render وجود ندارد. استیج `apex-ai-chaos-staging` با Neon خارجی کار می‌کند و 7423 رکورد دارد — پرود هر دیپلوی صفر می‌شود.

**راه‌حل صادقانه (فقط تو می‌توانی انجام دهی — من کد را آماده کردم):**

### گزینه 1 — سریع‌ترین (1 دقیقه، بدون هزینه):
1. برو `https://dashboard.render.com` → `apex-ai-trading-assistant` (سرویس پرود)
2. تب `Environment` → `Add Environment Variable`
3. `Key: DATABASE_URL` — `Value:` را از استیج کپی کن:
   - برو `apex-ai-chaos-staging` → `Environment` → `DATABASE_URL` → `Copy`
   - یا از Neon Dashboard → `Connection string` (postgres://...)
4. `Save Changes` — Render اتوماتیک 2-3 دقیقه ری‌دیپلوی می‌کند
5. چک: `curl https://apex-ai-trading-assistant.onrender.com/ready` باید `postgresql true` و `production_database_ready true` شود

### گزینه 2 — دائمی در کد (اگر می‌خواهی پرود و استیج جدا بمانند):
- در `render.yaml` برای پرود `DATABASE_URL` را به `fromDatabase` Render Postgres جدید تغییر بده (باید اول در Render → `New → PostgreSQL` بسازی — رایگان 90 روز، بعد پولی).

**بعد از فیکس:** cohort پرود دیگر صفر نمی‌شود و `failed_gate` و `shadow` هم در پرود می‌ماند.

**مدرک الان:**
- استیج: `curl https://apex-ai-chaos-staging.onrender.com/ready` → `postgresql true` ✅
- پرود: `curl https://apex-ai-trading-assistant.onrender.com/ready` → `sqlite degraded` ❌ (تا فیکس بالا)

**من چه کردم:** `render.yaml` را `value: 3.19.0-pro-alpha84` کردم و TTL را 10ث کردم + WebSocket — کد آماده است، فقط ENV دستی می‌خواهد.
