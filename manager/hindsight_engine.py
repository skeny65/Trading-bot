import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from core.alpaca_data_source import AlpacaDataSource
from core.regret_calculator import RegretCalculator, RegretResult
from core.trade_query import TradeQuery

class HindsightEngine:
    """
    Analiza decisiones pasadas para calcular el arrepentimiento (Regret Rate).
    Compara qué hubiera pasado si no se hubiera pausado una estrategia.
    """
    def __init__(self, history_path: str = "data/decisions_history.json"):
        self.history_path = history_path
        self.data_source = AlpacaDataSource()
        self.calculator = RegretCalculator()
        self.trade_query = TradeQuery()
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        if not os.path.exists(self.history_path):
            with open(self.history_path, 'w') as f:
                json.dump([], f)

    def record_decision(self, strategy_id: str, verdict: str, symbol: str, price: float, regime: str):
        """Registra una decisión con el precio actual del activo y el régimen detectado."""
        with open(self.history_path, 'r') as f:
            history = json.load(f)
        
        history.append({
            "timestamp": datetime.now().isoformat(),
            "strategy_id": strategy_id,
            "symbol": symbol,
            "verdict": verdict,
            "price_at_decision": price,
            "regime_at_decision": regime,
            "status": "open" if verdict == "PAUSE" else "closed"
        })
        
        with open(self.history_path, 'w') as f:
            json.dump(history[-500:], f, indent=4)  # Mantener los últimos 500 registros

    def calculate_regret(self, strategy_id: str, current_price: float) -> RegretResult:
        """
        Evalúa si la última decisión fue correcta basándose en el movimiento del precio.
        """
        with open(self.history_path, 'r') as f:
            history = json.load(f)
        
        # Buscar la última decisión para este bot para evaluarla
        last_decision = next((d for d in reversed(history) if d["strategy_id"] == strategy_id), None)
        
        if not last_decision:
            return RegretResult(
                decision_id="none", strategy_id=strategy_id, symbol="N/A",
                decision_date=datetime.now().isoformat(), verdict="NONE",
                was_correct=True, opportunity_cost_pct=0.0,
                regime_at_decision="N/A", days_evaluated=0
            )

        price_then = last_decision["price_at_decision"]
        verdict = last_decision["verdict"]
        regime = last_decision.get("regime_at_decision", "N/A")
        market_return_pct = (current_price - price_then) / price_then * 100

        if verdict == "PAUSE":
            # Usamos el calculador para evaluar la pausa
            # Para una evaluación simple, pasamos los precios extremos
            return self.calculator.calculate_regret(
                strategy_id, last_decision["timestamp"], [price_then, current_price], [], regime
            )

        # Evaluación por defecto para HOLD/REACTIVATE
        was_correct = market_return_pct >= 0 if verdict != "PAUSE" else market_return_pct <= 0
        opportunity_cost = abs(market_return_pct) if not was_correct else 0.0

        return RegretResult(
            decision_id=f"{strategy_id}_{last_decision['timestamp']}",
            strategy_id=strategy_id,
            decision_date=last_decision["timestamp"],
            verdict=verdict,
            was_correct=was_correct,
            opportunity_cost_pct=round(opportunity_cost, 2),
            regime_at_decision=regime,
            days_evaluated=0,
            missed_trades=0,
            missed_profit=0.0
        )

    def get_adaptation_score(self, strategy_id: str) -> float:
        """
        Calcula un score de 0 a 100. 
        Scores bajos indican que las pausas han sido útiles (salvaron dinero).
        Scores altos indican que las pausas han sido erróneas (perdimos oportunidades).
        """
        with open(self.history_path, 'r') as f:
            history = json.load(f)
        
        strategy_history = [d for d in history if d["strategy_id"] == strategy_id]
        if not strategy_history:
            return 50.0 # Score neutral
            
        # Lógica simplificada: si el arrepentimiento promedio es positivo, el score sube.
        # Esto se integraría con el Learning Engine en el futuro.
        return 50.0 # Placeholder para lógica compleja de arrepentimiento acumulado