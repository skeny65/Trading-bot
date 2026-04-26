# variables de entorno

configuradas en el archivo `.env` en la raíz del proyecto.

---

## credenciales
| variable | descripción |
|----------|-------------|
| `alpaca_api_key` | api key de alpaca |
| `alpaca_secret_key` | secret key de alpaca |
| `alpaca_base_url` | url de la api (v2) |

## seguridad
| variable | descripción |
|----------|-------------|
| `webhook_secret` | clave para validar webhooks de claude |

## modo de ejecución
| variable | default | descripción |
|----------|---------|-------------|
| `execute_orders` | `false` | `false` = simulación, `true` = real |
| `dry_run_initial_balance` | `100000` | balance ficticio |

## telegram (opcional)
| variable | descripción |
|----------|-------------|
| `telegram_bot_token` | token del bot |
| `telegram_chat_id` | id del chat para alertas |

---

## archivo .env.example
```bash
# alpaca
alpaca_api_key=pk_xxxxxxxxxxxxxxxxxxxxxxxx
alpaca_secret_key=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
alpaca_base_url=https://paper-api.alpaca.markets/v2

# webhook
webhook_secret=mi_clave_secreta_muy_segura_123

# bot
bot_host=0.0.0.0
bot_port=8000

# modo
execute_orders=false
dry_run_initial_balance=100000

# telegram
telegram_bot_token=
telegram_chat_id=
```

## seguridad
* nunca commitear el archivo .env real
* rotar webhook_secret periódicamente