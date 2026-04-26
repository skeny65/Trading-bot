import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Interfaz base para todas las estrategias de trading.
    Asegura que todas reporten métricas y señales en el mismo formato.
    """
    def __init__(self, config: dict):
        self.config = config
        self.name = "base_strategy"
        self.version = "1.0.0"
        self.status = "ACTIVE"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Recibe OHLCV y retorna DataFrame con signal, position, stop_loss y take_profit.
        """
        pass

    def calculate_metrics(self, returns: pd.Series) -> dict:
        """
        Calcula métricas clave para el Bot Manager.
        """
        if returns.empty or len(returns) < 2:
            return {"status": "insufficient_data"}

        wins = returns[returns > 0]
        losses = returns[returns <= 0]
        
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0
        profit_factor = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float('inf')
        
        return {
            "strategy_id": self.name,
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": len(returns),
            "sharpe_ratio": round(self._sharpe(returns), 2),
            "max_drawdown": round(self._drawdown(returns), 2)
        }

    def _sharpe(self, returns):
        if returns.std() == 0: return 0.0
        return (returns.mean() / returns.std()) * np.sqrt(252)

    def _drawdown(self, returns):
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        dd = (cumulative - peak) / peak
        return dd.min() * 100