import json
import os

def load_thresholds():
    """
    Carga umbrales calibrados del backtest, o usa defaults conservadores.
    """
    calibrated_path = "bot-manager/backtest/results/recommended_config.json"
    
    if os.path.exists(calibrated_path):
        with open(calibrated_path, 'r') as f:
            config = json.load(f)
            return config['thresholds']
    
    return {
        'wr_pause': 45,
        'dd_pause': -20,
        'pf_pause': 1.05,
        'consec_pause': 6,
        'wr_reactivate': 52,
        'dd_reactivate': -15,
        'pf_reactivate': 1.2
    }

THRESHOLDS = load_thresholds()
USE_LEARNING_OVERRIDE = True
USE_MARKOV_REGIMES = True