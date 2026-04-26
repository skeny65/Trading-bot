import os
from typing import Dict
from core.alpaca_client import AlpacaClient


class OrderRouter:
    """
    enruta órdenes a alpaca, con soporte transparente para dry run.
    """
    
    def __init__(self):
        self.client = AlpacaClient()
        self.dry_run = self.client.dry_run
    
    async def place_order(self, signal: Dict) -> Dict:
        """
        prepara y envía orden, o la simula.
        """
        order_request = {
            "symbol": signal.get("symbol"),
            "qty": signal.get("size", 0.1),
            "side": signal.get("action", "buy").lower(),
            "type": "market",
            "time_in_force": "day"
        }
        
        result = self.client.place_order(order_request)
        
        # agregar metadata del modo
        result["execution_mode"] = "dry_run" if self.dry_run else "live"
        result["original_signal"] = {
            "strategy_id": signal.get("strategy_id"),
            "confidence": signal.get("confidence")
        }
        
        return result

    async def cancel_for_bot(self, bot_id: str):
        return self.client.cancel_all_orders(bot_id)