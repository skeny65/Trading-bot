# trading bot manager

sistema de trading algorítmico automatizado con inteligencia artificial.

## qué hace

- recibe señales de trading desde **claude ai** via webhook
- ejecuta órdenes en **alpaca** (paper o live)
- analiza performance diaria con **modelos de markov**
- decide automáticamente **pausar o reactivar** estrategias
- aprende de errores con **hindsight analysis**
- genera **dashboard visual** con métricas en tiempo real

## arquitectura
claude → github → webhook → ngrok → bot.py → alpaca
↓
bot manager (10am)
↓
dashboard + alertas

## documentación

- api reference
- formato de webhook
- esquemas de datos
- variables de entorno
- arquitectura completa
- guía de despliegue

## inicio rápido

```bash
git clone https://github.com/tu-usuario/trading-bot.git
cd trading-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editar .env con tus credenciales
python bot.py
```

## estado del proyecto
[x] ejecución de trades via webhook
[x] bot manager con decisiones automáticas
[x] detección de regímenes de mercado
[x] hindsight y regret analysis
[x] dashboard html interactivo
[x] notificaciones telegram
[x] modo dry run / live
[x] persistencia avanzada de trades
[x] despliegue 24/7 con systemd
[x] documentación completa

## licencia
mit
