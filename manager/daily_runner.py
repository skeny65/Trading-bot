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
        self.hindsight = HindsightEngine(records_path=hindsight_path)
        self.notifier = notifier

    def collect_data(self) -> Dict:
        """Simula recolección de métricas reales para cada bot."""
        metrics_by_bot = {}
        for bot in self.registry.list_bots():
            sid = bot["strategy_id"]
            metrics = {"win_rate": np.random.uniform(40, 60), "drawdown": np.random.uniform(-25, -5)}
            metrics_by_bot[sid] = metrics
            self.registry.update_metrics(sid, metrics)
        return metrics_by_bot

    def detect_regime(self) -> str:
        return self.learning_engine.detect_regime()

    def evaluate_all_bots(self) -> List[Dict]:
        decisions = []
        regime = self.detect_regime()
        for bot in self.registry.list_bots():
            sid = bot["strategy_id"]
            metrics = bot.get("metrics", {})
            verdict = self.decision_engine.get_verdict(sid, metrics, regime, hindsight=self.hindsight)
            decisions.append({"strategy_id": sid, "verdict": verdict, "regime": regime})
        return decisions

    def execute_decisions(self, decisions: List[Dict]):
        for d in decisions:
            self.registry.set_status(d["strategy_id"], d["verdict"])

    def save_report(self) -> str:
        path = f"data/reports/{datetime.now().strftime('%Y-%m-%d')}.json"
        # Lógica de guardado simplificada
        return path