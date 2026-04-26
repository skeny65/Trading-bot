import json
import os
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Iterator
from pathlib import Path


class TradeLogger:
    """
    logger de trades en formato json lines (jsonl).
    append-only para alta performance, un archivo por día.
    """
    
    def __init__(self, base_dir: str = "data/trades"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        (self.base_dir / "archive").mkdir(exist_ok=True)
        
        self.current_file = None
        self.current_date = None
    
    def _get_file_for_date(self, target_date: date = None) -> Path:
        """
        obtiene o crea archivo para una fecha específica.
        """
        if target_date is None:
            target_date = date.today()
        
        if self.current_date != target_date and self.current_file:
            self.current_file.close()
            self.current_file = None
        
        self.current_date = target_date
        filename = target_date.strftime("%Y-%m-%d") + ".jsonl"
        filepath = self.base_dir / filename
        
        if self.current_file is None or self.current_file.closed:
            self.current_file = open(filepath, 'a', encoding='utf-8')
        
        return filepath
    
    def log_trade(self, trade: Dict) -> str:
        """
        registra un trade. operación atómica de append.
        """
        trade_id = self._generate_trade_id(trade)
        
        enriched_trade = {
            "_id": trade_id,
            "_logged_at": datetime.now().isoformat(),
            "_date": date.today().isoformat(),
            **trade
        }
        
        self._get_file_for_date()
        self.current_file.write(json.dumps(enriched_trade, default=str) + "\n")
        self.current_file.flush()
        
        return trade_id
    
    def log_signal_rejected(self, signal: Dict, reason: str):
        """registra señal rechazada para hindsight."""
        record = {
            "_id": self._generate_trade_id(signal),
            "_logged_at": datetime.now().isoformat(),
            "_date": date.today().isoformat(),
            "_type": "signal_rejected",
            "reason": reason,
            "signal": signal
        }
        self._get_file_for_date()
        self.current_file.write(json.dumps(record, default=str) + "\n")
        self.current_file.flush()
    
    def _generate_trade_id(self, data: Dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        content = json.dumps(data, sort_keys=True, default=str)
        short_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{timestamp}_{short_hash}"
    
    def get_trades_for_date(self, target_date: date = None) -> List[Dict]:
        if target_date is None:
            target_date = date.today()
        
        filename = target_date.strftime("%Y-%m-%d") + ".jsonl"
        filepath = self.base_dir / filename
        
        if not filepath.exists():
            return []
        
        trades = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get("_type") not in ["signal_rejected", "decision"]:
                        trades.append(record)
                except json.JSONDecodeError:
                    continue
        return trades
    
    def get_trades_for_range(self, start_date: date, end_date: date) -> Iterator[Dict]:
        current = start_date
        while current <= end_date:
            for trade in self.get_trades_for_date(current):
                yield trade
            current += timedelta(days=1)
    
    def get_trades_for_strategy(self, strategy_id: str, days: int = 30) -> List[Dict]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        trades = []
        for trade in self.get_trades_for_range(start_date, end_date):
            if trade.get("strategy_id") == strategy_id or trade.get("bot_id") == strategy_id:
                trades.append(trade)
        return trades

    def get_daily_summary(self, target_date: date = None) -> Dict:
        if target_date is None: target_date = date.today()
        trades = self.get_trades_for_date(target_date)
        if not trades: return {"total_trades": 0, "total_pnl": 0.0}
        
        pnls = [t.get("pnl", 0) or t.get("profit", 0) or 0 for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        return {
            "date": target_date.isoformat(),
            "total_trades": len(trades),
            "win_rate": round(wins / len(trades) * 100, 1) if trades else 0,
            "total_pnl": round(sum(pnls), 2)
        }
    
    def close(self):
        if self.current_file and not self.current_file.closed:
            self.current_file.close()
            self.current_file = None