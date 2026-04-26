from datetime import datetime, timedelta
from client import alpaca_client
import logging

logger = logging.getLogger(__name__)

class AlpacaDataSource:
    """
    Data collection service for the Bot Manager.
    Provides methods to fetch positions, orders, and historical market data.
    """
    def __init__(self):
        self.api = alpaca_client.api

    def get_positions(self):
        """Returns current open positions from Alpaca."""
        try:
            return self.api.list_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_order_history(self, days=30):
        """Returns a list of orders (filled, canceled, etc.) within the last N days."""
        try:
            # Calculate the RFC3339 timestamp required by Alpaca
            after = (datetime.now() - timedelta(days=days)).isoformat()
            return self.api.list_orders(status='all', after=after)
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return []

    def get_bars(self, symbol, timeframe, limit=100):
        """
        Fetches historical price bars for a symbol.
        Returns a pandas DataFrame for easier quantitative analysis.
        """
        try:
            return self.api.get_bars(symbol, timeframe, limit=limit).df
        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return None