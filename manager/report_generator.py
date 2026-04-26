import json
import os
from datetime import datetime
from typing import Dict, List


class ReportGenerator:
    """
    centraliza la generación de reportes json con datos reales del sistema.
    """
    
    def __init__(self, reports_dir: str = "data/reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    def generate(
        self,
        date: str,
        bots_data: List[Dict],
        regime_data: Dict,
        decisions: List[Dict],
        hindsight_summary: Dict,
        execution_mode: str = "dry_run"
    ) -> str:
        """
        genera reporte completo con todos los datos del análisis diario.
        """
        report = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "date": date,
                "version": "1.0",
                "execution_mode": execution_mode
            },
            "summary": {
                "total_bots": len(bots_data),
                "active": sum(1 for b in bots_data if b.get("status") == "active"),
                "paused": sum(1 for b in bots_data if b.get("status") == "paused"),
                "hold": sum(1 for b in bots_data if b.get("status") == "hold")
            },
            "market_regime": regime_data,
            "bots": self._format_bots(bots_data),
            "decisions": decisions,
            "hindsight": hindsight_summary,
            "alerts": self._generate_alerts(bots_data, decisions)
        }
        
        filepath = os.path.join(self.reports_dir, f"{date}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        # también guardar como latest.json
        latest_path = os.path.join(self.reports_dir, "latest.json")
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filepath
    
    def _format_bots(self, bots_data: List[Dict]) -> Dict:
        formatted = {}
        for bot in bots_data:
            bot_id = bot.get("strategy_id", "unknown")
            formatted[bot_id] = {
                "strategy_id": bot_id,
                "symbol": bot.get("symbol", "unknown"),
                "status": bot.get("status", "unknown"),
                "registered_at": bot.get("registered_at"),
                "last_status_change": bot.get("last_status_change"),
                "metrics": bot.get("metrics", {}),
                "recent_trades": bot.get("trades", [])[-5:],
                "last_decision": bot.get("last_decision")
            }
        return formatted
    
    def _generate_alerts(self, bots_data: List[Dict], decisions: List[Dict]) -> List[Dict]:
        alerts = []
        for bot in bots_data:
            metrics = bot.get("metrics", {})
            dd = metrics.get("drawdown", 0)
            if dd < -25:
                alerts.append({
                    "level": "critical", "type": "drawdown", "bot_id": bot.get("strategy_id"),
                    "message": f"drawdown crítico: {dd:.1f}%", "timestamp": datetime.now().isoformat()
                })
            elif dd < -20:
                alerts.append({
                    "level": "warning", "type": "drawdown", "bot_id": bot.get("strategy_id"),
                    "message": f"drawdown alto: {dd:.1f}%", "timestamp": datetime.now().isoformat()
                })
        
        for decision in decisions:
            if decision.get("verdict") == "pause":
                alerts.append({
                    "level": "info", "type": "decision", "bot_id": decision.get("strategy_id"),
                    "message": f"bot pausado: {decision.get('reason', '')}", "timestamp": decision.get("timestamp")
                })
            elif decision.get("verdict") == "reactivate":
                alerts.append({
                    "level": "info", "type": "decision", "bot_id": decision.get("strategy_id"),
                    "message": "bot reactivado", "timestamp": decision.get("timestamp")
                })
        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)[:10]