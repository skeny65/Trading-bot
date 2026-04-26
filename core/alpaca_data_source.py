import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def _build_api():
    """
    Intenta crear el cliente real de Alpaca.
    Si las credenciales faltan o la librería no está disponible,
    devuelve None y el data source operará en modo simulado.
    """
    try:
        import alpaca_trade_api as tradeapi
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")

        if not api_key or not secret_key:
            logger.warning("AlpacaDataSource: credenciales no configuradas, modo simulado activo")
            return None

        return tradeapi.REST(api_key, secret_key, base_url, api_version='v2')
    except ImportError:
        logger.warning("alpaca_trade_api no instalado, modo simulado activo")
        return None
    except Exception as e:
        logger.warning(f"Error inicializando cliente Alpaca: {e}, modo simulado activo")
        return None


class AlpacaDataSource:
    """
    Data collection service for the Bot Manager.
    Provides methods to fetch positions, orders, and historical market data.
    Falls back to synthetic data when in dry-run mode or API is unavailable.
    """
    def __init__(self):
        self.api = _build_api()
        self.dry_run = self.api is None

    def get_positions(self):
        if self.dry_run:
            return []
        try:
            return self.api.list_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_order_history(self, days=30):
        if self.dry_run:
            return []
        try:
            after = (datetime.now() - timedelta(days=days)).isoformat()
            return self.api.list_orders(status='all', after=after)
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return []

    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetches historical price bars for a symbol.
        Returns a pandas DataFrame. Falls back to synthetic data on failure.
        """
        if not self.dry_run:
            try:
                return self.api.get_bars(symbol, timeframe, limit=limit).df
            except Exception as e:
                logger.error(f"Error fetching bars for {symbol}: {e}. Usando datos sintéticos.")

        # Synthetic fallback: realistic random walk
        return self._synthetic_bars(symbol, limit)

    def _synthetic_bars(self, symbol: str, periods: int) -> pd.DataFrame:
        """Genera barras OHLCV simuladas para modo dry run o cuando la API falla."""
        np.random.seed(hash(symbol) % (2**31))
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
        close = 400 * np.cumprod(1 + np.random.normal(0.0003, 0.012, periods))
        volume = np.random.randint(50_000_000, 100_000_000, periods).astype(float)
        df = pd.DataFrame({
            "open": close * np.random.uniform(0.995, 1.005, periods),
            "high": close * np.random.uniform(1.001, 1.015, periods),
            "low": close * np.random.uniform(0.985, 0.999, periods),
            "close": close,
            "volume": volume,
        }, index=dates)
        return df

    def get_price_provider(self, strategy_id: str, start_date: str, days: int) -> list:
        """Returns closing prices for the given strategy's symbol."""
        symbol_map = {"strategy_001": "SPY", "strategy_002": "QQQ", "strategy_003": "IWM"}
        symbol = symbol_map.get(strategy_id, "SPY")

        if self.dry_run:
            return self._synthetic_bars(symbol, days)['close'].tolist()

        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = start_dt + timedelta(days=days)
            bars = self.api.get_bars(
                symbol, "1Day",
                start=start_dt.isoformat(),
                end=end_dt.isoformat()
            ).df
            return [] if bars.empty else bars['close'].tolist()
        except Exception as e:
            logger.error(f"Hindsight Price Provider Error for {strategy_id}: {e}")
            return self._synthetic_bars(symbol, days)['close'].tolist()

    def get_trade_provider(self, strategy_id: str, start_date: str, days: int) -> list:
        """Returns trades executed after the decision date."""
        if self.dry_run:
            return []
        try:
            after_dt = datetime.fromisoformat(start_date)
            orders = self.api.list_orders(status='all', after=after_dt.isoformat())
            return [order._raw for order in orders if order.status == 'filled']
        except Exception as e:
            logger.error(f"Hindsight Trade Provider Error for {strategy_id}: {e}")
            return []