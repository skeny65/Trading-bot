# flujo completo de extremo a extremo

este documento describe el ciclo de vida completo de una señal de trading, desde que claude analiza el mercado hasta que la orden se ejecuta en alpaca, y cómo el sistema aprende de los resultados.

---

## diagrama general

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLAUDE AI (Routines)                                               │
│  Analiza el mercado cada N horas según la rutina configurada        │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP POST con JSON
                             │ X-Webhook-Secret: <clave>
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NGROK (túnel HTTPS)                                                │
│  shaft-goliath-shakable.ngrok-free.dev                              │
│  reenvía el tráfico al puerto 8000 local                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BOT.PY — FastAPI en localhost:8000                                 │
│  POST /webhook                                                      │
│                                                                     │
│  1. valida X-Webhook-Secret                                         │
│  2. parsea JSON (tolerante a markdown fences)                       │
│  3. detecta tipo de payload:                                        │
│     a) status=pending  → hay señal → procesar                       │
│     b) status=no_signal → monitoreo → registrar y salir             │
│  4. verifica que el bot no esté pausado (BotRegistry)               │
│  5. valida la señal (SignalProcessor)                               │
│  6. enruta la orden (OrderRouter)                                   │
└────────────────┬───────────────────────────────────────────────────┘
                 │ si EXECUTE_ORDERS=true
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ALPACA API (Paper o Live)                                          │
│  paper-api.alpaca.markets  o  api.alpaca.markets                    │
│                                                                     │
│  - recibe la orden (market / limit)                                 │
│  - confirma con order_id                                            │
│  - ejecuta en el mercado                                            │
└─────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REGISTRO Y PERSISTENCIA                                            │
│  - TradeLogger → data/trades/YYYY-MM-DD.jsonl                       │
│  - BotRegistry → data/bot_status.json (actualiza métricas)         │
│  - TelegramNotifier → alerta si hay error                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## flujo detallado — señal de trading

### paso 1 — claude genera la señal

claude analiza el mercado (precio, volumen, indicadores técnicos, noticias) y decide si hay una oportunidad. genera un JSON con el envelope de rutina:

```json
{
  "timestamp": "2026-04-26T10:00:00",
  "status": "pending",
  "processed": false,
  "signal": {
    "strategy_id": "strategy_001",
    "symbol": "SPY",
    "action": "buy",
    "confidence": 0.87,
    "size": 0.1
  }
}
```

si no hay señal, envía `status: "no_signal"` de todas formas para que el bot sepa que la rutina sigue funcionando.

### paso 2 — ngrok reenvía al bot

ngrok mantiene un túnel HTTPS persistente desde `shaft-goliath-shakable.ngrok-free.dev` al `localhost:8000`. claude envía el webhook a la URL pública y ngrok lo reenvía al bot local en tiempo real.

### paso 3 — bot.py recibe y valida

```
POST /webhook
  ├── verifica X-Webhook-Secret → 401 si no coincide
  ├── parsea body (2 intentos: JSON puro → extraer de markdown)
  ├── detecta envelope vs señal directa
  ├── si status != "pending" → registra como no_signal y responde 200
  ├── verifica bot_registry.is_paused(strategy_id)
  │     └── si paused → responde "rejected", no ejecuta
  └── valida campos del signal (TradingSignal pydantic)
```

### paso 4 — order router decide

```
OrderRouter.place_order(signal)
  ├── si EXECUTE_ORDERS=false → dry_run_logger (simula, no llama a alpaca)
  └── si EXECUTE_ORDERS=true  → alpaca_client.place_order()
        ├── construye el body de la orden (symbol, qty, side)
        ├── POST a Alpaca API /v2/orders
        └── retorna order_id
```

### paso 5 — registro del trade

```
TradeLogger.log_trade({
  strategy_id, symbol, side, qty, price, order_id, mode
})
→ append a data/trades/YYYY-MM-DD.jsonl

BotRegistry.record_trade(strategy_id, result)
→ actualiza data/bot_status.json
```

### paso 6 — respuesta a claude

el bot responde a claude con el resultado:

```json
{ "status": "executed", "order_id": "abc123-..." }
```

claude puede loggear esta respuesta para auditoría.

---

## flujo del bot manager (análisis diario — 10:00 AM)

cada día a las 10:00 AM el scheduler APScheduler ejecuta el análisis automático:

```
APScheduler trigger → DailyRunner.run()
  │
  ├── LearningEngine.update()
  │     ├── carga trades de los últimos 30 días
  │     ├── calcula win_rate, drawdown, profit_factor por estrategia
  │     └── actualiza learning_state.json
  │
  ├── DecisionEngine.decide()
  │     ├── detecta régimen de mercado (Markov Chain)
  │     │     bull_trend / bear_trend / mean_reverting /
  │     │     high_volatility / low_volatility
  │     ├── compara métricas contra umbrales:
  │     │     win_rate < 45%  → PAUSE
  │     │     win_rate > 52%  → REACTIVATE (si estaba pausado)
  │     │     drawdown < -20% → PAUSE
  │     │     profit_factor < 1.0 → PAUSE
  │     └── emite veredicto por bot: PAUSE / HOLD / REACTIVATE
  │
  ├── ExecuteDecisions.apply()
  │     └── actualiza data/bot_status.json con los nuevos estados
  │
  ├── HindsightEngine.evaluate()
  │     ├── evalúa decisiones pasadas (¿fue correcto pausar ese bot?)
  │     ├── calcula regret_rate (oportunidades perdidas)
  │     └── actualiza hindsight_records.json
  │
  ├── ReportGenerator.save()
  │     ├── escribe data/reports/YYYY-MM-DD.json
  │     └── sobreescribe data/reports/latest.json
  │
  ├── DashboardGenerator.generate()
  │     ├── lee data/reports/latest.json
  │     ├── genera HTML con Plotly (gráficos interactivos)
  │     ├── actualiza dashboard/dashboard_history.json (snapshot)
  │     ├── escribe dashboard/output/latest.html
  │     └── escribe dashboard/history/dashboard_YYYYMMDD_HHMMSS.html
  │
  └── TelegramNotifier.send_daily_summary()
        └── envía resumen con veredictos y métricas al chat
```

---

## plan b — envío manual de señales

cuando las claude routines no están disponibles o hay que enviar una señal manualmente:

```
scripts/start_trading_stack.bat
  └── abre scripts/send_claude_signal.ps1

send_claude_signal.ps1
  ├── auto-detecta .env y lee WEBHOOK_SECRET
  ├── muestra prompt interactivo
  ├── el usuario pega el JSON de claude
  ├── escribe END para enviar o EXIT para cerrar
  ├── valida el formato del envelope
  ├── agrega timestamp si falta
  ├── codifica en UTF-8
  └── POST http://localhost:8000/webhook
        con X-Webhook-Secret del .env
```

---

## flujo de acceso al dashboard

```
usuario → navegador → http://localhost:8000/dashboard
                            │
                       GET /dashboard
                            │
                       FileResponse("dashboard/output/latest.html")
                            │
                       HTML con Plotly (auto-contenido)
                            │
                       auto-refresh cada 5 minutos (JS)
```

el dashboard muestra en tiempo real:
- estado de cada bot (activo / pausado / hold)
- equity curves de los últimos 30 días
- régimen de mercado detectado
- log de decisiones del bot manager
- métricas comparativas entre estrategias
- historial de snapshots diarios (7d / 30d)

---

## flujo completo de extremo a extremo (resumen visual)

```
CLAUDE                NGROK              BOT.PY              ALPACA
  │                     │                  │                    │
  │──── POST /webhook ──►│                  │                    │
  │                     │──── forward ────►│                    │
  │                     │                  │─ validate secret   │
  │                     │                  │─ parse JSON        │
  │                     │                  │─ check bot status  │
  │                     │                  │─ validate signal   │
  │                     │                  │──── POST /orders ──►│
  │                     │                  │◄─── order_id ──────│
  │                     │                  │─ log trade         │
  │◄─── 200 executed ───│◄─── response ───│                    │
  │                     │                  │                    │
  │   (10:00 AM) ────────────────────────►│                    │
  │                     │                  │─ daily analysis    │
  │                     │                  │─ update metrics    │
  │                     │                  │─ PAUSE/HOLD/REACT  │
  │                     │                  │─ generate dashboard│
  │                     │                  │─ telegram notify   │
```

---

## estados posibles de un bot

```
         ┌──────────────────────────────┐
         │           ACTIVE             │
         │  recibe y ejecuta señales    │
         └─────┬────────────────────────┘
               │ WR<45% o DD<-20% o PF<1.0
               ▼
         ┌──────────────────────────────┐
         │           PAUSED             │
         │  rechaza todas las señales   │
         │  sigue monitoreándose        │
         └─────┬────────────────────────┘
               │ WR>52% y recuperación confirmada
               ▼
         ┌──────────────────────────────┐
         │           HOLD               │
         │  métricas ambiguas           │
         │  monitoreo estricto          │
         └──────────────────────────────┘
```

---

## componentes del sistema

| módulo | archivo | responsabilidad |
|--------|---------|-----------------|
| API Server | `bot.py` | FastAPI, scheduler, webhook |
| Signal Processor | `core/signal_processor.py` | valida y normaliza señales |
| Order Router | `core/order_router.py` | decide dry_run vs live |
| Alpaca Client | `core/alpaca_client.py` | conecta con API de Alpaca |
| Bot Registry | `core/bot_registry.py` | estado persistente de bots |
| Trade Logger | `core/trade_logger.py` | log JSONL de trades |
| Daily Runner | `manager/daily_runner.py` | orquesta el análisis diario |
| Learning Engine | `manager/learning_engine.py` | métricas y actualización |
| Decision Engine | `manager/decision_engine.py` | PAUSE / HOLD / REACTIVATE |
| Hindsight Engine | `manager/hindsight_engine.py` | regret analysis |
| Report Generator | `manager/report_generator.py` | genera JSON de reportes |
| Dashboard Generator | `dashboard/generate_dashboard.py` | genera HTML con Plotly |
| Telegram Notifier | `utils/telegram_notifier.py` | alertas y resúmenes |
| GitHub Poller | `bot.py (inline)` | canal alternativo de señales |
