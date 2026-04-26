import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv

load_dotenv()

class AlpacaClient:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.base_url = os.getenv("ALPACA_BASE_URL")
        
        self.api = tradeapi.REST(
            self.api_key,
            self.secret_key,
            self.base_url,
            api_version='v2'
        )

    def get_account(self):
        return self.api.get_account()

alpaca_client = AlpacaClient()