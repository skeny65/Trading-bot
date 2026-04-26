# esquemas de datos

## archivos json

### bot_status.json
estado actual de todos los bots.
```json
{
  "bots": {
    "strategy_id": {
      "strategy_id": "string",
      "symbol": "string",
      "status": "active | paused | hold",
      "registered_at": "iso_datetime",
      "metrics": {
        "win_rate": "number (0-100)",
        "drawdown": "number (negative)"
      }
    }
  }
}
```

### learning_state.json
estado del modelo de markov y aprendizaje.
```json
{
  "regime_history": [
    {
      "date": "YYYY-MM-DD",
      "regime_name": "bull_trend",
      "probabilities": [0.8, 0.1, 0.1]
    }
  ]
}
```

### hindsight_records.json
registro de decisiones y evaluaciones retrospectivas.
```json
{
  "records": [
    {
      "decision_id": "strategy_id_YYYY-MM-DD",
      "strategy_id": "string",
      "verdict": "pause | hold | reactivate",
      "evaluated": "boolean",
      "regret_result": {
        "was_correct": "boolean",
        "missed_profit": "number"
      }
    }
  ]
}
```

### trades/YYYY-MM-DD.jsonl
log de trades en formato json lines (una línea = un json).
```json
{"_id":"20260425103015_a1b2c3d4", "strategy_id":"rsi", "symbol":"spy", "side":"buy", "qty":10, "pnl":0}
```

### reports/YYYY-MM-DD.json
reporte diario generado por el bot manager.
```json
{
  "meta": { "date": "YYYY-MM-DD", "execution_mode": "dry_run | live" },
  "summary": { "total_bots": "integer", "active": "integer" },
  "market_regime": { "regime_name": "string", "confidence": "number" },
  "bots": { ... },
  "decisions": [ ... ]
}
```

## notas sobre formato jsonl
* cada línea es un json válido independiente
* no usar arrays ni objetos multilínea
* append-only: nunca modificar líneas existentes
* rotación: archivos se comprimen a .gz después de 7 días