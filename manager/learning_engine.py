import numpy as np
import pandas as pd
from hmmlearn import hmm
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from core.alpaca_data_source import AlpacaDataSource

class RegimeDetector:
    """
    Detects market regimes using Hidden Markov Model.
    """
    def __init__(self, n_regimes: int = 5):
        self.n_regimes = n_regimes
        self.model = None
        self.regime_names = {
            0: "bull_trend", 1: "bear_trend", 2: "mean_reverting",
            3: "high_volatility", 4: "low_volatility"
        }
        self.is_fitted = False
        
    def _calculate_features(self, prices: pd.Series, volume: pd.Series = None) -> np.ndarray:
        returns = np.log(prices / prices.shift(1)).dropna()
        volatility = returns.rolling(window=20).std().dropna()
        price_range = returns.abs().rolling(window=10).mean().dropna()
        momentum = (prices / prices.shift(10) - 1).dropna()
        
        feat_list = [returns, volatility, price_range, momentum]
        min_len = min(len(f) for f in feat_list)
        features = np.column_stack([f.iloc[-min_len:].values for f in feat_list])
        return features
    
    def fit(self, prices: pd.Series, volume: pd.Series = None):
        features = self._calculate_features(prices, volume)
        self.model = hmm.GaussianHMM(n_components=self.n_regimes, n_iter=100, random_state=42)
        self.model.fit(features)
        self.is_fitted = True
        return self
    
    def predict_regime(self, prices: pd.Series, volume: pd.Series = None) -> Tuple[int, str, np.ndarray]:
        if not self.is_fitted: raise ValueError("Model not fitted.")
        features = self._calculate_features(prices, volume)
        regime_id = self.model.predict(features)[-1]
        regime_name = self.regime_names.get(regime_id, f"regime_{regime_id}")
        probs = self.model.predict_proba(features)[-1]
        return regime_id, regime_name, probs

class LearningState:
    def __init__(self, filepath: str = "data/learning_state.json"):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self) -> Dict:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        try:
            with open(self.filepath, 'r') as f: return json.load(f)
        except:
            return {"regime_history": [], "last_updated": datetime.now().isoformat()}
    
    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, 'w') as f: json.dump(self.data, f, indent=2)

    def add_record(self, name: str, probs: list):
        self.data["regime_history"].append({"regime": name, "probabilities": probs, "timestamp": datetime.now().isoformat()})
        self.save()

class LearningEngine:
    def __init__(self):
        self.detector = RegimeDetector()
        self.state = LearningState()
        self.data_source = AlpacaDataSource()

    def detect_regime(self) -> str:
        try:
            bars = self.data_source.get_bars("SPY", "1Day", limit=300)
            if bars is None or bars.empty: return "UNKNOWN"
            prices = bars['close']
            self.detector.fit(prices)
            _, regime_name, probs = self.detector.predict_regime(prices)
            self.state.add_record(regime_name, probs.tolist())
            return regime_name.upper()
        except Exception as e:
            print(f"Error in LearningEngine: {e}")
            return "VOLATILE"

    def get_adaptation_score(self, strategy_id: str) -> float:
        history = self.state.data.get("regime_history", [])
        if len(history) < 5: return 50.0
        return 75.0 # Simplificado para el ejemplo