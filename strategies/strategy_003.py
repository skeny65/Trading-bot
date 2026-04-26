import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy

class Strategy003(BaseStrategy):
    """
    BREAKOUT MOMENTUM (Donchian Channels + Volume)
    """
    def __init__(self, config: dict = None):
        params = {"donchian": 20, "vol_mult": 1.5, "atr_multiplier_tp": 4.0}
        if config: params.update(config)
        super().__init__(params)
        self.name = "strategy_003_breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        p = self.config

        # Donchian Channels
        data['d_high'] = data['high'].rolling(p['donchian']).max()
        data['d_low'] = data['low'].rolling(p['donchian']).min()
        
        # Volumen
        data['vol_avg'] = data['volume'].rolling(20).mean()
        data['atr'] = ta.atr(data['high'], data['low'], data['close'])

        # Entrada Long: Cierre por encima del máximo de N periodos con volumen
        data['long_entry'] = (data['close'] > data['d_high'].shift(1)) & \
                             (data['volume'] > data['vol_avg'] * p['vol_mult']) & \
                             (data['atr'] > data['atr'].rolling(100).median())

        data['signal'] = 0
        data.loc[data['long_entry'], 'signal'] = 1
        
        # Gestión de salida
        data['stop_loss'] = data['close'] - data['atr']
        data['take_profit'] = data['close'] + (data['atr'] * p['atr_multiplier_tp'])

        return data