# ai_trading_bot Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-26

## Active Technologies
- Python 3.10 + Existing pinned runtime stack in `requirements.txt` / `pyproject.toml`: Lumibot, Alpaca integration via Lumibot and `alpaca-py`, pandas, numpy, scipy, yfinance, joblib, python-dotenv, Flask, pytest (004-preflight-offline-mode)
- File-based CSV logs, local fixture files for cached/offline news, model artifacts in `models/`, environment variables from `.env` / `env/.env` (004-preflight-offline-mode)
- Python 3.10 + Existing Flask/pandas/python-dotenv stack; add `pystray==0.19.5` and `Pillow==11.3.0` for tray icon support (005-dashboard-tray-app)
- Existing local CSV runtime evidence files under configured log paths; no database (005-dashboard-tray-app)
- Python 3.10 + Existing Flask, pandas, python-dotenv, pytest, pystray, Pillow stack already used by the monitor feature (006-monitor-accuracy-refinement)
- Python 3.10 + Existing Flask, pandas, python-dotenv, Lumibot runtime stack, local FinBERT path through `transformers` and `torch`, pytest (007-sentiment-observability)
- Existing local CSV runtime evidence files plus current news/sentiment runtime flows; no database (007-sentiment-observability)
- Python 3.10 + Existing Python runtime stack plus standard-library `subprocess`, `threading`, `json`, `pathlib`, and `dataclasses`; no new third-party dependency planned (008-runtime-manager)
- Existing CSV runtime evidence plus a local runtime-registry JSON/state file for managed process lifecycle metadata (008-runtime-manager)

- Python 3.10 + Lumibot, Alpaca integration via Lumibot broker support, pandas, joblib, python-dotenv, pytest (002-modular-trading-bot)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.10: Follow standard conventions

## Recent Changes
- 008-runtime-manager: Added Python 3.10 + Existing Python runtime stack plus standard-library `subprocess`, `threading`, `json`, `pathlib`, and `dataclasses`; no new third-party dependency planned
- 007-sentiment-observability: Added Python 3.10 + Existing Flask, pandas, python-dotenv, Lumibot runtime stack, local FinBERT path through `transformers` and `torch`, pytest
- 006-monitor-accuracy-refinement: Added Python 3.10 + Existing Flask, pandas, python-dotenv, pytest, pystray, Pillow stack already used by the monitor feature


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
