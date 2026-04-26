import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    configura logger con formato consistente.
    soporta rotación automática para bot.log y telegram.log.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers: return logger
    
    import sys
    # Forzar UTF-8 en Windows para soportar emojis en consola
    stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1) if sys.platform == 'win32' else sys.stdout
    console = logging.StreamHandler(stream)
    console.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(console)
    
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Configuración específica por archivo según el plan
        if "bot.log" in log_file:
            max_bytes = 10_000_000 # 10 MB
            backup_count = 7
            fmt = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        else:
            max_bytes = 5_000_000 # 5 MB
            backup_count = 5
            fmt = '%(asctime)s | %(message)s'
        
        formatter = logging.Formatter(fmt)
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger