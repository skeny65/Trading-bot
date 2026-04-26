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
        self.live_api = None
        
        if self.dry_run:
            print("alpaca client: modo dry run activo")
            print(f"balance simulado: ${self.simulated_balance:,.2f}")
        else:
            print("alpaca client: modo live trading - se enviarán órdenes reales")
            self.live_api = self._build_live_api()

    def _normalize_base_url(self, base_url: str) -> str:
        # alpaca_trade_api.REST espera base URL sin sufijo /v2
        if not base_url:
            return "https://paper-api.alpaca.markets"
        return base_url[:-3] if base_url.endswith("/v2") else base_url

    def _build_live_api(self):
        try:
            import alpaca_trade_api as tradeapi

            api_key = os.getenv("ALPACA_API_KEY")
            secret_key = os.getenv("ALPACA_SECRET_KEY")
            base_url = self._normalize_base_url(os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"))

            if not api_key or not secret_key:
                raise ValueError("ALPACA_API_KEY/ALPACA_SECRET_KEY no configuradas")

            return tradeapi.REST(api_key, secret_key, base_url, api_version="v2")
        except Exception as e:
            print(f"Error inicializando Alpaca live API: {e}")
            raise

    def _place_order_live(self, order_request: Dict) -> Dict:
        if not self.live_api:
            raise RuntimeError("live_api no inicializada")

        submit_kwargs = {
            "symbol": order_request.get("symbol"),
            "qty": order_request.get("qty"),
            "side": order_request.get("side"),
            "type": order_request.get("type", "market"),
            "time_in_force": order_request.get("time_in_force", "day"),
        }

        if submit_kwargs["type"] == "limit" and order_request.get("limit_price") is not None:
            submit_kwargs["limit_price"] = order_request.get("limit_price")

        # Bracket orders no soportados para crypto en Alpaca.
        # SL/TP se omiten intencionalmente; el cierre lo gestiona TradingView via alertas sell.

        order = self.live_api.submit_order(**submit_kwargs)

        # Estandarizar salida para que OrderRouter/BotRegistry mantengan el mismo contrato
        return {
            "id": getattr(order, "id", None),
            "client_order_id": getattr(order, "client_order_id", None),
            "symbol": getattr(order, "symbol", order_request.get("symbol")),
            "side": getattr(order, "side", order_request.get("side")),
            "qty": str(getattr(order, "qty", order_request.get("qty"))),
            "filled_qty": str(getattr(order, "filled_qty", 0)),
            "filled_avg_price": str(getattr(order, "filled_avg_price", 0) or 0),
            "status": getattr(order, "status", "accepted"),
            "created_at": str(getattr(order, "created_at", datetime.now().isoformat())),
            "filled_at": str(getattr(order, "filled_at", "")),
            "mode": "live",
        }
    
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

    def close_position(self, symbol: str) -> Dict:
        """
        cierra una posición abierta por símbolo.
        """
        if self.dry_run:
            simulated_response = {
                "id": f"dry_close_{random.randint(100000, 999999)}",
                "symbol": symbol,
                "status": "closed",
                "mode": "dry_run",
                "closed_at": datetime.now().isoformat(),
            }
            if self.logger:
                self.logger.log_order(
                    {"symbol": symbol, "action": "close_position"},
                    simulated_response,
                )
            return simulated_response

        if not self.live_api:
            raise RuntimeError("live_api no inicializada")

        closed = self.live_api.close_position(symbol)
        return {
            "id": getattr(closed, "id", None),
            "symbol": symbol,
            "status": "closed",
            "mode": "live",
            "closed_at": datetime.now().isoformat(),
            "raw": getattr(closed, "_raw", {}),
        }
    
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

        if not self.live_api:
            raise RuntimeError("live_api no inicializada")

        open_orders = self.live_api.list_orders(status="open")
        cancelled = []
        for order in open_orders:
            self.live_api.cancel_order(order.id)
            cancelled.append(order.id)

        return {
            "status": "cancelled",
            "cancelled_orders": cancelled,
            "bot_id": bot_id,
            "timestamp": datetime.now().isoformat(),
        }
    
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

        if not self.live_api:
            raise RuntimeError("live_api no inicializada")

        positions = self.live_api.list_positions()
        return {
            "status": "live",
            "positions": [p._raw for p in positions],
            "timestamp": datetime.now().isoformat(),
        }
    
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

        if not self.live_api:
            raise RuntimeError("live_api no inicializada")

        account = self.live_api.get_account()
        return {
            "status": "live",
            "account_number": getattr(account, "account_number", None),
            "cash": float(getattr(account, "cash", 0) or 0),
            "portfolio_value": float(getattr(account, "portfolio_value", 0) or 0),
            "buying_power": float(getattr(account, "buying_power", 0) or 0),
            "timestamp": datetime.now().isoformat(),
        }
    
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