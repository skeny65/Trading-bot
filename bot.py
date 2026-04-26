#!/usr/bin/env python3
"""
bot.py - sistema de trading local 24/7
combina receptor de webhooks, scheduler de tareas diarias,
y gestión de bots en un solo proceso.
"""

import os
import sys
import json
import signal
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from github import Github

# importar módulos del proyecto
from core.signal_processor import SignalProcessor
from core.order_router import OrderRouter
from core.bot_registry import BotRegistry
from manager.daily_runner import DailyRunner
from manager.learning_engine import LearningEngine
from manager.hindsight_engine import HindsightEngine
from dashboard.generate_dashboard import DashboardGenerator
from utils.logger import setup_logger
from utils.state_validator import StateValidator
from utils.telegram_notifier import TelegramNotifier
from core.trade_logger import TradeLogger

class GitHubSignalPoller:
    """
    lee senales pendientes desde github en lugar de webhook.
    """
    def __init__(self, token: str, repo_name: str, file_path: str = "signals/pending_signal.json"):
        self.token = token
        self.repo_name = repo_name
        self.file_path = file_path
        self.github = Github(self.token) if self.token else None
        self.last_processed = None

    async def poll(self):
        if not self.github:
            logger.warning("GitHub poller deshabilitado: Falta token 'github_token' en .env")
            return
            
        logger.info(f"Iniciando GitHub poller para {self.repo_name}...")
        while True:
            try:
                # Ejecutar lectura síncrona en un hilo separado
                loop = asyncio.get_event_loop()
                signal_data = await loop.run_in_executor(None, self._read_signal)
                
                if signal_data and signal_data.get("status") == "pending" and not signal_data.get("processed"):
                    if signal_data.get("timestamp") != self.last_processed:
                        logger.info(f"Nueva señal detectada en GitHub: {signal_data['signal']['strategy_id']}")
                        await self._process_signal(signal_data)
                        await loop.run_in_executor(None, self._mark_processed, signal_data["timestamp"])
                        self.last_processed = signal_data["timestamp"]
            except Exception as e:
                logger.error(f"Error en GitHub Poller: {e}")
            await asyncio.sleep(60)

    def _read_signal(self):
        try:
            repo = self.github.get_repo(self.repo_name)
            file = repo.get_contents(self.file_path)
            return json.loads(file.decoded_content.decode('utf-8'))
        except: return None

    async def _process_signal(self, signal_data: dict):
        try:
            # Instanciar modelo Pydantic para validación
            signal = TradingSignal(**signal_data.get("signal", {}))
            if bot_registry and bot_registry.is_paused(signal.strategy_id):
                if telegram and telegram.enabled:
                    await telegram.send_signal_rejected(signal.dict(), "PAUSED (via GitHub)")
                return
            processed = signal_processor.validate(signal)
            order_result = await order_router.place_order(processed)
            bot_registry.record_trade(signal.strategy_id, order_result)
        except Exception as e:
            logger.error(f"Error procesando señal de GitHub: {e}")

    def _mark_processed(self, timestamp: str):
        try:
            repo = self.github.get_repo(self.repo_name)
            file = repo.get_contents(self.file_path)
            content = json.loads(file.decoded_content.decode('utf-8'))
            content.update({"processed": True, "status": "processed", "processed_at": datetime.now().isoformat()})
            repo.update_file(self.file_path, f"Processed {timestamp}", json.dumps(content, indent=2), file.sha)
        except Exception as e:
            logger.error(f"Error marcando señal en GitHub: {e}")

# configuración desde .env
from dotenv import load_dotenv
load_dotenv()

# setup logging
logger = setup_logger("bot", "logs/bot.log")

# modelos pydantic
class TradingSignal(BaseModel):
    strategy_id: str
    symbol: str
    action: str  # buy, sell, close
    confidence: float
    size: Optional[float] = 0.1
    params: Optional[Dict] = {}

# variables globales del proceso
scheduler: Optional[AsyncIOScheduler] = None
daily_runner: Optional[DailyRunner] = None
bot_registry: Optional[BotRegistry] = None
signal_processor: Optional[SignalProcessor] = None
order_router: Optional[OrderRouter] = None
dashboard_generator: Optional[DashboardGenerator] = None
validator = StateValidator()
trade_logger: Optional[TradeLogger] = None
telegram: Optional[TelegramNotifier] = None
github_poller: Optional[GitHubSignalPoller] = None

def handle_exit(sig, frame):
    logger.info("Shutdown graceful iniciado...")
    if bot_registry:
        bot_registry._save()
    if trade_logger:
        trade_logger.close()
    if scheduler and scheduler.running:
        scheduler.shutdown()
    logger.info("Estado guardado. Cerrando.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def init_components():
    """inicializa todos los componentes del sistema."""
    global bot_registry, signal_processor, order_router, trade_logger
    global daily_runner, dashboard_generator, telegram, github_poller
    
    logger.info("inicializando componentes del bot...")
    
    os.makedirs("data/reports", exist_ok=True)
    os.makedirs("dashboard/output", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    trade_logger = TradeLogger()
    # Notificador
    telegram = TelegramNotifier()
    
    bot_registry = BotRegistry("data/bot_status.json")
    signal_processor = SignalProcessor()
    order_router = OrderRouter()
    daily_runner = DailyRunner(
        bot_registry=bot_registry,
        learning_state_path="data/learning_state.json",
        hindsight_path="data/hindsight_records.json",
        notifier=telegram
    )
    dashboard_generator = DashboardGenerator()
    github_poller = GitHubSignalPoller(
        token=os.getenv("github_token"),
        repo_name="skeny65/Trading-bot"
    )
    
    logger.info("componentes inicializados correctamente")

async def run_daily_analysis():
    """tarea programada: análisis diario del bot manager."""
    now = datetime.now()
    logger.info(f"iniciando análisis diario: {now}")
    
    try:
        metrics = daily_runner.collect_data()
        regime = daily_runner.detect_regime()
        decisions = daily_runner.evaluate_all_bots()
        daily_runner.execute_decisions(decisions)
        report_path = daily_runner.save_report()
        dashboard_path = dashboard_generator.generate(report_path)
        
        if telegram.enabled:
            await telegram.send_daily_summary(daily_runner.get_summary())
        
        logger.info(f"análisis diario completado. dashboard: {dashboard_path}")
    except Exception as e:
        logger.error(f"error en análisis diario: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """gestión del ciclo de vida de la aplicación."""
    global scheduler
    
    # verificar modo al inicio
    execute_mode = os.getenv("EXECUTE_ORDERS", "false").lower() == "true"
    mode_text = "live trading" if execute_mode else "dry run (simulación)"
    
    logger.info("=" * 60)
    logger.info(f"modo de ejecución: {mode_text}")
    logger.info("=" * 60)
    
    if not execute_mode:
        logger.info("no se enviarán órdenes reales a alpaca")
        logger.info("todas las acciones serán simuladas y logueadas")
        logger.info(f"balance simulado: ${os.getenv('DRY_RUN_INITIAL_BALANCE', '100000')}")
    
    init_components()
    logger.info("Validando integridad de datos...")
    validator.validate_all()

    if telegram.enabled:
        await telegram.send_startup_notification()
        
    scheduler = AsyncIOScheduler(timezone="America/New_York")
    
    scheduler.add_job(
        run_daily_analysis,
        trigger=CronTrigger(hour=10, minute=0, day_of_week="mon-fri"),
        id="daily_analysis"
    )
    
    scheduler.start()
    if github_poller:
        asyncio.create_task(github_poller.poll())

    yield
    if scheduler:
        scheduler.shutdown()
    logger.info("bot detenido")

app = FastAPI(title="trading bot manager", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/webhook")
async def receive_webhook(signal: TradingSignal, x_webhook_secret: Optional[str] = Header(None)):
    expected_secret = os.getenv("WEBHOOK_SECRET")
    if expected_secret and x_webhook_secret != expected_secret:
        raise HTTPException(status_code=401, detail="unauthorized")
    
    if bot_registry and bot_registry.is_paused(signal.strategy_id):
        if telegram.enabled:
            await telegram.send_signal_rejected(signal.dict(), "PAUSED")
        return {"status": "rejected", "reason": "bot is paused by manager"}
    
    try:
        processed = signal_processor.validate(signal)
        order_result = await order_router.place_order(processed)
        bot_registry.record_trade(signal.strategy_id, order_result)
        return {"status": "executed", "order_id": getattr(order_result, 'id', 'closed')}
    except Exception as e:
        if telegram.enabled:
            await telegram.send_order_error(signal.strategy_id, str(e), signal.dict())
        logger.error(f"error ejecutando orden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mode")
async def get_execution_mode():
    """muestra el modo de ejecución actual."""
    is_live = os.getenv("EXECUTE_ORDERS", "false").lower() == "true"
    return {
        "mode": "live" if is_live else "dry_run",
        "execute_orders": is_live,
        "warning": "live trading activo" if is_live else "modo simulación activo"
    }

@app.get("/health/detailed")
async def health_detailed():
    """health check con información del sistema."""
    import psutil
    
    process = psutil.Process(os.getpid())
    
    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - process.create_time()),
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
        "cpu_percent": process.cpu_percent(),
        "threads": process.num_threads(),
        "scheduler_running": scheduler.running if scheduler else False,
        "next_daily_run": str(scheduler.get_job('daily_analysis').next_run_time) if scheduler and scheduler.get_job('daily_analysis') else None,
        "bots_registered": len(bot_registry.list_bots()) if bot_registry else 0,
        "trades_today": len(trade_logger.get_trades_for_date()) if trade_logger else 0,
        "mode": "live" if os.getenv("EXECUTE_ORDERS") == "true" else "dry_run"
    }

@app.get("/dashboard")
async def get_dashboard():
    dashboard_path = "dashboard/output/latest.html"
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    raise HTTPException(status_code=404, detail="dashboard no disponible")

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=True)