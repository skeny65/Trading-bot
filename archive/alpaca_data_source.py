from datetime import datetime, timedelta, timezone
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

    def get_price_provider(self, strategy_id: str, start_date: str, days: int) -> list:
        """
        Returns a list of closing prices starting from start_date for the specified window.
        Used by HindsightEngine.
        """
        # Map strategy to symbol (This should ideally come from a config)
        symbol_map = {"strategy_001": "SPY", "strategy_002": "QQQ"}
        symbol = symbol_map.get(strategy_id, "SPY")
        
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = start_dt + timedelta(days=days)
            
            # Alpaca API expects ISO format
            bars = self.api.get_bars(
                symbol, 
                "1Day", 
                start=start_dt.isoformat(), 
                end=end_dt.isoformat()
            ).df
            
            if bars.empty:
                return []
            return bars['close'].tolist()
        except Exception as e:
            logger.error(f"Hindsight Price Provider Error for {strategy_id}: {e}")
            return []

    def get_trade_provider(self, strategy_id: str, start_date: str, days: int) -> list:
        """
        Returns trades executed after the decision. 
        (In this architecture, we return actual orders from history).
        """
        try:
            after_dt = datetime.fromisoformat(start_date)
            orders = self.api.list_orders(status='all', after=after_dt.isoformat())
            # Filter for specific strategy symbol (simplified)
            return [order._raw for order in orders if order.status == 'filled']
        except Exception as e:
            logger.error(f"Hindsight Trade Provider Error for {strategy_id}: {e}")
            return []