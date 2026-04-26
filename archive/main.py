import os
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict
from signal_processor import SignalProcessor
from order_router import order_router
from monitor import BotManagerMonitor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Trading Bot Core")

# Initialize Services
processor = SignalProcessor()
bot_manager = BotManagerMonitor()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

async def verify_webhook_secret(x_webhook_secret: str = Header(None)):
    """
    Security dependency to verify the webhook secret.
    """
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Webhook Secret")

class TradingSignal(BaseModel):
    strategy_id: str
    symbol: str
    action: str  # BUY, SELL, CLOSE
    confidence: float
    params: Dict = {}

@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "bot_manager": bot_manager.get_summary()
    }

@app.post("/webhook")
async def receive_signal(signal: TradingSignal, _ = Depends(verify_webhook_secret)):
    """
    Endpoint to receive signals from Claude Routines.
    Consults Bot Manager before execution and records results.
    """
    # 1. Verificar si el bot está pausado por el Bot Manager
    if bot_manager.is_paused(signal.strategy_id):
        return {
            "status": "rejected",
            "reason": "paused",
            "metrics": bot_manager.get_bot_metrics(signal.strategy_id)
        }

    try:
        # 2. Procesar señal (Valida y calcula sizing/params)
        processed_signal = processor.validate(signal)
        
        # 3. Enviar orden a Alpaca
        order = order_router.place_order(processed_signal)
        
        # 4. Registrar trade para el Bot Manager
        bot_manager.record_trade(signal.strategy_id, order)

        return {
            "status": "executed",
            "order_id": getattr(order, 'id', 'closed'),
            "strategy": signal.strategy_id,
            "bot_manager_status": "ACTIVE"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)