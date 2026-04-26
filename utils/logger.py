import logging
import os

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    configura logger con formato consistente.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers: return logger
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger