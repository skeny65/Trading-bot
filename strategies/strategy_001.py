import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy

class Strategy001(BaseStrategy):
    """
    MOMENTUM TREND-FOLLOWING (RSI + EMA Crossover)
    """
    def __init__(self, config: dict = None):
        params = {
            "ema_fast": 9, "ema_slow": 21, "rsi_period": 14,
            "adx_threshold": 25, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 3.0
        }
        if config: params.update(config)
        super().__init__(params)
        self.name = "strategy_001_momentum"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        p = self.config

        # Indicadores
        data['ema_f'] = ta.ema(data['close'], length=p['ema_fast'])
        data['ema_s'] = ta.ema(data['close'], length=p['ema_slow'])
        data['rsi'] = ta.rsi(data['close'], length=p['rsi_period'])
        adx = ta.adx(data['high'], data['low'], data['close'])
        data['adx'] = adx[f'ADX_{p["rsi_period"]}']
        data['atr'] = ta.atr(data['high'], data['low'], data['close'])

        # Lógica Long
        data['long_entry'] = (data['ema_f'] > data['ema_s']) & \
                             (data['ema_f'].shift(1) <= data['ema_s'].shift(1)) & \
                             (data['rsi'] > 50) & (data['adx'] > p['adx_threshold'])

        # Lógica Short
        data['short_entry'] = (data['ema_f'] < data['ema_s']) & \
                              (data['ema_f'].shift(1) >= data['ema_s'].shift(1)) & \
                              (data['rsi'] < 50) & (data['adx'] > p['adx_threshold'])

        data['signal'] = 0
        data.loc[data['long_entry'], 'signal'] = 1
        data.loc[data['short_entry'], 'signal'] = -1

        # SL y TP dinámicos
        data['stop_loss'] = 0.0
        data['take_profit'] = 0.0
        
        # Aplicamos SL/TP solo en filas con señal
        mask_l = data['signal'] == 1
        data.loc[mask_l, 'stop_loss'] = data['close'] - (data['atr'] * p['atr_multiplier_sl'])
        data.loc[mask_l, 'take_profit'] = data['close'] + (data['atr'] * p['atr_multiplier_tp'])
        
        mask_s = data['signal'] == -1
        data.loc[mask_s, 'stop_loss'] = data['close'] + (data['atr'] * p['atr_multiplier_sl'])
        data.loc[mask_s, 'take_profit'] = data['close'] - (data['atr'] * p['atr_multiplier_tp'])

        return data