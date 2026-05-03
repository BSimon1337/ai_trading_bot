# AI Trading Bot Presentation

Approximate length: 8 minutes

## Slide 1: Title

**A Sentiment-Aware Machine Learning Trading Bot with Runtime Guardrails**

- Beau
- Final Project
- May 2026

**Speaker notes, about 30 seconds**

Hi, my project is an AI trading bot built around machine-learning signals, financial-news sentiment, and runtime safety controls. The goal was not just to make a model that predicts price movement, but to build a more complete trading prototype that can backtest, run in paper or live modes, log evidence, and show what it is doing through a dashboard.

## Slide 2: Project Goal

**Problem**

- Trading bots need more than prediction accuracy
- They need data handling, risk controls, execution safeguards, and observability
- Operators need to know why the bot traded or did not trade

**Project goal**

- Build a modular AI trading bot that combines model signals, sentiment, and guardrails

**Speaker notes, about 50 seconds**

The main problem I focused on is that algorithmic trading systems are often judged by one number, like model accuracy or backtest return. But if a bot is going to run in paper trading or potentially live trading, the system needs much more around the model. It needs to know where data came from, whether data is stale, whether live trading is allowed, how big orders can be, and how to explain skipped trades. So my project goal was to build a modular prototype that connects the predictive part with a safer runtime and a monitoring layer.

## Slide 3: System Overview

**Core components**

- Python 3.10 trading application
- Lumibot strategy runtime
- Alpaca market data and broker integration
- Local CSV evidence logs
- Flask monitoring dashboard
- Optional tray app and runtime manager

**Speaker notes, about 55 seconds**

The system is written in Python 3.10. Lumibot handles the strategy runtime, and Alpaca is used for market data and broker integration. The bot writes local CSV logs for decisions, fills, and daily snapshots. I also built a Flask dashboard that reads those files and summarizes the current state of the bot. Later project work added runtime management, so the dashboard can show whether a bot process is running, stopped, stale, or failed. This made the project more like a full operator tool instead of only a model experiment.

## Slide 4: Data and Features

**Historical data**

- Daily bars from 2022 through 2024
- Symbols: SPY, BTCUSD, ETHUSD
- Cached news records by symbol

**Features**

- Technical: return, SMA, EMA, RSI, volume z-score
- Sentiment: average headline sentiment and headline count
- Target: next-day positive return

**Speaker notes, about 55 seconds**

For the empirical part, I used daily market bars from 2022 through 2024. The main symbols were SPY, BTCUSD, and ETHUSD. SPY gives an equity benchmark, while BTC and ETH test the crypto side. The technical features include one-day return, moving averages, RSI, and a volume z-score. The sentiment features are based on cached financial headlines, using an average sentiment score and headline count. Each row is labeled by whether the next daily return is positive, so the machine-learning task is directional classification.

## Slide 5: Modeling Method

**Models evaluated**

- Logistic regression with technical features
- Logistic regression with technical plus sentiment features
- XGBoost with full feature set

**Signal conversion**

- Model predicts probability of upward move
- Probability is compared to configurable buy and sell thresholds
- Sentiment can confirm, block, or provide fallback signals

**Speaker notes, about 60 seconds**

I evaluated three model setups. The first is a technical-only logistic regression model. The second adds sentiment features to logistic regression. The third uses XGBoost with the full feature set. The model output is a probability that the next move is upward. The strategy converts that probability into buy, sell, or hold based on configurable thresholds. Sentiment is used carefully: it can confirm a signal, block a signal when sentiment strongly disagrees, or act as a fallback when the model does not produce an actionable signal.

## Slide 6: Risk Controls and Runtime Safety

**Guardrails**

- Paper/live mode separation
- Live trading requires explicit enablement and confirmation token
- Position size and leverage limits
- Daily loss limit
- Trade-per-day limit
- Cooldown after losses
- Kill switch and stale-data checks
- Broker rejection logging

**Speaker notes, about 65 seconds**

This is one of the most important parts of the project. The bot has several layers of guardrails. Live trading is fail-closed: it will not run live unless paper mode is off, credentials exist, live trading is enabled, and a run-specific confirmation token matches. The strategy also limits position size, gross leverage, daily losses, trades per day, and consecutive losses. There is a cooldown after losing trades, a kill switch, and stale-data checks. If the broker rejects an order, that gets logged as evidence instead of disappearing into the runtime.

## Slide 7: Monitoring and Observability

**Dashboard shows**

- Current account and symbol state
- Last decision and last fill
- Sentiment label, confidence, source, and fallback state
- Recent headline previews
- Runtime process state
- Recent control actions
- Current, stale, historical, or unavailable evidence

**Speaker notes, about 55 seconds**

The dashboard is meant to answer a practical question: what is the bot doing right now, and why? It shows the latest decision, latest fill, sentiment state, headline evidence, account information, and runtime state. One problem I specifically handled is stale evidence. Old logs should not look like current trading activity. So the monitor distinguishes current, stale, historical, and unavailable evidence. This is important because automated systems can be misleading if they only show the last thing that happened without showing how old it is.

## Slide 8: Results

**Model evaluation**

- Best directional accuracy: XGBoost full model, 52.4%
- Best ROC AUC: XGBoost full model, 0.521
- Best cross-validation strategy Sharpe: technical logistic model, 1.084

**Out-of-sample findings**

- Conservative and medium settings reduced drawdown
- Strategy returns did not consistently beat buy-and-hold
- Aggressive BTCUSD setting failed out of sample

**Speaker notes, about 80 seconds**

The results were mixed, which is actually useful. The best model accuracy was the XGBoost full model at about 52.4 percent, with a ROC AUC of 0.521. That is only modest directional predictability. In the strategy summaries, the technical logistic model had the best cross-validation strategy Sharpe. In the out-of-sample 2024 matrix, the conservative and medium settings had much smaller drawdowns than buy-and-hold, especially for BTCUSD. But they also did not match the benchmark's total return. The aggressive BTCUSD setup looked strong in exploratory results but failed out of sample, losing over 60 percent. So the results support conservative risk controls rather than aggressive deployment.

## Slide 9: Limitations

**Main limitations**

- Daily bars only
- No full order-book replay
- Slippage, latency, spreads, and partial fills are simplified
- Dataset is small for machine learning
- News availability can fail or be limited
- Results are research evidence, not trading guarantees

**Speaker notes, about 50 seconds**

There are several important limitations. The study uses daily bars, not full order-book replay. That means latency, bid-ask spread, partial fills, and market impact are not modeled in full detail. The dataset is also small for machine learning, especially for sentiment. Another limitation is news availability. If the API does not provide news, or if local sentiment dependencies are unavailable, the bot falls back to neutral sentiment. That is safer operationally, but it also limits predictive power. Because of these limitations, the results should be treated as research evidence, not as a claim that the bot will make money.

## Slide 10: Conclusion

**Takeaways**

- The project connects ML signals with a real trading runtime
- Safety and observability are as important as prediction
- Conservative settings were more stable than aggressive settings
- The dashboard helps explain both trades and skipped trades

**Future work**

- Broader stock universe scanner
- More walk-forward validation
- Better transaction-cost modeling
- More robust feature and sentiment evaluation

**Speaker notes, about 60 seconds**

To conclude, this project shows a modular AI trading bot that combines machine-learning signals, sentiment analysis, execution guardrails, and operator observability. The strongest finding is not that the bot reliably beats buy-and-hold. The stronger lesson is that a trading bot needs conservative risk controls and transparent evidence before it should be trusted even in paper trading. Future work would include expanding the stock universe scanner, adding more walk-forward validation, improving transaction-cost modeling, and testing more feature sets. Overall, the project became both a trading experiment and a software-engineering exercise in making automated decisions visible and safer.

## Optional Closing Line

Thank you. I am happy to answer questions about the model results, the runtime safeguards, or the dashboard design.

