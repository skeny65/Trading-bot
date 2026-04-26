import os
from typing import Dict, List
from core.bot_registry import BotRegistry
from core.alpaca_client import AlpacaClient
from utils.dry_run_logger import DryRunLogger


class DecisionExecutor:
    """
    aplica veredictos del bot manager a los bots.
    respeta el modo dry run para simulación segura.
    """
    
    def __init__(self, bot_registry: BotRegistry, notifier=None):
        self.registry = bot_registry
        self.alpaca = AlpacaClient()
        self.dry_run = self.alpaca.dry_run
        self.logger = DryRunLogger() if self.dry_run else None
        self.notifier = notifier
    
    def apply_pause(self, bot_id: str, reason: str, metrics: Dict):
        """
        pausa un bot: cancela órdenes y bloquea señales.
        """
        self.registry.set_status(bot_id, "paused", reason)
        self.registry.update_metrics(bot_id, metrics)
        
        if self.dry_run:
            cancel_result = self.alpaca.cancel_all_orders(bot_id)
            if self.logger:
                self.logger.log_pause(bot_id, reason, metrics)
            
            print(f"[dry run] bot {bot_id} pausado (simulado)")
            return {
                "status": "paused_simulated",
                "bot_id": bot_id,
                "mode": "dry_run"
            }
        
        print(f"[live] bot {bot_id} pausado - órdenes canceladas")
        return {"status": "paused", "bot_id": bot_id, "mode": "live"}
    
    def apply_reactivate(self, bot_id: str, reason: str, metrics: Dict):
        """
        reactiva un bot: permite nuevas señales.
        """
        self.registry.set_status(bot_id, "active", reason)
        self.registry.update_metrics(bot_id, metrics)
        
        if self.dry_run:
            if self.logger:
                self.logger.log_reactivate(bot_id, reason, metrics)
            print(f"[dry run] bot {bot_id} reactivado (simulado)")
            return {"status": "reactivated_simulated", "bot_id": bot_id, "mode": "dry_run"}
        
        print(f"[live] bot {bot_id} reactivado")
        return {"status": "reactivated", "bot_id": bot_id, "mode": "live"}
    
    def apply_hold(self, bot_id: str, reason: str):
        print(f"[{'dry run' if self.dry_run else 'live'}] bot {bot_id} en hold")
        return {"status": "hold", "bot_id": bot_id, "mode": "dry_run" if self.dry_run else "live"}
    
    def execute_all(self, decisions: List[Dict]) -> List[Dict]:
        results = []
        for decision in decisions:
            bot_id = decision["strategy_id"]
            verdict = decision["verdict"]
            reason = decision.get("reason", "")
            metrics = decision.get("metrics", {})
            
            # Normalize verdict to lowercase for comparison
            verdict_lower = verdict.lower() if verdict else "hold"
            if verdict_lower == "pause":
                result = self.apply_pause(bot_id, reason, metrics)
            elif verdict_lower in ("reactivate", "active"):
                result = self.apply_reactivate(bot_id, reason, metrics)
            else:
                result = self.apply_hold(bot_id, reason)
            results.append(result)
        return results