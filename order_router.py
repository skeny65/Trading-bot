from client import alpaca_client
import logging

# Configure logging for production-level visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderRouter:
    """
    Service responsible for translating validated signals into broker-specific commands.
    """
    def __init__(self):
        self.api = alpaca_client.api

    def place_order(self, processed_params: dict):
        """
        Bridge method to support the new standardized signal pipeline.
        """
        return self.execute_order(
            symbol=processed_params.get("symbol"),
            action=processed_params.get("action"),
            quantity=processed_params.get("quantity"),
            order_type=processed_params.get("order_type", "market"),
            limit_price=processed_params.get("limit_price")
        )

    def execute_order(self, symbol: str, action: str, quantity: float, order_type: str, limit_price: float = None):
        try:
            # Handle position liquidation
            if action.lower() == "close":
                logger.info(f"Requesting liquidation for position: {symbol}")
                return self.api.close_position(symbol)

            side = "buy" if action.lower() == "buy" else "sell"
            
            # Construct order payload
            order_params = {
                "symbol": symbol,
                "qty": quantity,
                "side": side,
                "type": order_type,
                "time_in_force": "gtc"
            }

            if order_type == "limit" and limit_price:
                order_params["limit_price"] = limit_price

            logger.info(f"Routing {side} order to Alpaca: {quantity} shares of {symbol} ({order_type})")
            order = self.api.submit_order(**order_params)
            logger.info(f"Order successfully submitted. ID: {order.id}")
            return order

        except Exception as e:
            logger.error(f"Alpaca API execution error for {symbol}: {str(e)}")
            raise e

order_router = OrderRouter()