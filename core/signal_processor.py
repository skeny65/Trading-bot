class SignalProcessor:
    """
    Handles validation and transformation of raw signals into executable parameters.
    """
    def validate(self, signal):
        # Basic validation logic
        if signal.confidence < 0.5:
            raise ValueError("confidence too low")

        # Logic to determine quantity (sizing)
        quantity = signal.params.get("quantity", 1)
        
        return {
            "symbol": signal.symbol,
            "action": signal.action,
            "quantity": quantity,
            "order_type": signal.params.get("order_type", "market"),
            "limit_price": signal.params.get("limit_price")
        }