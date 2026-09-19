# APEX AI — Base44 Dev Environment

## What this is
A FastAPI backend (`backend/app/main.py`) for a crypto/forex trading assistant. The
Android app (`android/`) is a Kotlin/Compose mobile client and is NOT run in the
preview — only the backend API is served here.

## Running it
```
docker compose -f docker-compose.base44.yml up -d
```
- Web entry point: host port **3000** → container 8000 (uvicorn `--reload`).
- Health check: `GET /ready` → `{"status":"ready",...}`.
- API docs (Swagger UI): `GET /docs`.
- OpenAPI schema: `GET /openapi.json`.

## Database
No external database is required. When `DATABASE_URL` is empty the backend falls
back to a local SQLite file at `backend/app_data/smartmoney.db` (auto-created,
schema auto-migrated on startup). A PostgreSQL URL can be supplied via
`DATABASE_URL` for production; the adapter handles both.

## Credentials / secrets
The app boots with **no external credentials** — all API keys are optional:
- `AI_PROVIDER=deterministic` is the default; the deterministic explainer works
  without any AI key. Set `AI_OPENAI_API_KEY` (or Gemini/Cerebras/Groq/OpenRouter)
  only to enable the external AI explanation layer.
- `TWELVEDATA_API_KEY` / `FINNHUB_API_KEY` enable live market/news data; without
  them the backend serves synthetic/paper data.
- Broker keys (Binance/Bybit/OANDA/MT5/cTrader) are for execution features only.
- `USER_SECRET_MASTER_KEY` (32-byte base64) is only needed to use the provider
  vault (encrypted broker secret storage).
- `ENABLE_LIVE_EXECUTION` / `ENABLE_TESTNET_EXECUTION` stay `false` by default.

Real secrets are delivered via `/run/base44/app.env` (platform-managed, outside
the repo) and override the repo defaults in `.env.base44-defaults`.

## Demo login
- Email: `demo@apexai.app`
- Password: `Demo12345!`
(seeded automatically in development via `SEED_DEMO_USER=true`)

## Live reload
Source is bind-mounted at `./backend` → `/app`; uvicorn `--reload` watches
`/app/app`, so edits to `backend/app/**` hot-reload without a rebuild. For
compose/env/dependency changes, run `reload_preview` after editing.

## Notes
- `pip install` runs on every container start (deps cached in the
  `apex_pip_cache` volume). First start is slower; subsequent restarts reuse the
  cache.
- The repo's own `docker-compose.yml` builds a production image (`COPY`-based)
  and is intentionally NOT used here.
