# api reference
+
base url: `http://localhost:8000` (local) o `https://shaft-goliath-shakable.ngrok-free.dev` (público)

---

## resumen de endpoints

| método | path | descripción |
|--------|------|-------------|
| GET | `/health` | health check básico |
| GET | `/health/detailed` | métricas del sistema (CPU, RAM, uptime) |
| GET | `/mode` | modo de ejecución actual (dry_run / live) |
| GET | `/dashboard` | sirve el dashboard HTML interactivo |
| POST | `/webhook` | recibe señales de trading desde claude |

---

## `GET /health`

health check básico. útil para monitorear que el bot está vivo.

**response 200:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-26T10:00:00.123456"
}
```

---

## `GET /health/detailed`

health check completo con métricas del proceso y del scheduler.

**response 200:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "memory_mb": 45.2,
  "cpu_percent": 2.1,
  "threads": 4,
  "scheduler_running": true,
  "next_daily_run": "2026-04-27 10:00:00-04:00",
  "bots_registered": 3,
  "trades_today": 5,
  "mode": "dry_run"
}
```

---

## `GET /mode`

muestra si el bot está en modo simulación o ejecutando órdenes reales.

**response 200:**
```json
{
  "mode": "dry_run",
  "execute_orders": false,
  "warning": "modo simulación activo"
}
```

cuando `EXECUTE_ORDERS=true` en `.env`:
```json
{
  "mode": "live",
  "execute_orders": true,
  "warning": "live trading activo"
}
```

---

## `GET /dashboard`

sirve el dashboard HTML interactivo generado por `DashboardGenerator`.

- **response 200:** archivo HTML (Content-Type: text/html)
- **response 404:** si el dashboard no ha sido generado aún (`dashboard/output/latest.html` no existe)

el dashboard incluye:
- KPIs en tiempo real (bots activos, WR, drawdown)
- gráficos Plotly interactivos (equity curves, régimen, métricas)
- tabla de decisiones del bot manager
- historial de snapshots diarios (últimos 365 días)
- auto-refresh cada 5 minutos

para acceder: `http://localhost:8000/dashboard` o vía ngrok.

---

## `POST /webhook`

endpoint principal. recibe señales de trading desde claude routines.

**headers requeridos:**
```
Content-Type: application/json
X-Webhook-Secret: <valor de WEBHOOK_SECRET en .env>
```

### caso 1 — señal de trading (status=pending)

**request body:**
```json
{
  "timestamp": "2026-04-26T10:00:00",
  "status": "pending",
  "processed": false,
  "signal": {
    "strategy_id": "strategy_001",
    "symbol": "SPY",
    "action": "buy",
    "confidence": 0.85,
    "size": 0.1
  }
}
```

**response 200 — ejecutado:**
```json
{
  "status": "executed",
  "order_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**response 200 — rechazado (bot pausado):**
```json
{
  "status": "rejected",
  "reason": "bot is paused by manager"
}
```

### caso 2 — monitoreo sin señal (status != pending)

**request body:**
```json
{
  "timestamp": "2026-04-26T10:00:00",
  "status": "no_signal",
  "processed": false,
  "reason": "mercado lateral sin setup",
  "signal": null
}
```

**response 200:**
```json
{
  "status": "received_no_signal",
  "processed": true,
  "reason": "mercado lateral sin setup"
}
```

### caso 3 — señal directa (plan B / legacy)

**request body:**
```json
{
  "strategy_id": "strategy_001",
  "symbol": "SPY",
  "action": "buy",
  "confidence": 0.82,
  "size": 0.1
}
```

---

## códigos de error

| código | descripción |
|--------|-------------|
| `400` | body vacío, encoding inválido, o JSON no parseable |
| `401` | `X-Webhook-Secret` ausente o incorrecto |
| `422` | campos obligatorios del signal faltantes |
| `500` | error interno al enviar la orden a Alpaca |
  "confidence": 0.85,
  "size": 0.1,
  "params": {
    "stop_loss": 0.02,
    "take_profit": 0.04
  }
}
```

**response 200 (ejecutado):**
```json
{
  "status": "executed",
  "order_id": "dry_12345",
  "strategy_id": "rsi_mean_reversion",
  "symbol": "spy",
  "action": "buy",
  "bot_status": "active"
}
```

| código | significado | solución |
|--------|-------------|----------|
| 401 | webhook secret inválido | verificar .env y header |
| 422 | body json inválido | verificar formato del request |
| 500 | error interno | revisar logs/bot.log |