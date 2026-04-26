# test_learning_engine.py

import numpy as np
import pandas as pd
from learning_engine import RegimeDetector

# Generar datos sintéticos para test
np.random.seed(42)
n_days = 252

# Simular precios con diferentes regímenes
trend = np.cumsum(np.random.randn(n_days) * 0.01 + 0.001)
prices = pd.Series(100 * np.exp(trend))

# Test
detector = RegimeDetector(n_regimes=3)  # 3 regímenes para test simple
detector.fit(prices)

regime_id, regime_name, probs = detector.predict_regime(prices)

print(f"Regimen: {regime_name}")
print(f"Probs: {probs}")
print(f"Matrix:\n{detector.get_transition_matrix()}")