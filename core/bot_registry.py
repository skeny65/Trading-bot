import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class BotRegistry:
    """
    Gestiona el estado persistente de los bots (ACTIVE/PAUSED/HOLD) y sus métricas.
    Almacena objetos completos por estrategia en lugar de simples strings.
    """

    KNOWN_BOTS = ["strategy_001", "strategy_002", "strategy_003"]

    def __init__(self, storage_path: str = "data/bot_status.json"):
        self.storage_path = storage_path
        self._data: Dict = {}
        self._ensure_storage_exists()
        self._load()

    # ------------------------------------------------------------------ #
    #  Persistencia                                                        #
    # ------------------------------------------------------------------ #

    def _ensure_storage_exists(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            initial = {sid: self._default_entry(sid) for sid in self.KNOWN_BOTS}
            with open(self.storage_path, 'w') as f:
                json.dump(initial, f, indent=4)

    def _default_entry(self, strategy_id: str) -> Dict:
        return {
            "strategy_id": strategy_id,
            "status": "ACTIVE",
            "reason": "",
            "metrics": {},
            "last_trade": None,
            "updated_at": datetime.now().isoformat(),
        }

    def _load(self):
        try:
            with open(self.storage_path, 'r') as f:
                raw = json.load(f)
            # Migrate flat format {sid: "STATUS"} → full object
            migrated: Dict = {}
            for sid, value in raw.items():
                if isinstance(value, str):
                    entry = self._default_entry(sid)
                    entry["status"] = value.upper()
                    migrated[sid] = entry
                else:
                    migrated[sid] = value
            self._data = migrated
        except Exception:
            self._data = {sid: self._default_entry(sid) for sid in self.KNOWN_BOTS}

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self._data, f, indent=4, default=str)

    def _get_entry(self, strategy_id: str) -> Dict:
        if strategy_id not in self._data:
            self._data[strategy_id] = self._default_entry(strategy_id)
        return self._data[strategy_id]

    # ------------------------------------------------------------------ #
    #  API pública                                                         #
    # ------------------------------------------------------------------ #

    def get_status(self, strategy_id: str) -> str:
        return self._get_entry(strategy_id).get("status", "ACTIVE")

    def set_status(self, strategy_id: str, status: str, reason: str = ""):
        entry = self._get_entry(strategy_id)
        entry["status"] = status.upper()
        entry["reason"] = reason
        entry["updated_at"] = datetime.now().isoformat()
        self._save()

    def is_paused(self, strategy_id: str) -> bool:
        return self.get_status(strategy_id).upper() == "PAUSED"

    def update_metrics(self, strategy_id: str, metrics: Dict):
        entry = self._get_entry(strategy_id)
        entry["metrics"] = metrics
        entry["updated_at"] = datetime.now().isoformat()
        self._save()

    def record_trade(self, strategy_id: str, order_result: Dict):
        entry = self._get_entry(strategy_id)
        entry["last_trade"] = {
            "order_id": order_result.get("id"),
            "symbol": order_result.get("symbol"),
            "side": order_result.get("side"),
            "qty": order_result.get("qty"),
            "filled_avg_price": order_result.get("filled_avg_price"),
            "status": order_result.get("status"),
            "recorded_at": datetime.now().isoformat(),
        }
        self._save()

    def list_bots(self) -> List[Dict]:
        return list(self._data.values())

    def get_bot_id(self, strategy_id: str) -> str:
        return f"bot_{strategy_id}"

    def get_summary(self) -> Dict:
        bots = self.list_bots()
        return {
            "total": len(bots),
            "active": sum(1 for b in bots if b.get("status", "").upper() == "ACTIVE"),
            "paused": sum(1 for b in bots if b.get("status", "").upper() == "PAUSED"),
            "hold": sum(1 for b in bots if b.get("status", "").upper() == "HOLD"),
            "bots": [
                {"strategy_id": b["strategy_id"], "status": b.get("status")}
                for b in bots
            ],
        }