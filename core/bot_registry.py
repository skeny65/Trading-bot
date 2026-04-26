import json
import os
from datetime import datetime
from utils.state_validator import StateValidator

class BotRegistry:
    """
    Handles persistence of bot status and mapping.
    """
    def __init__(self, storage_path="data/bot_status.json"):
        self.storage_path = storage_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w') as f:
                json.dump({}, f)

    def get_status(self, strategy_id: str) -> str:
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
        return data.get(strategy_id, "ACTIVE")  # Default to ACTIVE

    def set_status(self, strategy_id: str, status: str):
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
        
        data[strategy_id] = status
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=4)

    def get_bot_id(self, strategy_id: str) -> str:
        # Placeholder mapping logic
        return f"bot_{strategy_id}"