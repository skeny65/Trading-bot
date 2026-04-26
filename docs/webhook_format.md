# especificación de webhook

## propósito
este documento define el formato exacto que claude routines debe enviar via webhook al bot de trading.

## endpoint

```
POST https://<tu-dominio>.ngrok-free.app/webhook
X-Webhook-Secret: <valor de WEBHOOK_SECRET en .env>
Content-Type: application/json
```

en local (sin ngrok): `POST http://localhost:8000/webhook`

---

## formatos aceptados

el bot acepta **dos formatos** de payload: envelope de rutina y señal directa.

---

### formato 1 — envelope de rutina (recomendado)

este es el formato que envía claude routines en cada ejecución, incluya o no una señal real.

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

cuando claude analiza el mercado y **no hay señal**, envía `status != "pending"`:

```json
{
  "timestamp": "2026-04-26T10:00:00",
  "status": "no_signal",
  "processed": false,
  "reason": "mercado lateral sin setup claro",
  "signal": null
}
```

el bot registra este evento como `received_no_signal` sin ejecutar ninguna orden. esto permite monitorear que la rutina sigue corriendo correctamente.

#### campos del envelope
| campo | tipo | requerido | descripción |
|-------|------|-----------|-------------|
| `timestamp` | string ISO | no | momento en que claude generó la señal |
| `status` | string | sí | `"pending"` = hay señal. cualquier otro = sin señal |
| `processed` | boolean | sí | siempre `false` al enviar |
| `signal` | object | si status=pending | objeto de señal (ver abajo) |
| `reason` | string | no | razón de no_signal |

---

### formato 2 — señal directa (plan b / manual)

se usa cuando se envía manualmente con `scripts/send_claude_signal.ps1` o en emergencias.

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

### campos del objeto signal

| campo | tipo | requerido | descripción | ejemplo |
|-------|------|-----------|-------------|---------|
| `strategy_id` | string | **sí** | identificador único de la estrategia | `"strategy_001"` |
| `symbol` | string | **sí** | símbolo del activo (mayúsculas) | `"SPY"`, `"AAPL"` |
| `action` | string | **sí** | acción a ejecutar | `"buy"`, `"sell"`, `"close"` |
| `confidence` | number | **sí** | confianza de la señal (0.0 a 1.0) | `0.85` |
| `size` | number | no (default 0.1) | fracción del capital a usar | `0.1` = 10% |
| `params` | object | no | parámetros adicionales para la estrategia | `{}` |

---

## respuestas del servidor

| status http | body `status` | descripción |
|-------------|---------------|-------------|
| `200` | `"executed"` | orden enviada a alpaca correctamente |
| `200` | `"rejected"` | bot pausado por el manager, no ejecuta |
| `200` | `"received_no_signal"` | monitoreo: rutina corrió pero sin señal |
| `400` | — | body vacío, encoding inválido, o JSON mal formado |
| `401` | — | `X-Webhook-Secret` incorrecto o ausente |
| `422` | — | campos obligatorios faltantes en el signal |
| `500` | — | error interno al colocar la orden en alpaca |

### ejemplo de respuesta exitosa
```json
{
  "status": "executed",
  "order_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## tolerancia a formatos mixtos

el bot tiene un parser robusto de dos pasos:

1. intenta parsear el body como JSON puro
2. si falla, elimina markdown fences (` ```json `) y extrae el primer bloque `{...}` válido

esto permite que claude envíe texto con el JSON embebido sin romper el webhook.

---

## plan b — envío manual con powershell

para enviar señales manualmente sin esperar la rutina de claude:

```powershell
# iniciar el enviador interactivo
.\scripts\send_claude_signal.ps1

# pegar el JSON de claude, terminar con END en línea nueva
# escribir EXIT para cerrar la ventana
```

el script auto-detecta el `.env`, calcula el HMAC si se requiere, y envía con encoding UTF-8.

---

## troubleshooting

| problema | causa probable | solución |
|----------|----------------|----------|
| `401 Unauthorized` | `X-Webhook-Secret` incorrecto | verificar que `.env` y el header coinciden |
| `400 invalid json body` | JSON malformado o encoding incorrecto | revisar el payload; el script PS1 fuerza UTF-8 |
| `422 invalid signal payload` | falta `strategy_id`, `symbol`, `action` o `confidence` | revisar campos obligatorios |
| `rejected - bot is paused` | el bot manager pausó esa estrategia | revisar dashboard para ver la razón |
| webhook no llega | ngrok no está corriendo | iniciar ngrok con el dominio fijo |
| ngrok túnel caído | sesión expirada | reiniciar ngrok; usar dominio fijo para no cambiar URL |