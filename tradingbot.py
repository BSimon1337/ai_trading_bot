from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from pandas import Timedelta
from finbert_utils import estimate_sentiment

from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env file

# Access environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET" : API_SECRET,
    "PAPER": True
}

class MLTrader(Strategy):
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url= BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')
    
   
    def get_sentiment(self):
        today, three_days_prior = self.get_dates() 
        news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)
        news = [ev.__dict__["_raw"]["headline"]for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment


    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > 0.999:
                if self.last_trade == "sell":
                    print("Selling all positions as last trade was 'sell'")
                    self.sell_all()

                if quantity > 0:
                    # For backtesting: Use simple market order for buy
                    order = self.create_order(
                        self.symbol,
                        quantity,
                        "buy",
                        type="market"
                    )
                    print("Market buy order created for backtesting:", order)
                    
                    # Uncomment below for live trading with bracket order
                    # order = self.create_order(
                    #     self.symbol,
                    #     quantity,
                    #     "buy",
                    #     type="bracket",
                    #     take_profit_price=last_price * 1.20,
                    #     stop_loss_price=last_price * 0.95
                    # )
                    # print("Bracket buy order created:", order)

                    submission_result = self.submit_order(order)
                    print("Order submission result:", submission_result)
                    self.last_trade = "buy"
                else:
                    print("Quantity is zero, skipping buy order.")

            elif sentiment == "negative" and probability > 0.999:
                if self.last_trade == "buy":
                    print("Selling all positions as last trade was 'buy'")
                    self.sell_all()

                if quantity > 0:
                    # For backtesting: Use simple market order for sell
                    order = self.create_order(
                        self.symbol,
                        quantity,
                        "sell",
                        type="market"
                    )
                    print("Market sell order created for backtesting:", order)
                    
                    # Uncomment below for live trading with bracket order
                    # order = self.create_order(
                    #     self.symbol,
                    #     quantity,
                    #     "sell",
                    #     type="bracket",
                    #     take_profit_price=last_price * 0.8,
                    #     stop_loss_price=last_price * 1.05
                    # )
                    # print("Bracket sell order created:", order)

                    submission_result = self.submit_order(order)
                    print("Order submission result:", submission_result)
                    self.last_trade = "sell"
                else:
                    print("Quantity is zero, skipping sell order.")

start_date = datetime(2020,1,1)
end_date = datetime(2024,11,1)

broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"SPY","cash_at_risk":.5})

print("Testing get_dates output:", strategy.get_dates())

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol":"SPY","cash_at_risk":.5}
)