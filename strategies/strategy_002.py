import pandas as pd
import pandas_ta as ta
from strategies.base_strategy import BaseStrategy

class Strategy002(BaseStrategy):
    """
    MEAN REVERSION (Bollinger Bands + Z-Score)
    """
    def __init__(self, config: dict = None):
        params = {"bb_period": 20, "bb_std": 2.0, "z_threshold": 2.0, "adx_max": 20}
        if config: params.update(config)
        super().__init__(params)
        self.name = "strategy_002_mean_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        p = self.config

        # Indicadores
        bb = ta.bbands(data['close'], length=p['bb_period'], std=p['bb_std'])
        data['bb_l'] = bb[f'BBL_{p["bb_period"]}_{p["bb_std"]}']
        data['bb_m'] = bb[f'BBM_{p["bb_period"]}_{p["bb_std"]}']
        data['bb_h'] = bb[f'BBU_{p["bb_period"]}_{p["bb_std"]}']
        
        # Z-Score manual para precisión
        rolling_mean = data['close'].rolling(p['bb_period']).mean()
        rolling_std = data['close'].rolling(p['bb_period']).std()
        data['zscore'] = (data['close'] - rolling_mean) / rolling_std
        
        adx = ta.adx(data['high'], data['low'], data['close'])
        data['adx'] = adx[f'ADX_14']

        # Entradas
        # Long: Precio rompe hacia arriba la banda inferior tras estar sobrevendido
        data['long_entry'] = (data['close'].shift(1) < data['bb_l'].shift(1)) & \
                             (data['close'] > data['bb_l']) & \
                             (data['zscore'] < -p['z_threshold']) & \
                             (data['adx'] < p['adx_max'])

        data['signal'] = 0
        data.loc[data['long_entry'], 'signal'] = 1
        
        # Take Profit en la media de Bollinger
        data['take_profit'] = data['bb_m']
        data['stop_loss'] = data['bb_l'] - (data['bb_m'] - data['bb_l']) # SL simétrico

        return data