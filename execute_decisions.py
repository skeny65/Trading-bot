import logging
from client import alpaca_client
from bot_registry import BotRegistry

logger = logging.getLogger(__name__)

class BotManagerExecutor:
    """
    Service responsible for applying the Bot Manager's verdicts to the live system.
    It bridges the gap between intelligence and execution.
    """
    
    def __init__(self):
        self.api = alpaca_client.api
        self.bot_registry = BotRegistry()
        
    def apply_verdict(self, strategy_id: str, verdict: str):
        """
        Translates a quantitative verdict (PAUSE/REACTIVATE/HOLD) into system actions.
        """
        logger.info(f"Applying verdict '{verdict}' to strategy: {strategy_id}")
        
        if verdict == "PAUSE":
            # 1. Cancel all open orders for this strategy to prevent unintended fills
            # Note: In a production environment, you might want to filter by symbol 
            # if multiple strategies trade the same asset.
            try:
                self.api.cancel_all_orders()
                logger.info(f"All open orders cancelled for {strategy_id} suspension.")
            except Exception as e:
                logger.error(f"Failed to cancel orders during PAUSE: {e}")
            
            # 2. Update status in registry to block future signals in bot-core
            self.bot_registry.set_status(strategy_id, "PAUSED")
            self.notify(f"🛑 Bot {strategy_id} PAUSED by Bot Manager due to performance thresholds.")
            
        elif verdict == "REACTIVATE":
            # 1. Allow signals to pass through again
            self.bot_registry.set_status(strategy_id, "ACTIVE")
            self.notify(f"✅ Bot {strategy_id} REACTIVATED by Bot Manager.")
            
        elif verdict == "HOLD":
            # No state change, continue monitoring
            self.notify(f"⏸️ Bot {strategy_id} on HOLD - status maintained.")

    def notify(self, message: str):
        """
        Placeholder for notification dispatch (Telegram/Discord).
        Currently logs to console.
        """
        logger.info(f"[NOTIFICATION] {message}")
        # TODO: Integration with notifications/telegram_bot.py