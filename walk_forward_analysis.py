import pandas as pd
import numpy as np
from typing import Dict

class WalkForwardAnalysis:
    """
    Valida que los umbrales no estén sobreajustados dividiendo datos en ventanas.
    """
    def __init__(self, train_size: int = 180, test_size: int = 60):
        self.train_size = train_size
        self.test_size = test_size

    def run(self, price_data, trade_signals, regime_data, optimizer, engine) -> Dict:
        total_days = len(price_data)
        results = []
        start = 0

        while start + self.train_size + self.test_size <= total_days:
            train_price = price_data.iloc[start : start + self.train_size]
            test_price = price_data.iloc[start + self.train_size : start + self.train_size + self.test_size]
            
            # Optimize on training set
            best_t, _ = optimizer.optimize("wf_train", train_price, trade_signals, regime_data)
            
            # Validate on test set
            res = engine.run_backtest("wf_test", test_price, trade_signals, regime_data, best_t)
            results.append(res.total_return_pct)
            start += self.test_size

        consistency = {
            'avg_return': np.mean(results),
            'std_return': np.std(results),
            'is_robust': np.mean(results) > 0 and np.std(results) < 15
        }
        return consistency