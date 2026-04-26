class LearningEngine:
    def detect_regime(self) -> str:
        """
        Stub for Markov Model regime detection.
        Returns: 'BULL', 'BEAR', 'VOLATILE', 'SIDEWAYS'
        """
        # Logic would involve fetching last 30 days of SPY data
        # and applying a Hidden Markov Model
        return "VOLATILE"