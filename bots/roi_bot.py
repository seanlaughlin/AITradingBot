import yfinance as yf
from ta.trend import MACD
from ta.momentum import roc
from keras.models import model_from_json
import numpy as np
import joblib


class RoiBot:
    def __init__(self, ticker_symbol, model_architecture_path, model_weights_path, scaler_X_path, scaler_y_path):
        self.prediction_candle = None
        self.ticker_symbol = ticker_symbol
        self.model = self.load_model(model_architecture_path, model_weights_path)
        self.data = self.get_last_26_candles()
        self.scaler_X = self.load_scaler(scaler_X_path)
        self.scaler_y = self.load_scaler(scaler_y_path)
        self.update_features()

    def load_model(self, model_architecture_path, model_weights_path):
        with open(model_architecture_path, 'r') as json_file:
            loaded_model_json = json_file.read()

        loaded_model = model_from_json(loaded_model_json)

        loaded_model.load_weights(model_weights_path)

        return loaded_model

    def load_scaler(self, scaler_path):
        scaler = joblib.load(scaler_path)
        return scaler

    def get_last_26_candles(self):
        data = yf.download(self.ticker_symbol, interval='15m', period='5d', prepost=True)
        last_26_candles = data.iloc[-26:]
        return last_26_candles

    def calculate_macd_momentum(self):
        macd = MACD(self.data['Close'])
        self.data['MACD'] = macd.macd()

        momentum = roc(self.data['Close'])
        self.data['Momentum'] = momentum

    def engineer_features(self):
        self.data['MACD_Cross'] = 0
        self.data.loc[self.data['MACD'] > self.data['MACD'].shift(1), 'MACD_Cross'] = 1

        self.data['Momentum_Change'] = self.data['Momentum'].diff()

    def update_features(self):
        self.data = yf.download(self.ticker_symbol, interval='15m', period='7d', prepost=True)

        macd = MACD(self.data['Close'])
        self.data['MACD'] = macd.macd()
        self.data['MACD_Signal'] = macd.macd_signal()
        self.data['MACD_Cross'] = np.where((self.data['MACD'] > self.data['MACD_Signal']) & (
                self.data['MACD'].shift(1) <= self.data['MACD_Signal'].shift(1)), 1, 0)

        momentum = roc(self.data['Close'])
        self.data['Momentum'] = momentum
        self.data['Momentum_Change'] = self.data['Momentum'].diff()

        latest_candle = self.data.iloc[-1]
        latest_candle_features = [
            latest_candle['Close'],
            latest_candle['Volume'],
            latest_candle['Momentum'],
            latest_candle['MACD_Cross'],
            latest_candle['Momentum_Change']
        ]
        self.prediction_candle = self.scaler_X.transform(np.array(latest_candle_features).reshape(1, -1))

    def predict_roi(self):
        prediction = self.model.predict(self.prediction_candle)
        prediction_scaled = self.scaler_y.inverse_transform(prediction)
        return prediction_scaled[0][0]
