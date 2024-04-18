from datetime import datetime

from dotenv import load_dotenv

from bots.roi_bot import RoiBot
from bots.sentiment_bot import SentimentBot
from bots.trader_bot import Trader
import os
import time


def calculate_roi_points(predicted_roi):
    roi_points = 0
    if predicted_roi > 0.1:
        roi_points = roi_points + 1
    if predicted_roi > 0.5:
        roi_points = roi_points + 1
    if predicted_roi < 0:
        roi_points = roi_points - 1
    if predicted_roi < -0.5:
        roi_points = roi_points - 1
    return roi_points


if __name__ == '__main__':
    load_dotenv()
    ticker_symbol = 'SPY'

    # setup for trader bot
    api_key = os.getenv('APCA-API-KEY-ID')
    api_secret = os.getenv('APCA-API-SECRET-KEY')
    trader = Trader(api_key=api_key, api_secret=api_secret)

    # setup for roi bot
    model_architecture_path = 'resources/roi_lstm/roi_lstm_model_architecture.json'
    model_weights_path = 'resources/roi_lstm/roi_lstm_model_weights.h5'
    scaler_X_path = "resources/roi_lstm/scaler_X.pkl"
    scaler_y_path = "resources/roi_lstm/scaler_y.pkl"

    roi_bot = RoiBot(ticker_symbol, model_architecture_path, model_weights_path, scaler_X_path, scaler_y_path)

    # setup for sentiment bot
    azure_api_key = os.getenv('AZURE-KEY')
    azure_endpoint = os.getenv('AZURE-ENDPOINT')
    google_news_rss = os.getenv("GOOGLE-NEWS-RSS")
    sentiment_bot = SentimentBot(num_results=5, rss_url=google_news_rss, azure_endpoint=azure_endpoint, azure_key=azure_api_key)

    while True:
        roi_bot.update_features()
        predicted_roi = roi_bot.predict_roi()
        print('Time: ', datetime.now())
        print("Predicted ROI (15 minutes):", predicted_roi)
        roi_points = calculate_roi_points(predicted_roi)
        print('ROI Points: ', roi_points)
        print('Getting news sentiment...')
        sentiment_bot.update()
        sentiment_points = sentiment_bot.get_overall_sentiment()
        print('Sentiment Points: ', sentiment_points)
        total_points = sentiment_points + roi_points
        print('Total Points: ', total_points)

        balance = trader.check_balance()
        formatted_balance = "${:,.2f}".format(balance)

        print('Account value: ', formatted_balance)
        if 0.5 <= total_points <= 2:
            print('Executing buy order (normal)...')
            trader.buy(symbol=ticker_symbol, qty=10, multiplier=1)
            print('New balance: ', "${:,.2f}".format(trader.check_balance()))
        elif total_points > 2:
            print('Executing buy order (large)...')
            trader.buy(symbol=ticker_symbol, qty=10, multiplier=2)
            print('New balance: ', "${:,.2f}".format(trader.check_balance()))
        elif total_points < 0:
            print('Executing sell order...')
            trader.sell(symbol=ticker_symbol)
            print('New balance: ', "${:,.2f}".format(trader.check_balance()))
        else:
            print("No trade action taken.")

        print('Sleeping for 15 min...')
        time.sleep(15 * 60)
