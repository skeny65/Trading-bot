import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RegretResult:
    decision_id: str
    strategy_id: str
    decision_date: str
    verdict: str
    was_correct: bool
    opportunity_cost_pct: float
    missed_trades: int
    missed_profit: float
    regime_at_decision: str
    days_evaluated: int

class RegretCalculator:
    """
    Calcula cuánto se perdió (o se evitó perder) por una decisión de PAUSE o HOLD.
    """
    
    def __init__(self, evaluation_window: int = 14):
        self.evaluation_window = evaluation_window
    
    def calculate_regret(
        self,
        strategy_id: str,
        pause_date: str,
        prices_during_pause: List[float],
        trades_during_pause: List[Dict],
        regime_at_pause: str
    ) -> RegretResult:
        """
        Evalúa si una pausa fue correcta o generó arrepentimiento.
        """
        if not prices_during_pause or len(prices_during_pause) < 2:
            return self._empty_result(strategy_id, pause_date, "PAUSE", regime_at_pause)
        
        # Calcular retorno del activo durante la ventana de pausa
        start_price = prices_during_pause[0]
        end_price = prices_during_pause[-1]
        market_return = (end_price - start_price) / start_price
        
        # Simular ganancia/pérdida que hubiera tenido la estrategia
        missed_profit = 0.0
        missed_trades = 0
        
        for trade in trades_during_pause:
            if trade.get("side") == "buy":
                entry = trade.get("entry_price", 0)
                exit_p = trade.get("exit_price", entry)
                if entry > 0:
                    profit = (exit_p - entry) / entry * 100
                    missed_profit += profit
                    missed_trades += 1
        
        # La pausa fue correcta si evitamos pérdidas significativas o el mercado cayó
        was_correct = missed_profit <= 0 or market_return < -0.05
        
        # Oportunidad costo: Profit perdido menos el benchmark del mercado
        opportunity_cost = missed_profit - (market_return * 100)
        
        return RegretResult(
            decision_id=f"{strategy_id}_{pause_date}",
            strategy_id=strategy_id,
            decision_date=pause_date,
            verdict="PAUSE",
            was_correct=was_correct,
            opportunity_cost_pct=round(opportunity_cost, 2),
            missed_trades=missed_trades,
            missed_profit=round(missed_profit, 2),
            regime_at_decision=regime_at_pause,
            days_evaluated=len(prices_during_pause)
        )

    def calculate_hold_regret(
        self,
        strategy_id: str,
        hold_date: str,
        actual_profit: float,
        regime_at_hold: str
    ) -> RegretResult:
        """Evalúa si mantener activo el bot (HOLD) fue correcto."""
        was_correct = actual_profit >= 0
        return RegretResult(
            decision_id=f"{strategy_id}_{hold_date}",
            strategy_id=strategy_id,
            decision_date=hold_date,
            verdict="HOLD",
            was_correct=was_correct,
            opportunity_cost_pct=0.0 if was_correct else round(abs(actual_profit), 2),
            missed_trades=0,
            missed_profit=round(actual_profit, 2),
            regime_at_decision=regime_at_hold,
            days_evaluated=0
        )

    def _empty_result(self, s_id, date, verdict, regime):
        return RegretResult(
            f"{s_id}_{date}", s_id, date, verdict, True, 0.0, 0, 0.0, regime, 0
        )