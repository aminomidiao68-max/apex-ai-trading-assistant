# APEX AI

APEX AI is a mobile-first **crypto & forex trading assistant** with:
- Android app (Kotlin + Jetpack Compose)
- FastAPI backend
- Signal workflows inspired by smart-money analysis concepts
- Risk management controls
- Trade journal and analytics
- Backtesting, parameter sweep, and walk-forward validation
- Execution preview and multi-connector foundations

> This repository is a **product-ready foundation**. It does not guarantee profit and must be tested in demo/testnet conditions before any live usage.

---

## Main Features

### Mobile App
- Branded splash screen
- Login / Register
- Live dashboard
- Signal center
- Candlestick chart with zoom / pan / crosshair
- Risk calculator
- Trade journal
- Backtest lab
- Analytics center
- Broker / execution preview lab
- Settings screen
- Firebase push foundation

### Backend
- FastAPI REST API
- WebSocket market stream
- Signal scoring engine
- Professional risk engine
- SQLite storage
- Backtest / sweep / walk-forward
- Analytics report endpoints
- Notification device registration
- Execution preview and routing foundations

---

## Connector Foundations
Included:
- Binance Futures
- Bybit
- OANDA
- MT5 foundation
- cTrader foundation

Some connectors are route-ready, while others remain foundation-level until final bridge/API integration is completed.

---

## Validation Tooling
APEX AI includes:
- Backtest run
- Parameter sweep
- Walk-forward analysis
- Journal statistics
- Signal analytics report

---

## Tech Stack

### Android
- Kotlin
- Jetpack Compose
- Navigation Compose
- Retrofit
- OkHttp / WebSocket
- Firebase Messaging foundation

### Backend
- FastAPI
- Pydantic
- httpx
- SQLite
- Google-auth-supported FCM-ready backend structure

---

## Quick Start

### Backend
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger:
```text
http://127.0.0.1:8000/docs
```

### Android
Open:
```text
project/android
```

Debug defaults:
- API: `http://10.0.2.2:8000/`
- WS: `ws://10.0.2.2:8000/ws/market`

---

## Demo Login
- Email: `demo@apexai.app`
- Password: `Demo12345!`

---

## Documentation
Important docs in `project/docs/`:
- release checklist
- deployment guide
- firebase setup
- connector setup
- privacy policy
- risk & terms
- user guide
- technical handover
- run-on-your-system guide

---

## Safety Notice
- No guaranteed profit
- No guaranteed signal accuracy
- Always use testnet/demo first
- Always verify risk limits before live execution
- Backtest results alone are not sufficient for live trading decisions

---

## Current Product Stage
A product-ready mobile trading assistant foundation, suitable for:
- MVP presentation
- private demo environments
- team handoff
- continued production development

---

## Disclaimer
This software is for analysis, workflow support, and controlled execution assistance. The user remains fully responsible for all trading decisions and risk exposure.
