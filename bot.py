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
from pathlib import Path
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
from apuesta.tradingview_bridge import TradingViewBridge
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

                if signal_data:
                    event_id = signal_data.get("timestamp") or json.dumps(signal_data, sort_keys=True)
                    if event_id == self.last_processed:
                        await asyncio.sleep(60)
                        continue

                    status = str(signal_data.get("status", "")).lower()
                    if status == "pending" and not signal_data.get("processed"):
                        strategy_id = (signal_data.get("signal") or {}).get("strategy_id", "unknown")
                        logger.info(f"Nueva señal detectada en GitHub: {strategy_id}")
                        await self._process_signal(signal_data)
                        if signal_data.get("timestamp"):
                            await loop.run_in_executor(None, self._mark_processed, signal_data["timestamp"])
                        self.last_processed = event_id
                    elif status == "no_signal":
                        reason = signal_data.get("reason", "sin razón")
                        logger.info(f"Monitor GitHub: no_signal recibido | reason={reason}")
                        if trade_logger:
                            trade_logger.log_signal_rejected(
                                {"source": "github_poller", "payload": signal_data},
                                f"NO_SIGNAL:{reason}"
                            )
                        self.last_processed = event_id
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
tradingview_bridge: Optional[TradingViewBridge] = None
bot2_decisions_path = Path("data") / "bot2_decisions.jsonl"

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
    global daily_runner, dashboard_generator, telegram, github_poller, tradingview_bridge
    
    logger.info("inicializando componentes del bot...")
    
    os.makedirs("data/reports", exist_ok=True)
    os.makedirs("dashboard/output", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    bot2_decisions_path.parent.mkdir(parents=True, exist_ok=True)
    
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

    tradingview_bridge = TradingViewBridge(
        order_router=order_router,
        bot_registry=bot_registry,
        trade_logger=trade_logger,
        logger=logger,
        notifier=telegram,
        webhook_secret=os.getenv("TV_WEBHOOK_SECRET", os.getenv("WEBHOOK_SECRET", "")),
        risk_usdt=float(os.getenv("APUESTA_RISK_USDT", "1")),
        reward_usdt=float(os.getenv("APUESTA_REWARD_USDT", "1")),
        max_notional_usdt=float(os.getenv("APUESTA_MAX_NOTIONAL_USDT", "10")),
        cooldown_min=int(os.getenv("APUESTA_COOLDOWN_MIN", "5")),
        max_daily_losses=int(os.getenv("APUESTA_MAX_DAILY_LOSSES", "10")),
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


def refresh_dashboard_after_event():
    """
    regenera dashboard usando el reporte más reciente para incluir operaciones/logs actuales.
    """
    if not dashboard_generator:
        return
    try:
        dashboard_generator.generate("data/reports/latest.json")
    except Exception as e:
        logger.warning(f"no se pudo regenerar dashboard tras evento: {e}")

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

def _extract_signal_payload(body: Dict) -> Dict:
    if "status" in body and "signal" in body:
        return body.get("signal") or {}
    return body


def _get_signal_source(body: Dict, signal_payload: Dict, forced_source: Optional[str] = None) -> str:
    if forced_source:
        return forced_source.lower()

    body_source = body.get("source")
    if isinstance(body_source, str) and body_source.strip():
        return body_source.strip().lower()

    params = signal_payload.get("params") or {}
    if isinstance(params, dict):
        src = params.get("source")
        if isinstance(src, str) and src.strip():
            return src.strip().lower()

    strategy_id = str(signal_payload.get("strategy_id", "")).strip().lower()
    if strategy_id.startswith("bot2"):
        return "bot2"

    return "routine"


def _is_allowed_bot2_host(request: Request) -> bool:
    allowed_raw = os.getenv("BOT2_ALLOWED_HOSTS", "127.0.0.1,::1,localhost")
    allowed_hosts = {h.strip().lower() for h in allowed_raw.split(",") if h.strip()}
    client_host = (request.client.host if request.client else "").lower()
    return client_host in allowed_hosts


def _log_bot2_decision(status: str, payload: Dict, result: Optional[Dict] = None, reason: Optional[str] = None):
    record = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "reason": reason,
        "payload": payload,
        "result": result or {},
    }
    with bot2_decisions_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def _receive_webhook_impl(
    request: Request,
    x_webhook_secret: Optional[str] = None,
    forced_source: Optional[str] = None,
):
    raw_body = await request.body()
    if not raw_body:
        logger.warning("webhook rechazado: body vacío")
        raise HTTPException(status_code=400, detail="empty request body")

    decoded = ""
    try:
        decoded = raw_body.decode("utf-8").strip()
    except UnicodeDecodeError:
        logger.warning("webhook rechazado: body no UTF-8")
        raise HTTPException(status_code=400, detail="invalid body encoding")

    # Intento 1: JSON puro
    try:
        body = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = None

    # Intento 2: quitar fences markdown y texto extra
    if body is None:
        cleaned = decoded
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # Si viene texto adicional, tomar desde la primera llave hasta la última
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start:end + 1]
            try:
                body = json.loads(candidate)
            except json.JSONDecodeError:
                body = None

    if body is None:
        preview = decoded[:180].replace("\n", " ")
        logger.warning(f"webhook rechazado: body no es JSON válido | preview={preview}")
        raise HTTPException(status_code=400, detail="invalid json body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="invalid payload")

    # Entrada 2: TradingView (apuesta) via mismo webhook principal
    if forced_source is None and tradingview_bridge and tradingview_bridge.is_tradingview_payload(body):
        provided_secret = (
            x_webhook_secret
            or request.query_params.get("secret")
            or body.get("secret")
        )
        if not tradingview_bridge.is_secret_valid(provided_secret):
            raise HTTPException(status_code=403, detail="invalid secret")

        tv_response, status_code = await tradingview_bridge.handle_payload(body)
        if status_code >= 400:
            raise HTTPException(status_code=status_code, detail=tv_response.get("detail", "tradingview error"))
        refresh_dashboard_after_event()
        return tv_response

    signal_payload = _extract_signal_payload(body)
    source = _get_signal_source(body, signal_payload, forced_source)
    is_bot2 = source == "bot2"

    if is_bot2:
        # Seguridad bot2: secreto dedicado + opcionalmente solo localhost.
        expected_bot2_secret = os.getenv("BOT2_WEBHOOK_SECRET", os.getenv("WEBHOOK_SECRET", ""))
        if expected_bot2_secret and x_webhook_secret != expected_bot2_secret:
            raise HTTPException(status_code=401, detail="unauthorized bot2 webhook")

        bot2_local_only = os.getenv("BOT2_LOCAL_ONLY", "true").lower() == "true"
        if bot2_local_only and not _is_allowed_bot2_host(request):
            raise HTTPException(status_code=403, detail="bot2 webhook only allowed from localhost")
    else:
        # Entrada 1: rutina Claude/GitHub (formato existente)
        expected_secret = os.getenv("WEBHOOK_SECRET")
        if expected_secret and x_webhook_secret != expected_secret:
            raise HTTPException(status_code=401, detail="unauthorized")

    # Acepta envelope completo de rutina para monitoreo continuo
    # Formato esperado: {timestamp, signal, status, processed, reason?}
    if "status" in body and "signal" in body:
        status = str(body.get("status", "")).lower()
        if status != "pending":
            reason = body.get("reason", "no_signal")
            logger.info(f"webhook monitor recibido: status={status}, source={source}, reason={reason}")
            if trade_logger:
                trade_logger.log_signal_rejected(
                    {"source": source, "payload": body},
                    f"NO_SIGNAL:{reason}"
                )
            if is_bot2:
                _log_bot2_decision("received_no_signal", body, {"processed": True}, str(reason))
            return {
                "status": "received_no_signal",
                "processed": True,
                "reason": reason
            }

    try:
        signal = TradingSignal(**signal_payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid signal payload: {e}")
    
    if bot_registry and bot_registry.is_paused(signal.strategy_id):
        if is_bot2:
            _log_bot2_decision("rejected", body, {"status": "rejected", "reason": "bot is paused by manager"}, "PAUSED")
        if telegram and telegram.enabled:
            await telegram.send_signal_rejected(signal.dict(), "PAUSED")
        return {"status": "rejected", "reason": "bot is paused by manager"}
    
    try:
        processed = signal_processor.validate(signal)
        order_result = await order_router.place_order(processed)
        bot_registry.record_trade(signal.strategy_id, order_result)
        if is_bot2:
            _log_bot2_decision("executed", body, {"status": "executed", "order_id": order_result.get("id")})
        refresh_dashboard_after_event()

        order_id = order_result.get("id", "closed") if isinstance(order_result, dict) else getattr(order_result, "id", "closed")
        return {"status": "executed", "order_id": order_id}
    except Exception as e:
        if is_bot2:
            _log_bot2_decision("error", body, {"status": "error"}, str(e))
        if telegram and telegram.enabled:
            await telegram.send_order_error(signal.strategy_id, str(e), signal.dict())
        logger.error(f"error ejecutando orden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
async def receive_webhook(request: Request, x_webhook_secret: Optional[str] = Header(None)):
    return await _receive_webhook_impl(request, x_webhook_secret, forced_source=None)


@app.post("/webhook/bot2")
async def receive_webhook_bot2(request: Request, x_webhook_secret: Optional[str] = Header(None)):
    return await _receive_webhook_impl(request, x_webhook_secret, forced_source="bot2")

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
async def get_dashboard(refresh: bool = False):
    if refresh:
        refresh_dashboard_after_event()
    dashboard_path = "dashboard/output/latest.html"
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    raise HTTPException(status_code=404, detail="dashboard no disponible")


@app.get("/apuesta/health")
async def apuesta_health():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return tradingview_bridge.get_health()


@app.get("/apuesta/report")
async def apuesta_report():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return FileResponse("data/apuesta/trades_report.csv") if os.path.exists("data/apuesta/trades_report.csv") else {"status": "empty", "detail": "sin operaciones"}


@app.get("/apuesta/stats")
async def apuesta_stats():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return tradingview_bridge.get_stats()


@app.get("/apuesta/paper")
async def apuesta_paper():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return FileResponse("data/apuesta/paper_resolved.csv") if os.path.exists("data/apuesta/paper_resolved.csv") else {"status": "empty", "detail": "sin paper resolved"}


@app.get("/apuesta/paper_stats")
async def apuesta_paper_stats():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return tradingview_bridge.get_paper_stats()


@app.post("/apuesta/unpause")
async def apuesta_unpause():
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    return tradingview_bridge.unpause()


@app.post("/apuesta/evaluate")
async def apuesta_evaluate():
    """Fuerza la evaluación WIN/LOSS de todas las posiciones abiertas contra precio de mercado."""
    if not tradingview_bridge:
        raise HTTPException(status_code=503, detail="apuesta module not initialized")
    open_before = len(tradingview_bridge.active_positions)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, tradingview_bridge._evaluate_outcomes)
    open_after = len(tradingview_bridge.active_positions)
    return {
        "status": "ok",
        "open_positions_before": open_before,
        "resolved": open_before - open_after,
        "open_positions_after": open_after,
    }

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=True)