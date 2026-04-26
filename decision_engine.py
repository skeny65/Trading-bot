class DecisionEngine:
    def calculate_metrics(self, strategy_id: str) -> dict:
        """Calculates win rate, drawdown, etc."""
        # Dummy data for demo
        return {"win_rate": 0.42, "drawdown": -0.22}

    def get_verdict(self, strategy_id: str, metrics: dict, regime: str) -> str:
        """
        Decides whether to PAUSE, HOLD, or REACTIVATE.
        """
        # Logic: If drawdown < -20% and regime is volatile, PAUSE.
        if metrics["drawdown"] < -0.20:
            return "PAUSE"
        
        # If win_rate > 50% and was paused, maybe REACTIVATE?
        # This is where the 'Learning Override' from your plan lives.
        if metrics["win_rate"] > 0.50:
            return "REACTIVATE"
            
        return "HOLD"