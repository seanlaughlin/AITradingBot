import json
import os
from datetime import datetime

from alpaca.trading import MarketOrderRequest
from alpaca.trading.client import TradingClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.requests import StockLatestQuoteRequest


class Trader:
    def __init__(self, api_key, api_secret):
        self.api = TradingClient(api_key, api_secret, paper=True)
        self.historical_data_api = StockHistoricalDataClient(api_key, api_secret)
        self.account = dict(self.api.get_account())
        self.holding_order = len(self.api.get_all_positions()) != 0
        self.qtyHeld = 0
        if len(self.api.get_all_positions()) > 0:
            self.buy_price = self.api.get_all_positions()[0].avg_entry_price
        else:
            self.buy_price = 0
        self.bought_at = ""

    def buy(self, symbol, qty, multiplier):
        try:
            if not self.holding_order:
                order_details = MarketOrderRequest(symbol=symbol, qty=qty*multiplier, side=OrderSide.BUY, time_in_force=TimeInForce.GTC)
                order = self.api.submit_order(order_data=order_details)
                if order.filled_at is None:
                    raise Exception('Order not filled. Queued for market open.')
                self.buy_price = self.get_price(symbol, 'buy')
                print(f"Bought {qty * multiplier} shares of {symbol} at ${self.buy_price} successfully.")
                self.holding_order = True
                self.qtyHeld = qty
                self.bought_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                print("Currently holding an order. No buy executed.")
        except Exception as e:
            print(f"Failed to buy {qty} shares of {symbol}: {e}")

    def sell(self, symbol):
        try:
            if self.holding_order:
                bid_price = self.get_price(symbol, 'sell')
                self.api.close_all_positions(cancel_orders=True)
                quantity = self.api.get_all_positions()[0].qty
                print(f"Sold {quantity} shares of {symbol} at ${bid_price} successfully.")
                self.holding_order = False
                self.update_trade_history(symbol, bid_price)
                self.qtyHeld = 0
                self.buy_price = 0
                self.bought_at = ""
            else:
                print('Unable to sell. Not currently holding a position.')
        except Exception as e:
            print(f"Failed to sell {self.qtyHeld} shares of {symbol}: {e}")

    def get_price(self, symbol, side):
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        latest_quote = self.historical_data_api.get_stock_latest_quote(request_params=request_params)
        if side == 'buy':
            return latest_quote['SPY'].ask_price
        elif side == 'sell':
            return latest_quote['SPY'].bid_price
        else:
            print('No side (buy/sell) specified, unable to provide quote.')

    def check_balance(self):
        account = self.api.get_account()
        return float(account.portfolio_value)

    def check_positions(self):
        positions = self.api.get_all_positions()
        return positions

    def update_trade_history(self, symbol, sell_price):
        pnl = (sell_price - self.buy_price) * self.qtyHeld

        trade_data = {
            "symbol": symbol,
            "qty": self.qtyHeld,
            "buy_price": self.buy_price,
            "sell_price": sell_price,
            "pnl": round(pnl, 2),
            "bought_at": self.bought_at,
            "sold_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_value": "${:,.2f}".format(self.check_balance())
        }

        trade_history_file = "trade_history.json"
        if not os.path.exists(trade_history_file):
            with open(trade_history_file, "w") as f:
                json.dump([trade_data], f, indent=4)
        else:
            with open(trade_history_file, "r+") as f:
                data = json.load(f)
                data.append(trade_data)
                f.seek(0)
                json.dump(data, f, indent=4)

    def is_holding_position(self):
        return self.holding_order
