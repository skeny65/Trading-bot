import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class StateValidator:
    """
    valida integridad de archivos de estado y repara si es posible.
    """
    def __init__(self, backup_dir: str = "data/backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def validate_bot_registry(self, filepath: str) -> Tuple[bool, str]:
        if not os.path.exists(filepath):
            return False, "archivo no existe"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return False, "formato incorrecto"
            return True, "válido"
        except Exception as e:
            return False, str(e)

    def create_backup(self, filepath: str):
        if not os.path.exists(filepath):
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_name = f"{filename.replace('.json', '')}_{timestamp}.json"
        shutil.copy2(filepath, os.path.join(self.backup_dir, backup_name))
        
        # Mantener solo 10
        backups = sorted([f for f in os.listdir(self.backup_dir) if filename.replace('.json', '') in f])
        for old in backups[:-10]:
            os.remove(os.path.join(self.backup_dir, old))

    def repair_bot_registry(self, filepath: str) -> bool:
        backups = sorted([f for f in os.listdir(self.backup_dir) if "bot_status" in f], reverse=True)
        for b in backups:
            path = os.path.join(self.backup_dir, b)
            valid, _ = self.validate_bot_registry(path)
            if valid:
                shutil.copy2(path, filepath)
                return True
        return False

    def validate_all(self) -> Dict[str, Tuple[bool, str]]:
        return {
            "bot_registry": self.validate_bot_registry("data/bot_status.json")
        }