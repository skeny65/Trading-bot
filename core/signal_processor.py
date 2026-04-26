class SignalProcessor:
    """
    Handles validation and transformation of raw signals into executable parameters.
    """
    def validate(self, signal) -> dict:
        if signal.confidence < 0.5:
            raise ValueError(f"confidence too low: {signal.confidence:.2f} (min 0.5)")

        quantity = signal.params.get("quantity", 1)
        size = getattr(signal, "size", 0.1)

        return {
            "strategy_id": signal.strategy_id,
            "symbol": signal.symbol,
            "action": signal.action,
            "confidence": signal.confidence,
            "size": size,
            "quantity": quantity,
            "order_type": signal.params.get("order_type", "market"),
            "limit_price": signal.params.get("limit_price"),
        }