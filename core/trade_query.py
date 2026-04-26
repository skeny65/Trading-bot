import json
import statistics
from datetime import date, timedelta
from typing import Dict, List, Optional
from core.trade_logger import TradeLogger


class TradeQuery:
    """
    consultas analíticas sobre trades históricos.
    usado por hindsight engine y dashboard.
    """
    
    def __init__(self, trade_logger: TradeLogger = None):
        self.logger = trade_logger or TradeLogger()
    
    def get_equity_curve(self, strategy_id: str, days: int = 90) -> List[Dict]:
        trades = self.logger.get_trades_for_strategy(strategy_id, days)
        if not trades: return []
        
        trades_sorted = sorted(trades, key=lambda t: t.get("timestamp", t.get("_logged_at", "")))
        equity = 10000
        curve = []
        
        for trade in trades_sorted:
            pnl = trade.get("pnl", 0) or trade.get("profit", 0) or 0
            equity += pnl
            curve.append({
                "timestamp": trade.get("timestamp", trade.get("_logged_at")),
                "equity": round(equity, 2),
                "trade_pnl": round(pnl, 2)
            })
        return curve
    
    def get_performance_metrics(self, strategy_id: str, days: int = 30) -> Dict:
        trades = self.logger.get_trades_for_strategy(strategy_id, days)
        if not trades: return {"win_rate": 0, "profit_factor": 0, "total_trades": 0}
        
        pnls = [t.get("pnl", 0) or t.get("profit", 0) or 0 for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        equity, peak, max_dd = 10000, 10000, 0
        for pnl in pnls:
            equity += pnl
            if equity > peak: peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd: max_dd = dd
            
        return {
            "win_rate": round(len(wins) / len(pnls) * 100, 1),
            "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else 999,
            "max_drawdown": round(max_dd, 2),
            "total_trades": len(trades),
            "total_pnl": round(sum(pnls), 2)
        }
    
    def get_trades_during_pause(self, strategy_id: str, pause_date: date, resume_date: date) -> List[Dict]:
        trades = []
        for trade in self.logger.get_trades_for_range(pause_date, resume_date):
            if trade.get("strategy_id") == strategy_id or trade.get("bot_id") == strategy_id:
                trades.append(trade)
        return trades