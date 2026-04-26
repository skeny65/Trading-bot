# esquemas de datos
+
## archivos de persistencia

todos los archivos se guardan relativos a la raíz del proyecto.

---

### `data/bot_status.json`

estado persistente de todos los bots. se actualiza en cada webhook y en cada análisis diario.

```json
{
  "strategy_001": {
    "strategy_id": "strategy_001",
    "symbol": "SPY",
    "status": "active",
    "reason": "",
    "registered_at": "2026-04-20T09:00:00",
    "updated_at": "2026-04-26T10:00:00",
    "metrics": {
      "win_rate": 52.3,
      "drawdown": -12.5,
      "profit_factor": 1.35
    },
    "last_trade": "2026-04-25T15:30:00",
    "trade_count": 42
  }
}
```

**valores de `status`:** `"active"` | `"paused"` | `"hold"`

---

### `data/reports/latest.json` y `data/reports/YYYY-MM-DD.json`

reporte generado por `DailyRunner` a las 10:00 AM. `latest.json` siempre es el más reciente.

```json
{
  "date": "2026-04-26",
  "generated_at": "2026-04-26T10:00:05.123456",
  "regime": "UNKNOWN",
  "decisions": [
    {
      "strategy_id": "strategy_001",
      "verdict": "PAUSE",
      "regime": "UNKNOWN",
      "metrics": {
        "win_rate": 52.4,
        "drawdown": -14.1,
        "profit_factor": 1.0
      }
    }
  ],
  "bots": [
    {
      "strategy_id": "strategy_001",
      "status": "paused",
      "reason": "Decision engine verdict: PAUSE",
      "metrics": { "win_rate": 52.4, "drawdown": -14.1, "profit_factor": 1.0 },
      "last_trade": "2026-04-25T15:30:00",
      "updated_at": "2026-04-26T10:00:05"
    }
  ],
  "hindsight_summary": {
    "total_decisions": 10,
    "correct_pauses": 7,
    "regret_rate": 0.15
  }
}
```

---

### `data/learning_state.json`

estado del modelo de Markov y aprendizaje adaptativo.

```json
{
  "regime_history": [
    {
      "date": "2026-04-25",
      "regime_name": "bull_trend",
      "probabilities": [0.8, 0.1, 0.05, 0.05]
    }
  ],
  "transition_matrix": [[0.7, 0.2, 0.1], [0.3, 0.5, 0.2], [0.1, 0.3, 0.6]],
  "last_updated": "2026-04-26T10:00:05"
}
```

---

### `data/hindsight_records.json`

evaluación retrospectiva de decisiones de pausa/reactivación.

```json
{
  "records": [
    {
      "decision_id": "strategy_001_2026-04-20",
      "strategy_id": "strategy_001",
      "verdict": "pause",
      "date": "2026-04-20",
      "evaluated": true,
      "regret_result": {
        "was_correct": true,
        "missed_profit": -2.3,
        "regret_score": 0.12
      }
    }
  ]
}
```

---

### `data/trades/YYYY-MM-DD.jsonl`

log de trades en formato JSON Lines (una línea = un evento). nunca se modifica, solo append.

```jsonl
{"_id":"20260426103015_a1b2c3d4","timestamp":"2026-04-26T10:30:15","strategy_id":"strategy_001","symbol":"SPY","side":"buy","qty":10,"price":512.30,"pnl":0,"mode":"live"}
{"_id":"20260426153000_b2c3d4e5","timestamp":"2026-04-26T15:30:00","strategy_id":"strategy_001","symbol":"SPY","side":"sell","qty":10,"price":518.45,"pnl":61.50,"mode":"live"}
```

archivos anteriores se mueven a `data/trades/archive/` tras 7 días.

---

### `dashboard/dashboard_history.json`

historial de snapshots diarios del dashboard. máximo 365 entradas. se actualiza cada vez que se regenera el dashboard.

```json
[
  {
    "timestamp": "2026-04-26T10:00:05.123456",
    "date": "2026-04-26",
    "bots_activos": 1,
    "bots_pausados": 2,
    "total_bots": 3,
    "win_rate_avg": 47.8,
    "max_drawdown": -14.1,
    "regime_name": "Unknown",
    "regime_confidence": 70.0,
    "adaptation_score_avg": 50.0
  }
]
```

este archivo alimenta la sección "Historial del Dashboard" con comparativas 7d / 30d.

---

## reglas de formato JSONL

- cada línea es un JSON válido e independiente
- no usar arrays ni objetos multilínea
- append-only: nunca modificar líneas existentes
- los archivos `.jsonl` son rotados a `data/trades/archive/` automáticamente