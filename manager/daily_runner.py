import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from core.bot_registry import BotRegistry
from manager.learning_engine import LearningEngine
from manager.decision_engine import DecisionEngine
from manager.hindsight_engine import HindsightEngine

class DailyRunner:
    def __init__(self, bot_registry: BotRegistry, learning_state_path: str, hindsight_path: str, notifier=None):
        self.registry = bot_registry
        self.learning_engine = LearningEngine()
        self.decision_engine = DecisionEngine()
        # Fix: pass history_path (not records_path) to match constructor
        self.hindsight = HindsightEngine(history_path=hindsight_path)
        self.notifier = notifier
        self._last_decisions: List[Dict] = []
        self._last_regime: str = "UNKNOWN"

    def collect_data(self) -> Dict:
        """Recolecta métricas reales o simuladas para cada bot."""
        metrics_by_bot = {}
        for bot in self.registry.list_bots():
            sid = bot["strategy_id"]
            metrics = {
                "win_rate": np.random.uniform(40, 60),
                "drawdown": np.random.uniform(-25, -5),
            }
            metrics_by_bot[sid] = metrics
            self.registry.update_metrics(sid, metrics)
        return metrics_by_bot

    def detect_regime(self) -> str:
        self._last_regime = self.learning_engine.detect_regime()
        return self._last_regime

    def evaluate_all_bots(self) -> List[Dict]:
        decisions = []
        regime = self.detect_regime()
        for bot in self.registry.list_bots():
            sid = bot["strategy_id"]
            metrics = bot.get("metrics", {})
            verdict = self.decision_engine.get_verdict(
                sid, metrics, regime, hindsight=self.hindsight
            )
            decisions.append({
                "strategy_id": sid,
                "verdict": verdict,
                "regime": regime,
                "metrics": metrics,
            })
        self._last_decisions = decisions
        return decisions

    def execute_decisions(self, decisions: List[Dict]):
        for d in decisions:
            sid = d["strategy_id"]
            verdict = d["verdict"]
            reason = f"verdict={verdict}, regime={d.get('regime', 'UNKNOWN')}"
            # set_status now accepts optional reason arg
            self.registry.set_status(sid, verdict, reason)

    def save_report(self) -> str:
        today = datetime.now().strftime('%Y-%m-%d')
        path = f"data/reports/{today}.json"
        os.makedirs("data/reports", exist_ok=True)

        report = {
            "date": today,
            "generated_at": datetime.now().isoformat(),
            "regime": self._last_regime,
            "decisions": self._last_decisions,
            "bots": self.registry.list_bots(),
            "hindsight_summary": self.hindsight.get_summary(),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        # también guardar como latest.json
        latest = "data/reports/latest.json"
        with open(latest, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        return path

    def get_summary(self) -> Dict:
        """Resumen del análisis diario para notificaciones y dashboard."""
        return {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "regime": self._last_regime,
            "registry": self.registry.get_summary(),
            "decisions": self._last_decisions,
            "hindsight": self.hindsight.get_summary(),
        }