# variables de entorno
+
configuradas en el archivo `.env` en la raíz del proyecto. nunca commitear este archivo.

---

## alpaca — credenciales de trading

| variable | requerida | descripción | ejemplo |
|----------|-----------|-------------|---------|
| `alpaca_api_key` | **sí** | API Key de Alpaca | `PK_xxxxxxxxxxxxxxxx` |
| `alpaca_secret_key` | **sí** | Secret Key de Alpaca | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `alpaca_base_url` | **sí** | URL base de la API | `https://paper-api.alpaca.markets/v2` |

para usar **paper trading** (simulación con dinero ficticio):
```
alpaca_base_url=https://paper-api.alpaca.markets/v2
```

para usar **live trading** (dinero real):
```
alpaca_base_url=https://api.alpaca.markets/v2
```

---

## seguridad del webhook

| variable | requerida | descripción |
|----------|-----------|-------------|
| `WEBHOOK_SECRET` | **sí** | clave compartida entre claude y el bot para validar webhooks |

el bot rechaza con `401` cualquier webhook sin este header o con valor incorrecto.  
rotar periódicamente y actualizar en claude routines cuando se cambie.

---

## integración local de bot2 (webhook localhost)

| variable | default | descripción |
|----------|---------|-------------|
| `BOT2_WEBHOOK_SECRET` | `WEBHOOK_SECRET` | secreto dedicado para webhooks de bot2. si no se define, usa `WEBHOOK_SECRET` |
| `BOT2_LOCAL_ONLY` | `true` | si `true`, solo acepta bot2 desde hosts locales |
| `BOT2_ALLOWED_HOSTS` | `127.0.0.1,::1,localhost` | lista de hosts permitidos para bot2 (separados por coma) |

ruta recomendada para bot2 local:
```
POST http://127.0.0.1:8000/webhook/bot2
```

headers requeridos para bot2:
```
Content-Type: application/json
X-Webhook-Secret: <BOT2_WEBHOOK_SECRET>
```

logs de bot2 recibidos por bot1:
```
data/bot2_decisions.jsonl
```

---

## modo de ejecución

| variable | default | descripción |
|----------|---------|-------------|
| `EXECUTE_ORDERS` | `false` | `false` = dry run (solo logs), `true` = ejecuta órdenes en Alpaca |
| `dry_run_initial_balance` | `100000` | balance ficticio para cálculos en dry run |

**importante:** cuando `EXECUTE_ORDERS=true`, el bot usa las credenciales de Alpaca para colocar órdenes reales. verificar que `alpaca_base_url` apunte a paper o live según la intención.

---

## servidor

| variable | default | descripción |
|----------|---------|-------------|
| `bot_host` | `0.0.0.0` | interfaz de escucha del servidor FastAPI |
| `bot_port` | `8000` | puerto del servidor |

---

## github — poller de señales (plan B alternativo)

| variable | requerida | descripción |
|----------|-----------|-------------|
| `github_token` | no | token de acceso personal de GitHub para leer señales del repositorio |

si está configurado, el bot también monitorea `signals/pending_signal.json` en el repositorio como canal alternativo de señales (además del webhook).

---

## telegram — notificaciones (opcional)

| variable | requerida | descripción |
|----------|-----------|-------------|
| `telegram_bot_token` | no | token del bot de Telegram |
| `telegram_chat_id` | no | ID del chat o canal donde enviar alertas |

cuando están configurados, el bot envía:
- resumen del análisis diario (10:00 AM)
- alertas de órdenes rechazadas
- errores críticos de ejecución

---

## archivo `.env.example` completo

```bash
# ========================================
# ALPACA — Paper Trading
# ========================================
alpaca_api_key=PK_xxxxxxxxxxxxxxxxxxxxxxxx
alpaca_secret_key=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
alpaca_base_url=https://paper-api.alpaca.markets/v2

# ========================================
# SEGURIDAD
# ========================================
WEBHOOK_SECRET=cambia_esto_por_una_clave_segura_larga
BOT2_WEBHOOK_SECRET=cambia_esto_por_otra_clave_para_bot2
BOT2_LOCAL_ONLY=true
BOT2_ALLOWED_HOSTS=127.0.0.1,::1,localhost

# ========================================
# SERVIDOR
# ========================================
bot_host=0.0.0.0
bot_port=8000

# ========================================
# MODO DE EJECUCIÓN
# ========================================
EXECUTE_ORDERS=false
dry_run_initial_balance=100000

# ========================================
# GITHUB POLLER (opcional)
# ========================================
github_token=ghp_xxxxxxxxxxxxxxxxxxxxxxxx

# ========================================
# TELEGRAM (opcional)
# ========================================
telegram_bot_token=
telegram_chat_id=
```

---

## buenas prácticas de seguridad

- agregar `.env` al `.gitignore` (ya está incluido)
- usar claves de al menos 32 caracteres para `WEBHOOK_SECRET`
- rotar `WEBHOOK_SECRET` cada 90 días y actualizarlo en claude routines
- nunca imprimir el contenido de `.env` en logs
- usar variables de entorno del sistema (no `.env`) en producción con systemd