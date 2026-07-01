<p align="center">
  <img src="docs/assets/apex_ai_logo.png" alt="APEX AI Logo" width="140" />
</p>

<h1 align="center">APEX AI</h1>
<p align="center"><b>Crypto & Forex Trading Assistant</b></p>
<p align="center">AI-assisted market analysis, risk control, signal workflows, backtesting, and execution foundations.</p>

<p align="center">
  <img src="docs/assets/apex_ai_hero.png" alt="APEX AI Hero" width="760" />
</p>

---

## Overview

APEX AI is a **mobile-first trading assistant platform** built for crypto and forex workflows. It combines:
- ICT / Smart Money inspired analysis logic
- Risk management controls
- Signal review and journaling
- Backtesting, parameter sweep, and walk-forward analysis
- Live market monitoring with WebSocket support
- Broker / exchange execution preview foundations

This repository contains both:
- **Android app** built with Kotlin + Jetpack Compose
- **FastAPI backend** for analysis, storage, analytics, and execution routing foundations

> Important: this software does **not** guarantee profit or signal accuracy. Always validate strategies in demo/testnet environments before any live execution.

---

## Key Features

### Android App
- Branded splash screen and polished UX
- Login / Register
- Live dashboard
- Signal center
- Candlestick chart with zoom / pan / crosshair
- Risk calculator
- Trade journal
- Backtest lab
- Analytics center
- Broker / execution preview lab
- Settings and risk acknowledgement
- Firebase push foundation

### Backend
- FastAPI REST API
- WebSocket market stream
- Signal scoring engine
- Professional risk engine
- SQLite storage for signals and journal
- Backtest run
- Parameter sweep
- Walk-forward analysis
- Analytics reporting
- Notification device registration
- Execution preview and routing foundations

---

## Connector Foundations

Included in the current foundation:
- **Binance Futures**
- **Bybit**
- **OANDA**
- **MT5 foundation**
- **cTrader foundation**

Some connectors are route-ready, while others remain foundation-level until their final bridge/API integration is completed.

---

## Validation Tooling

The project already includes strategy validation tools:
- Historical backtest
- Parameter sweep
- Walk-forward analysis
- Journal statistics
- Analytics reports

This makes the platform much more useful for structured strategy evaluation before real execution.

---

## Tech Stack

### Mobile
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
- Google auth / FCM-ready backend foundation

---

## Project Structure

```text
project/
  android/
  backend/
  docs/
  FINAL_DELIVERY_FA.md
```

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
Open this folder in Android Studio:
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

## Firebase Push

The project already contains:
- Firebase Messaging foundation on Android
- Device token registration
- Backend FCM-ready structure

To enable real Firebase push you still need:
- `google-services.json`
- Firebase project setup
- Backend Firebase service account configuration

See:
- `docs/firebase_setup_fa.md`
- `docs/fcm_backend_real_mode_fa.md`

---

## Documentation

Important docs included in `project/docs/`:
- release checklist
- deployment guide
- firebase setup
- connector setup
- privacy policy
- terms and risk
- user guide
- technical handover
- run-on-your-system guide

---

## Current Product Stage

This repository is best described as:

**A product-ready foundation for a mobile AI trading assistant**, suitable for:
- demo environments
- MVP presentation
- team handoff
- continued production development

---

## Safety Notice
- No guaranteed profit
- No guaranteed signal accuracy
- Always use testnet/demo first
- Always verify risk limits before live execution
- Backtest results alone are not sufficient for live trading decisions

---

## Next Recommended Steps
- Add real Firebase project files
- Complete MT5 / cTrader production bridges
- Expand optimization logic
- Improve chart interaction further
- Harden production deployment and monitoring

---

## Disclaimer

This software is for analysis, workflow support, and controlled execution assistance. The user remains fully responsible for all trading decisions and risk exposure.
