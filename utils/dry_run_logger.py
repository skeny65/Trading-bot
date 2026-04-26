import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class DryRunLogger:
    """
    registra en detalle qué se habría hecho en modo dry run.
    permite auditar decisiones y comparar contra ejecución real posterior.
    """
    
    def __init__(self, log_dir: str = "logs/dry_run"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.today_file = os.path.join(
            log_dir, 
            f"{datetime.now().strftime('%Y-%m-%d')}_simulation.jsonl"
        )
    
    def log_action(self, action_type: str, details: Dict):
        """
        registra una acción simulada.
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "mode": "dry_run",
            "action_type": action_type,
            "details": details
        }
        
        with open(self.today_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, default=str) + "\n")
    
    def log_order(self, order_request: Dict, simulated_response: Dict):
        """
        loguea una orden que se habría enviado a alpaca.
        """
        self.log_action("order", {
            "request": order_request,
            "simulated_response": simulated_response,
            "would_execute": True,
            "reason": "dry_run_mode_active"
        })
    
    def log_cancel(self, bot_id: str, orders_that_would_be_cancelled: List[str]):
        """
        loguea órdenes que se habrían cancelado al pausar un bot.
        """
        self.log_action("cancel_orders", {
            "bot_id": bot_id,
            "orders": orders_that_would_be_cancelled,
            "would_execute": True
        })
    
    def log_pause(self, bot_id: str, reason: str, metrics: Dict):
        """
        loguea decisión de pausa con contexto completo.
        """
        self.log_action("pause_bot", {
            "bot_id": bot_id,
            "reason": reason,
            "metrics_at_pause": metrics,
            "would_execute": True
        })
    
    def log_reactivate(self, bot_id: str, reason: str, metrics: Dict):
        """
        loguea decisión de reactivación.
        """
        self.log_action("reactivate_bot", {
            "bot_id": bot_id,
            "reason": reason,
            "metrics_at_reactivate": metrics,
            "would_execute": True
        })
    
    def log_signal_rejected(self, signal: Dict, reason: str):
        """
        loguea señal rechazada por bot pausado.
        """
        self.log_action("signal_rejected", {
            "signal": signal,
            "rejection_reason": reason,
            "would_have_executed": False
        })
    
    def get_today_summary(self) -> Dict:
        """
        resumen de acciones simuladas del día.
        """
        if not os.path.exists(self.today_file):
            return {"actions": 0, "orders": 0, "cancels": 0, "pauses": 0, "reactivates": 0}
        
        counts = {"actions": 0, "orders": 0, "cancels": 0, "pauses": 0, "reactivates": 0, "signals_rejected": 0}
        
        with open(self.today_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                counts["actions"] += 1
                action = record.get("action_type")
                if action in ["order", "cancel_orders", "pause_bot", "reactivate_bot", "signal_rejected"]:
                    # Logic to increment specific counts
                    pass 
        return counts