# trading bot manager

sistema de trading algorítmico automatizado con inteligencia artificial. recibe señales de **claude ai**, las valida, y ejecuta órdenes en **alpaca**. se autogestiona diariamente ajustando qué estrategias están activas según su performance real.

---

## arquitectura del sistema

```
SEÑAL PRINCIPAL
Claude Routines ──► ngrok HTTPS ──► bot.py /webhook ──► Alpaca API
										 │
CANAL ALTERNATIVO                        ├──► BotRegistry (pausa/activa)
GitHub repo ─────► GitHubPoller ─────────┤
										 ├──► TradeLogger (JSONL)
PLAN B                                   └──► TelegramNotifier
PowerShell script ──► localhost:8000

ANÁLISIS DIARIO (10:00 AM)
APScheduler ──► DailyRunner
				   ├── LearningEngine (métricas)
				   ├── DecisionEngine (Markov + umbrales)
				   ├── ExecuteDecisions (aplica PAUSE/HOLD/REACTIVATE)
				   ├── HindsightEngine (regret analysis)
				   ├── ReportGenerator (JSON)
				   ├── DashboardGenerator (HTML + Plotly)
				   └── TelegramNotifier (resumen diario)
```

---

## quick start — windows (entorno actual)

```powershell
# 1. clonar y configurar
git clone https://github.com/skeny65/Trading-bot.git
cd Trading-bot
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 2. configurar credenciales
copy .env.example .env
# editar .env con alpaca_api_key, alpaca_secret_key, WEBHOOK_SECRET, etc.

# 3. arrancar el stack completo
# opción A — script todo-en-uno
.\scripts\start_trading_stack.bat

# opción B — componentes manuales
.\venv\Scripts\python.exe bot.py                          # terminal 1
ngrok http 8000 --domain=shaft-goliath-shakable.ngrok-free.dev  # terminal 2
```

el bot queda disponible en:
- local: `http://localhost:8000`
- público: `https://shaft-goliath-shakable.ngrok-free.dev`
- dashboard: `http://localhost:8000/dashboard`

---

## estructura de carpetas

```
trading-bot/
├── bot.py                    ← punto de entrada, FastAPI + scheduler
├── .env                      ← credenciales (no commitear)
├── requirements.txt
│
├── core/                     ← lógica de negocio central
│   ├── alpaca_client.py      ← cliente de la API de Alpaca
│   ├── bot_registry.py       ← estado persistente de bots
│   ├── order_router.py       ← dry_run vs live
│   ├── signal_processor.py   ← validación de señales
│   ├── trade_logger.py       ← log JSONL de trades
│   └── trade_query.py        ← consultas de historial
│
├── manager/                  ← bot manager (análisis diario)
│   ├── daily_runner.py       ← orquestador del análisis 10AM
│   ├── decision_engine.py    ← lógica PAUSE/HOLD/REACTIVATE
│   ├── execute_decisions.py  ← aplica las decisiones
│   ├── hindsight_engine.py   ← evaluación retrospectiva
│   ├── learning_engine.py    ← actualización de métricas
│   └── report_generator.py   ← genera JSON de reportes
│
├── dashboard/                ← generación del dashboard HTML
│   ├── generate_dashboard.py ← genera HTML con Plotly
│   ├── template.html         ← plantilla neon/dark con placeholders
│   ├── output/               ← latest.html generado
│   ├── history/              ← snapshots históricos
│   └── dashboard_history.json ← últimos 365 snapshots
│
├── strategies/               ← estrategias de trading
│   ├── base_strategy.py
│   ├── strategy_001.py
│   ├── strategy_002.py
│   └── strategy_003.py
│
├── data/
│   ├── bot_status.json       ← estado de bots en tiempo real
│   ├── learning_state.json   ← modelo de Markov
│   ├── hindsight_records.json
│   ├── reports/              ← latest.json + YYYY-MM-DD.json
│   └── trades/               ← YYYY-MM-DD.jsonl + archive/
│
├── utils/
│   ├── logger.py
│   ├── telegram_notifier.py
│   ├── circuit_breaker.py
│   ├── dry_run_logger.py
│   ├── retry_handler.py
│   └── state_validator.py
│
├── scripts/
│   ├── start_trading_stack.bat    ← arranque completo en windows
│   └── send_claude_signal.ps1     ← plan B para envío manual
│
└── docs/                     ← documentación completa + prompts de rutina
```

---

## canales de señal

### canal principal — claude routines (webhook)
claude ai envía señales via HTTP POST a:
```
https://shaft-goliath-shakable.ngrok-free.dev/webhook
```
formato envelope: `{ "status": "pending", "signal": { ... } }`  
ver [webhook_format.md](webhook_format.md) para detalles completos.

### canal alternativo — github poller
el bot monitorea `signals/pending_signal.json` en el repositorio `skeny65/Trading-bot`. cuando detecta `"status": "pending"`, procesa la señal y escribe `"status": "processed"`.

### plan b — envío manual
```powershell
.\scripts\send_claude_signal.ps1
```
loop interactivo en PowerShell. pega el JSON, escribe `END` para enviar, `EXIT` para cerrar.

---

## modo dry run vs live

| variable | valor | comportamiento |
|----------|-------|----------------|
| `EXECUTE_ORDERS` | `false` (default) | simula órdenes, escribe logs en `logs/dry_run/` |
| `EXECUTE_ORDERS` | `true` | ejecuta órdenes reales en Alpaca |

verificar el modo activo: `GET /mode`

---

## análisis diario automático (10:00 AM)

el bot manager analiza automáticamente la performance de cada estrategia:

1. **métricas**: calcula win rate, max drawdown, profit factor de los últimos 30 días
2. **régimen**: detecta el régimen de mercado (bull/bear/mean-reverting/volatile)
3. **decisión**: PAUSE si métricas por debajo de umbrales, REACTIVATE si se recuperan
4. **hindsight**: evalúa si las pausas anteriores fueron correctas (regret analysis)
5. **dashboard**: regenera el HTML con gráficos Plotly actualizados
6. **telegram**: envía resumen de decisiones al canal configurado

---

## dashboard

acceso: `http://localhost:8000/dashboard`

incluye:
- estado de todos los bots en tiempo real
- equity curves por estrategia (últimos 30 días)
- régimen de mercado actual con confianza
- tabla de decisiones del bot manager
- comparativas 7d / 30d de métricas
- historial de snapshots diarios (hasta 365 días)
- auto-refresh cada 5 minutos

---

## estado del proyecto

```
[✓] webhook con parser robusto (JSON puro + markdown fences)
[✓] autenticación por WEBHOOK_SECRET
[✓] ejecución en Alpaca (paper trading activo)
[✓] modo dry run con logs separados
[✓] bot manager con análisis diario a las 10:00 AM
[✓] detección de régimen de mercado (Markov Chain)
[✓] decisiones automáticas PAUSE / HOLD / REACTIVATE
[✓] hindsight y regret analysis
[✓] dashboard HTML interactivo con Plotly
[✓] historial del dashboard (365 snapshots)
[✓] badge de estado dinámico (OPERATIVO / PAUSADO)
[✓] adaptation score real desde datos del bot
[✓] notificaciones Telegram
[✓] github poller (canal alternativo de señales)
[✓] plan B — PowerShell interactivo para señales manuales
[✓] túnel ngrok con dominio fijo
[✓] persistencia JSONL de trades con rotación
[✓] circuit breaker y retry handler
[✓] documentación completa (7 archivos)
```

---

## documentación

| archivo | descripción |
|---------|-------------|
| [api_reference.md](api_reference.md) | todos los endpoints del servidor |
| [webhook_format.md](webhook_format.md) | formato de señales, plan B, troubleshooting |
| [deployment.md](deployment.md) | arranque en windows y linux |
| [data_schemas.md](data_schemas.md) | estructura de todos los archivos JSON/JSONL |
| [environment_variables.md](environment_variables.md) | configuración del .env |
| [end_to_end_flow.md](end_to_end_flow.md) | flujo completo claude → alpaca con diagramas |
[x] despliegue 24/7 con systemd
[x] documentación completa

## licencia
mit
