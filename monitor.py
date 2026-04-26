import logging
import json
from bot_registry import BotRegistry

class BotManagerMonitor:
    """
    Monitors bot performance and health status.
    """
    def __init__(self):
        self.registry = BotRegistry()

    def get_bot_status(self, strategy_id: str) -> str:
        """Queries the persistent registry for the current bot state."""
        return self.registry.get_status(strategy_id)

    def is_paused(self, strategy_id: str) -> bool:
        """Convenience method to check if a bot is paused."""
        return self.get_bot_status(strategy_id) == "PAUSED"

    def get_bot_metrics(self, strategy_id: str) -> dict:
        """Retrieves last calculated metrics from the performance storage."""
        try:
            with open("data/bot_performance.json", "r") as f:
                perf = json.load(f)
            return perf.get(strategy_id, {"win_rate": 0, "drawdown": 0})
        except FileNotFoundError:
            return {"win_rate": 0.5, "drawdown": 0}

    def record_trade(self, strategy_id: str, order):
        logging.info(f"Recording trade for {strategy_id}: {getattr(order, 'id', 'N/A')}")

    def get_summary(self) -> str:
        """Generates a summary for the health check endpoint."""
        status = "System monitoring active."
        # Optional: Add logic to count paused vs active bots from registry
        return status