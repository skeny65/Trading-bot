import os
import json
import random
from datetime import datetime
from typing import Dict, Optional
from utils.retry_handler import alpaca_retry
from utils.circuit_breaker import alpaca_breaker
from utils.dry_run_logger import DryRunLogger


class AlpacaClient:
    """
    cliente de alpaca con soporte para dry run.
    en modo simulación, genera respuestas ficticias realistas.
    """
    
    def __init__(self):
        self.dry_run = os.getenv("EXECUTE_ORDERS", "false").lower() != "true"
        self.logger = DryRunLogger() if self.dry_run else None
        self.simulated_balance = float(os.getenv("DRY_RUN_INITIAL_BALANCE", "100000"))
        
        if self.dry_run:
            print("alpaca client: modo dry run activo")
            print(f"balance simulado: ${self.simulated_balance:,.2f}")
        else:
            print("alpaca client: modo live trading - se enviarán órdenes reales")
    
    def place_order(self, order_request: Dict) -> Dict:
        """
        envía orden con reintentos y circuit breaker.
        """
        if self.dry_run:
            return self._simulate_order(order_request)

        try:
            return alpaca_breaker.call(
                lambda: alpaca_retry.execute(self._place_order_live, order_request)
            )
        except Exception as e:
            print(f"Error crítico enviando orden: {e}")
            raise
    
    def cancel_all_orders(self, bot_id: str = None) -> Dict:
        """
        cancela órdenes abiertas o simula la cancelación.
        """
        if self.dry_run:
            simulated_orders = [f"sim_order_{random.randint(1000, 9999)}" for _ in range(random.randint(0, 3))]
            
            if self.logger:
                self.logger.log_cancel(bot_id or "unknown", simulated_orders)
            
            return {
                "status": "simulated_cancel",
                "cancelled_orders": simulated_orders,
                "bot_id": bot_id,
                "timestamp": datetime.now().isoformat()
            }
        
        raise NotImplementedError("modo live trading requiere implementación")
    
    def get_positions(self) -> Dict:
        """
        obtiene posiciones actuales o simula.
        """
        if self.dry_run:
            return {
                "status": "simulated",
                "positions": [],
                "balance": self.simulated_balance,
                "timestamp": datetime.now().isoformat()
            }
        
        raise NotImplementedError("modo live trading requiere implementación")
    
    def get_account(self) -> Dict:
        """
        obtiene información de cuenta o simula.
        """
        if self.dry_run:
            return {
                "status": "simulated",
                "account_number": "dry_run_account",
                "cash": self.simulated_balance,
                "portfolio_value": self.simulated_balance,
                "buying_power": self.simulated_balance * 2,
                "timestamp": datetime.now().isoformat()
            }
        
        raise NotImplementedError("modo live trading requiere implementación")
    
    def _simulate_order(self, order_request: Dict) -> Dict:
        """
        genera una respuesta de orden simulada realista.
        """
        order_id = f"dry_{random.randint(100000, 999999)}"
        symbol = order_request.get("symbol", "unknown")
        qty = order_request.get("qty", 0)
        side = order_request.get("side", "buy")
        
        # simular precio de ejecución
        base_price = random.uniform(50, 500)
        fill_price = base_price * random.uniform(0.995, 1.005)  # slippage simulado
        
        # simular comisión
        commission = fill_price * qty * 0.001
        
        simulated_response = {
            "id": order_id,
            "client_order_id": f"client_{order_id}",
            "symbol": symbol,
            "side": side,
            "qty": str(qty),
            "filled_qty": str(qty),
            "filled_avg_price": str(round(fill_price, 2)),
            "status": "filled",
            "commission": str(round(commission, 2)),
            "created_at": datetime.now().isoformat(),
            "filled_at": datetime.now().isoformat(),
            "mode": "dry_run"
        }
        
        if self.logger:
            self.logger.log_order(order_request, simulated_response)
        
        return simulated_response