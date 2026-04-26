import gzip
import os
import shutil
from datetime import datetime, date
from pathlib import Path


class FileRotation:
    """
    rota y comprime archivos de logs antiguos.
    """
    
    def __init__(
        self,
        base_dir: str = "data/trades",
        archive_dir: str = "data/trades/archive",
        max_days: int = 30,
        compress_after_days: int = 7
    ):
        self.base_dir = Path(base_dir)
        self.archive_dir = Path(archive_dir)
        self.max_days = max_days
        self.compress_after_days = compress_after_days
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def rotate(self):
        """comprime antiguos, elimina muy antiguos."""
        today = date.today()
        for filepath in sorted(self.base_dir.glob("*.jsonl")):
            try:
                file_date = datetime.strptime(filepath.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            
            days_old = (today - file_date).days
            
            if days_old > self.max_days:
                filepath.unlink()
                print(f"Eliminado por antigüedad: {filepath.name}")
            elif days_old > self.compress_after_days:
                self._compress_file(filepath)
    
    def _compress_file(self, filepath: Path):
        archive_path = self.archive_dir / (filepath.name + ".gz")
        with open(filepath, 'rb') as f_in:
            with gzip.open(archive_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        filepath.unlink()
        print(f"Comprimido: {filepath.name}")