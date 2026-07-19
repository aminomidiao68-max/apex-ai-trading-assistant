# Signal Shadow Alpha 18 — Scheduled Wake Collector

- GitHub Actions هر ۳۰ دقیقه Staging را بیدار می‌کند
- Endpoint داخلی از OpenAPI مخفی است
- Token تصادفی در GitHub/Render Secrets
- hmac.compare_digest برای مقایسه constant-time
- Production بدون Token و با 404
- asyncio Lock مانع اجرای هم‌زمان Worker/Cron
- Cycle خروجی فقط counts پاک‌سازی‌شده
- Capture/Resolve idempotent و بدون routing
- Render Free می‌تواند Sleep کند؛ Cron آن را دوره‌ای Wake می‌کند
