# guía de despliegue

## plataformas soportadas

| plataforma | estado | notas |
|------------|--------|-------|
| Windows 10/11 | ✅ Principal | entorno de desarrollo y producción actual |
| Ubuntu 20.04+ | ✅ Soportado | producción con systemd |
| macOS | ✅ Compatible | sin cambios adicionales |

---

## despliegue en windows (entorno actual)

### requisitos

- Python 3.9+ (con venv)
- ngrok instalado y con cuenta (para dominio fijo)
- Cuenta Alpaca Paper Trading
- Claude Routines configuradas
- PowerShell 5.1+

### instalación

```powershell
# 1. Clonar el repositorio
git clone https://github.com/skeny65/Trading-bot.git
cd Trading-bot

# 2. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
Copy-Item .env.example .env
notepad .env   # editar con tus credenciales reales
```

### arranque del stack completo

usar el script de inicio todo-en-uno:

```powershell
.\scripts\start_trading_stack.bat
```

este script abre **3 ventanas PowerShell** en paralelo:
1. **Bot** — `python bot.py` en puerto 8000
2. **ngrok** — túnel hacia `shaft-goliath-shakable.ngrok-free.dev` (dominio fijo)
3. **Plan B Sender** — `scripts/send_claude_signal.ps1` para envíos manuales

### arranque manual (por componente)

```powershell
# Terminal 1 — Bot
.\venv\Scripts\Activate.ps1
python bot.py

# Terminal 2 — ngrok (dominio fijo)
ngrok http --domain=shaft-goliath-shakable.ngrok-free.dev 8000

# Terminal 3 — Enviador manual (plan B)
.\scripts\send_claude_signal.ps1
```

### verificar que todo está corriendo

```powershell
# Health check básico
Invoke-RestMethod http://localhost:8000/health

# Health check detallado (CPU, memoria, próximo análisis)
Invoke-RestMethod http://localhost:8000/health/detailed

# Ver dashboard en el navegador
Start-Process "http://localhost:8000/dashboard"
```

---

## configuración de ngrok

### dominio fijo (cuenta gratuita de ngrok)

```powershell
# Autenticar ngrok (solo primera vez)
ngrok config add-authtoken <tu_token>

# Iniciar con dominio fijo
ngrok http --domain=shaft-goliath-shakable.ngrok-free.dev 8000
```

la URL pública del webhook es:  
`https://shaft-goliath-shakable.ngrok-free.dev/webhook`

esta URL debe configurarse en claude routines como el endpoint del webhook.

---

## despliegue en linux (ubuntu)

```bash
# 1. Preparar servidor
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git

# 2. Configurar proyecto
git clone https://github.com/skeny65/Trading-bot.git
cd Trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # editar credenciales
```

### instalar como servicio systemd

```bash
chmod +x deploy/install-service.sh scripts/stop.sh
sudo ./deploy/install-service.sh $USER

# Iniciar y habilitar en arranque
sudo systemctl start trading-bot@$USER
sudo systemctl enable trading-bot@$USER

# Verificar estado
sudo systemctl status trading-bot@$USER
```

### monitoreo en linux

```bash
# Logs en tiempo real
sudo journalctl -u trading-bot@$USER -f

# Health check
curl http://localhost:8000/health/detailed
```

### actualización

```bash
git pull origin main
sudo systemctl restart trading-bot@$USER
```

---

## estructura de carpetas relevante para despliegue

```
Trading-bot/
├── bot.py                         # punto de entrada principal
├── .env                           # credenciales (NO commitear)
├── .env.example                   # plantilla de variables
├── requirements.txt               # dependencias Python
├── dashboard/
│   ├── output/latest.html         # dashboard actual (se sobreescribe)
│   ├── dashboard_history.json     # historial de snapshots (365 días)
│   └── template.html              # plantilla neon del dashboard
├── data/
│   ├── reports/latest.json        # último reporte del bot manager
│   ├── trades/                    # logs JSONL de trades por día
│   └── bot_status.json            # estado persistente de bots
├── scripts/
│   ├── start_trading_stack.bat    # arranque completo windows
│   └── send_claude_signal.ps1    # enviador manual plan B
└── deploy/
	├── install-service.sh         # instalador systemd
	└── trading-bot.service        # unit file
```

---

## modo dry run vs live

| variable | valor | efecto |
|----------|-------|--------|
| `EXECUTE_ORDERS=false` | dry run | simula órdenes, no toca Alpaca |
| `EXECUTE_ORDERS=true` | live | ejecuta órdenes reales en Alpaca paper/live |

para cambiar de modo, editar `.env` y reiniciar el bot.

---

## análisis diario automático

el bot ejecuta análisis automático a las **10:00 AM** cada día (APScheduler):

1. carga trades del día anterior
2. calcula métricas por estrategia (WR, DD, PF)
3. detecta régimen de mercado (modelo de Markov)
4. decide PAUSE / HOLD / REACTIVATE por bot
5. guarda reporte en `data/reports/latest.json`
6. regenera dashboard HTML completo
7. envía resumen por Telegram (si configurado)