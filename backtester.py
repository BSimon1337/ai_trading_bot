from config import load_config
from tradingbot.app.backtest import run_backtest


if __name__ == "__main__":
    run_backtest(load_config(), print_summary=True)
