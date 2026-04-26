# especificación de webhook

## propósito
este documento define el formato exacto que claude routines debe enviar via webhook.

## endpoint
`POST http://tu-ngrok-url/webhook`
`X-Webhook-Secret: tu_clave_secreta`

## formato del json

### campos obligatorios
| campo | tipo | descripción | ejemplo |
|-------|------|-------------|---------|
| strategy_id | string | identificador único de la estrategia | "rsi_mean_reversion" |
| symbol | string | símbolo del activo | "spy", "aapl" |
| action | string | acción a ejecutar | "buy", "sell", "close" |
| confidence | number | confianza de la señal (0.0 a 1.0) | 0.85 |

### campos opcionales
| campo | tipo | default | descripción |
|-------|------|---------|-------------|
| size | number | 0.1 | tamaño de la posición (0.01 a 1.0) |
| params | object | {} | parámetros adicionales |

## ejemplos

### señal de compra básica
```json
{
  "strategy_id": "macd_trend",
  "symbol": "spy",
  "action": "buy",
  "confidence": 0.82
}
```

## validaciones del servidor
el bot valida cada webhook y rechaza si:
* falta x-webhook-secret o es inválido → 401
* falta strategy_id → 422
* bot está en estado paused → 200 con status "rejected"
* confidence menor a 0.5 → 200 con status "rejected"

## troubleshooting
| problema | causa | solución |
|----------|-------|----------|
| 401 unauthorized | secret incorrecto | verificar .env y header |
| 422 validation error | campo faltante | revisar formato json |
| rejected - bot paused | bot manager pausó | revisar dashboard |
| no llega el webhook | ngrok no corre | iniciar ngrok |