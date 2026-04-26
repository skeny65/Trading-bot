# api reference

base url: `http://localhost:8000` (local) o tu dominio/ngrok

---

## endpoints públicos

### `GET /`
verifica que el bot está activo.

**response:**
```json
{
  "status": "running",
  "timestamp": "2026-04-25T10:30:00",
  "components": {
    "bot_registry": true,
    "scheduler": true,
    "daily_runner": true
  }
}
```

### `GET /health`
health check básico.

**response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-25T10:30:00",
  "scheduler_jobs": [
    {
      "id": "daily_analysis",
      "name": "análisis diario del bot manager",
      "next_run": "2026-04-26 10:00:00-04:00"
    }
  ],
  "bots_registered": 3
}
```

### `GET /health/detailed`
health check con métricas del sistema.

**response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "memory_mb": 45.2,
  "cpu_percent": 2.1,
  "open_files": 12,
  "threads": 4,
  "scheduler_running": true,
  "next_daily_run": "2026-04-26 10:00:00-04:00",
  "bots_registered": 3,
  "trades_today": 5,
  "mode": "dry_run"
}
```

### `GET /mode`
muestra el modo de ejecución actual.

**response:**
```json
{
  "mode": "dry_run",
  "execute_orders": false,
  "dry_run_logging": true,
  "warning": "modo simulación - sin riesgo financiero"
}
```

---

## endpoints de bots

### `GET /bots`
lista todos los bots registrados.

**response:**
```json
{
  "bots": [
    {
      "strategy_id": "rsi_mean_reversion",
      "symbol": "spy",
      "status": "active",
      "registered_at": "2026-04-20T09:00:00",
      "metrics": {
        "win_rate": 52.3,
        "drawdown": -12.5,
        "profit_factor": 1.35
      }
    }
  ],
  "timestamp": "2026-04-25T10:30:00"
}
```

---

## endpoints de webhook

### `POST /webhook`
recibe señales de trading desde claude routines.

**headers:**
* `Content-Type: application/json`
* `X-Webhook-Secret: tu_clave_secreta`

**body:**
```json
{
  "strategy_id": "rsi_mean_reversion",
  "symbol": "spy",
  "action": "buy",
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