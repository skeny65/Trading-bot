import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BacktestResult:
    strategy_id: str
    start_date: str
    end_date: str
    total_days: int
    initial_equity: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    num_trades: int
    num_pauses: int
    num_reactivations: int
    num_overrides: int
    avg_regret_rate: float
    regime_transitions_caught: int
    regime_transitions_missed: int


class BacktestEngine:
    """
    Simula el comportamiento del bot manager en datos históricos.
    """
    
    def __init__(
        self,
        initial_equity: float = 10000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005
    ):
        self.initial_equity = initial_equity
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.results: List[BacktestResult] = []
    
    def run_backtest(
        self,
        strategy_id: str,
        price_data: pd.DataFrame,
        trade_signals: pd.DataFrame,
        regime_data: pd.DataFrame,
        thresholds: Dict,
        use_learning_override: bool = True,
        use_markov: bool = True
    ) -> BacktestResult:
        equity = self.initial_equity
        equity_curve = [equity]
        max_equity = equity
        max_drawdown = 0.0
        
        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0
        
        num_trades = 0
        num_pauses = 0
        num_reactivations = 0
        num_overrides = 0
        
        status = "ACTIVE"
        regret_records = []
        
        dates = price_data['date'].tolist()
        
        for i, date in enumerate(dates):
            current_price = price_data.iloc[i]['close']
            signal_row = trade_signals[trade_signals['date'] == date]
            has_signal = len(signal_row) > 0
            
            if len(regime_data[regime_data['date'] == date]) > 0 and use_markov:
                regime_row = regime_data[regime_data['date'] == date]
                current_regime = regime_row.iloc[0]['regime_name']
                regime_probs = {
                    'bull': regime_row.iloc[0].get('prob_bull', 0),
                    'bear': regime_row.iloc[0].get('prob_bear', 0),
                    'volatile': regime_row.iloc[0].get('prob_volatile', 0)
                }
            else:
                current_regime = "unknown"
                regime_probs = {}
            
            if i >= 30:
                window_prices = price_data.iloc[i-30:i]['close']
                window_returns = window_prices.pct_change().dropna()
                
                win_rate = self._calculate_win_rate(window_returns)
                drawdown = self._calculate_drawdown(window_prices, equity_curve[-30:])
                profit_factor = self._calculate_profit_factor(window_returns)
                consec_losses = self._calculate_consecutive_losses(window_returns)
            else:
                win_rate, drawdown, profit_factor, consec_losses = 50.0, -5.0, 1.1, 0
            
            if status == "ACTIVE":
                should_pause = (
                    win_rate < thresholds.get('wr_pause', 45) or
                    drawdown < thresholds.get('dd_pause', -20) or
                    profit_factor < thresholds.get('pf_pause', 1.05) or
                    consec_losses > thresholds.get('consec_pause', 6)
                )
                
                if should_pause:
                    if use_learning_override:
                        adaptation_score = self._simulate_adaptation_score(current_regime, regime_probs, win_rate, drawdown)
                        regret_rate = self._simulate_regret_rate(strategy_id, current_regime)
                        
                        if adaptation_score >= 70 and regret_rate > 40:
                            num_overrides += 1
                            status = "HOLD"
                        else:
                            status = "PAUSED"
                            num_pauses += 1
                    else:
                        status = "PAUSED"
                        num_pauses += 1
            
            elif status == "PAUSED":
                should_reactivate = (
                    win_rate >= thresholds.get('wr_reactivate', 52) and
                    drawdown > thresholds.get('dd_reactivate', -15) and
                    profit_factor >= thresholds.get('pf_reactivate', 1.2)
                )
                if should_reactivate:
                    status = "ACTIVE"
                    num_reactivations += 1
            
            if has_signal and status != "PAUSED":
                signal = signal_row.iloc[0]
                trade_result = self._simulate_trade(signal, current_price, equity)
                equity += trade_result['pnl']
                num_trades += 1
                
                if trade_result['pnl'] > 0:
                    wins += 1
                    total_profit += trade_result['pnl']
                else:
                    losses += 1
                    total_loss += abs(trade_result['pnl'])
                
                if equity > max_equity: max_equity = equity
                dd = (equity - max_equity) / max_equity * 100
                if dd < max_drawdown: max_drawdown = dd
            
            equity_curve.append(equity)
        
        total_return = (equity - self.initial_equity) / self.initial_equity * 100
        win_rate_final = (wins / num_trades * 100) if num_trades > 0 else 0
        pf_final = (total_profit / total_loss) if total_loss > 0 else 999
        
        result = BacktestResult(
            strategy_id=strategy_id, start_date=str(dates[0]), end_date=str(dates[-1]),
            total_days=len(dates), initial_equity=self.initial_equity, final_equity=equity,
            total_return_pct=round(total_return, 2), max_drawdown_pct=round(max_drawdown, 2),
            win_rate=round(win_rate_final, 2), profit_factor=round(pf_final, 2),
            num_trades=num_trades, num_pauses=num_pauses, num_reactivations=num_reactivations,
            num_overrides=num_overrides, avg_regret_rate=round(np.mean(regret_records) if regret_records else 0, 2),
            regime_transitions_caught=0, regime_transitions_missed=0
        )
        self.results.append(result)
        return result

    def _calculate_win_rate(self, returns: pd.Series) -> float:
        return (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 50.0

    def _calculate_drawdown(self, prices: pd.Series, equity_window: List[float]) -> float:
        if not equity_window: return -5.0
        peak = max(equity_window)
        return ((equity_window[-1] - peak) / peak) * 100 if peak > 0 else 0

    def _calculate_profit_factor(self, returns: pd.Series) -> float:
        p, l = returns[returns > 0].sum(), abs(returns[returns < 0].sum())
        return p / l if l > 0 else 999

    def _calculate_consecutive_losses(self, returns: pd.Series) -> int:
        max_c, current_c = 0, 0
        for r in returns:
            if r < 0:
                current_c += 1
                max_c = max(max_c, current_c)
            else: current_c = 0
        return max_c

    def _simulate_adaptation_score(self, regime, probs, wr, dd) -> float:
        score = 50.0
        if regime == "bull_trend" and probs.get('bull', 0) > 0.6: score += 20
        if wr < 40: score -= 15
        if dd < -25: score -= 20
        return min(100, max(0, score))

    def _simulate_regret_rate(self, strategy_id: str, regime: str) -> float:
        regret_map = {"bull_trend": 25.0, "bear_trend": 60.0, "mean_reverting": 45.0, "high_volatility": 55.0}
        return regret_map.get(regime, 30.0)

    def _simulate_trade(self, signal, price: float, equity: float) -> Dict:
        size = signal.get('size', 0.1)
        direction = 1 if signal['signal'] == 'buy' else -1
        win_prob = 0.45 + (signal.get('confidence', 0.5) * 0.2)
        pnl_pct = np.random.uniform(0.005, 0.03) if np.random.random() < win_prob else np.random.uniform(-0.03, -0.005)
        cost = (self.commission_pct + self.slippage_pct) * 2
        pnl_pct -= cost
        pnl = (equity * size) * pnl_pct * direction
        return {'pnl': pnl, 'pnl_pct': pnl_pct}

    def save_results(self, filepath: str = "bot-manager/backtest/results/backtest_summary.json"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        summary = {
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'strategy_id': r.strategy_id, 'total_return': r.total_return_pct,
                    'max_drawdown': r.max_drawdown_pct, 'win_rate': r.win_rate,
                    'num_pauses': r.num_pauses, 'num_overrides': r.num_overrides
                } for r in self.results
            ]
        }
        with open(filepath, 'w') as f: json.dump(summary, f, indent=2)