import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from itertools import product

class ThresholdOptimizer:
    """
    Busca la combinación óptima de umbrales usando grid search.
    """
    def __init__(self, backtest_engine):
        self.engine = backtest_engine
        self.best_config = None
        self.best_score = -999999

    def optimize(self, strategy_id: str, price_data, trade_signals, regime_data, parameter_grid: Dict = None) -> Tuple[Dict, float]:
        if parameter_grid is None:
            parameter_grid = {
                'wr_pause': [42, 45, 47],
                'dd_pause': [-22, -20, -18],
                'pf_pause': [1.05, 1.1],
                'wr_reactivate': [52, 55],
                'dd_reactivate': [-15, -12]
            }
        
        keys, values = list(parameter_grid.keys()), list(parameter_grid.values())
        combinations = list(product(*values))
        results = []

        for combo in combinations:
            thresholds = dict(zip(keys, combo))
            result = self.engine.run_backtest(strategy_id, price_data, trade_signals, regime_data, thresholds)
            score = self._calculate_score(result)
            
            if score > self.best_score:
                self.best_score = score
                self.best_config = thresholds.copy()

        self._save_results(results)
        return self.best_config, self.best_score

    def _calculate_score(self, result) -> float:
        return result.total_return_pct - (abs(result.max_drawdown_pct) * 2) - (result.num_pauses * 2)

    def _save_results(self, results):
        path = "bot-manager/backtest/results/threshold_optimization.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump({'best_thresholds': self.best_config, 'best_score': self.best_score}, f, indent=2)