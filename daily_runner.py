import logging
import json
import os
from client import alpaca_client
from execute_decisions import BotManagerExecutor
from learning_engine import LearningEngine
from decision_engine import DecisionEngine
from alpaca_data_source import AlpacaDataSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DailyRunner")

def run_daily_manager():
    """
    Orchestrates the 10:00 AM Bot Manager routine.
    """
    logger.info("Starting Daily Bot Manager Routine...")
    
    executor = BotManagerExecutor()
    learner = LearningEngine()
    decider = DecisionEngine()
    data_source = AlpacaDataSource()
    
    # 1. Recolecta datos de Alpaca (Phase 1)
    account = alpaca_client.get_account()
    positions = data_source.get_positions()
    orders = data_source.get_order_history(days=7)
    
    logger.info(f"Equity check: {account.equity}")
    logger.info(f"Phase 1 Complete: {len(positions)} positions and {len(orders)} recent orders retrieved.")

    # 2. Detecta régimen de mercado (Phase 2)
    regime = learner.detect_regime()
    logger.info(f"Current Market Regime: {regime}")

    # 3. Evalúa estrategias (Mapeado de tu lista de estrategias)
    strategies = ["strategy_001", "strategy_002"] # Esto vendría de una DB o config
    
    reports = {}

    for strategy_id in strategies:
        # Phase 3: Toma decisiones
        metrics = decider.calculate_metrics(strategy_id)
        verdict = decider.get_verdict(strategy_id, metrics, regime)
        
        # Phase 4: Ejecuta decisiones
        executor.apply_verdict(strategy_id, verdict)
        
        reports[strategy_id] = {
            "verdict": verdict,
            "metrics": metrics,
            "regime": regime
        }

    # 4. Guardar reporte JSON (Phase 4)
    os.makedirs("data/reports", exist_ok=True)
    with open("data/bot_performance.json", "w") as f:
        json.dump(reports, f, indent=4)
    
    logger.info("Daily Routine Completed. 10:05 AM Notifications triggered.")
    # Here you would call notifications/telegram_bot.py

if __name__ == "__main__":
    run_daily_manager()