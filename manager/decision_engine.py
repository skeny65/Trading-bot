class DecisionEngine:
    def calculate_metrics(self, strategy_id: str) -> dict:
        """Calculates win rate, drawdown, etc."""
        # Dummy data for demo
        return {"win_rate": 0.42, "drawdown": -0.22}

    def get_verdict(self, strategy_id: str, metrics: dict, regime: str, hindsight=None, adaptation_score: float = 50.0) -> str:
        """
        Decides whether to PAUSE, HOLD, or REACTIVATE.
        """
        is_bear = "BEAR" in regime.upper()

        if metrics["drawdown"] < -0.20:
            if hindsight and not is_bear:
                should_override, reason = hindsight.should_override_pause(strategy_id, regime, adaptation_score)
                if should_override:
                    return "HOLD"
            return "PAUSE"

        if metrics["win_rate"] > 0.50:
            return "REACTIVATE"
            
        return "HOLD"