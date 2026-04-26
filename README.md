# Trading-bot: Ecosistema de Trading Algorítmico Automatizado

Este proyecto construye un ecosistema completo que combina Inteligencia Artificial (Claude), ejecución de órdenes (Alpaca) y un sistema de monitoreo inteligente (Bot Manager) con aprendizaje adaptativo para decidir cuándo pausar o reactivar estrategias.

## 🚀 Arquitectura del Sistema

El sistema se divide en tres bloques principales:

1.  **Claude Routines (Análisis):** Rutinas diarias que analizan estrategias en GitHub, evalúan el mercado y envían señales mediante Webhooks.
2.  **Bot Core (Ejecución):** Servidor FastAPI que recibe señales, las valida, verifica el estado de riesgo y ejecuta las órdenes en Alpaca.
3.  **Bot Manager (Inteligencia de Riesgo):** Orquestador diario (CRON) que analiza el rendimiento histórico, detecta regímenes de mercado y toma decisiones de "PAUSE" o "REACTIVATE".

---

## 📂 Estructura de Archivos

```text
Trading-bot/
├── main.py                 # Punto de entrada FastAPI (Webhook receptor)
├── client.py               # Cliente base de Alpaca API
├── order_router.py         # Lógica de enrutamiento y ejecución de órdenes
├── signal_processor.py     # Validación de señales y cálculo de sizing
├── monitor.py              # Interfaz del Bot Core con el estado del Manager
├── bot_registry.py         # Persistencia del estado (ACTIVE/PAUSED) de bots
├── alpaca_data_source.py   # Extracción de datos históricos y posiciones
├── daily_runner.py         # Orquestador del Bot Manager (Fases 1-4)
├── learning_engine.py      # Motor de detección de régimen (Markov Model)
├── decision_engine.py      # Motor de veredictos basado en métricas y umbrales
├── execute_decisions.py    # Aplicador de veredictos (cancela órdenes/bloquea bots)
├── routine-config.json     # Configuración de la rutina para Claude MCP
└── .env.example            # Plantilla de variables de entorno
```

---

## 🔄 Flujo Operativo Diario

### 1. Fase de Señal (09:00 AM - 09:05 AM)
*   **Claude** lee las estrategias desde GitHub utilizando MCP.
*   Realiza un análisis técnico y genera una señal JSON.
*   Envía un **POST Webhook** a la URL de `ngrok` con un secret de seguridad.
*   `main.py` recibe la señal:
    1.  Valida el `X-Webhook-Secret`.
    2.  Consulta al `bot_manager` si la estrategia está en pausa.
    3.  `SignalProcessor` valida confianza y parámetros.
    4.  `OrderRouter` envía la orden a **Alpaca Paper/Live Trading**.

### 2. Fase de Inteligencia (10:00 AM - 10:05 AM)
*   Se ejecuta el `daily_runner.py` vía CRON:
    *   **Phase 1 (Data):** Obtiene historial de órdenes y posiciones desde AlpacaDataSource.
    *   **Phase 2 (Learning):** Detecta el régimen de mercado (Bull/Bear/Volatile).
    *   **Phase 3 (Decision):** Calcula Win Rate y Drawdown. Si se superan los umbrales (ej. DD < -20%), emite veredicto `PAUSE`.
    *   **Phase 4 (Execution):** Si el veredicto es `PAUSE`, cancela órdenes abiertas y actualiza `bot_status.json`.
*   Se disparan notificaciones (Telegram/Logs).

---

## 🛡️ Seguridad y Configuración

### Variables de Entorno (.env)
El sistema utiliza un archivo `.env` para gestionar:
*   **Credenciales:** Alpaca API Key/Secret.
*   **Infraestructura:** Dominio de ngrok y tokens de GitHub.
*   **Umbrales de Riesgo:** `THRESHOLD_WR_PAUSE`, `THRESHOLD_DD_PAUSE`, etc.
*   **Seguridad:** `WEBHOOK_SECRET` para firmar las peticiones de Claude.

### Verificación de Webhook
Todas las peticiones entrantes deben incluir el header:
`X-Webhook-Secret: tu_clave_secreta`

---

## 🛠️ Requisitos e Instalación

1.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```
2.  Configurar el archivo `.env` basado en `.env.example`.
3.  Iniciar el servidor de ejecución:
    ```bash
    python main.py
    ```
4.  Ejecutar el manager manualmente para pruebas:
    ```bash
    python daily_runner.py
    ```

---

## 📈 Estado del Proyecto

- [x] Infraestructura Base (FastAPI + Alpaca Client)
- [x] Pipeline de Ejecución (Signal -> Router -> Alpaca)
- [x] Sistema de Bloqueo/Pausa (Bot Registry)
- [x] Recolección de datos (Alpaca Data Source)
- [ ] Implementación avanzada de Markov Model en `learning_engine.py`
- [ ] Dashboard visual en HTML (Fase F)
- [ ] Integración final de notificaciones de Telegram
# Trading-bot: Ecosistema de Trading Algorítmico Automatizado

Este proyecto construye un ecosistema completo que combina Inteligencia Artificial (Claude), ejecución de órdenes (Alpaca) y un sistema de monitoreo inteligente (Bot Manager) con aprendizaje adaptativo para decidir cuándo pausar o reactivar estrategias.

## 🚀 Arquitectura del Sistema

El sistema se divide en tres bloques principales:

1.  **Claude Routines (Análisis):** Rutinas diarias que analizan estrategias en GitHub, evalúan el mercado y envían señales mediante Webhooks.
2.  **Bot Core (Ejecución):** Servidor FastAPI que recibe señales, las valida, verifica el estado de riesgo y ejecuta las órdenes en Alpaca.
3.  **Bot Manager (Inteligencia de Riesgo):** Orquestador diario (CRON) que analiza el rendimiento histórico, detecta regímenes de mercado y toma decisiones de "PAUSE" o "REACTIVATE".

---

## 📂 Estructura de Archivos

```text
Trading-bot/
├── main.py                 # Punto de entrada FastAPI (Webhook receptor)
├── client.py               # Cliente base de Alpaca API
├── order_router.py         # Lógica de enrutamiento y ejecución de órdenes
├── signal_processor.py     # Validación de señales y cálculo de sizing
├── monitor.py              # Interfaz del Bot Core con el estado del Manager
├── bot_registry.py         # Persistencia del estado (ACTIVE/PAUSED) de bots
├── alpaca_data_source.py   # Extracción de datos históricos y posiciones
├── daily_runner.py         # Orquestador del Bot Manager (Fases 1-4)
├── learning_engine.py      # Motor de detección de régimen (Markov Model)
├── decision_engine.py      # Motor de veredictos basado en métricas y umbrales
├── execute_decisions.py    # Aplicador de veredictos (cancela órdenes/bloquea bots)
├── routine-config.json     # Configuración de la rutina para Claude MCP
└── .env.example            # Plantilla de variables de entorno
```

---

## 🔄 Flujo Operativo Diario

### 1. Fase de Señal (09:00 AM - 09:05 AM)
*   **Claude** lee las estrategias desde GitHub utilizando MCP.
*   Realiza un análisis técnico y genera una señal JSON.
*   Envía un **POST Webhook** a la URL de `ngrok` con un secret de seguridad.
*   `main.py` recibe la señal:
    1.  Valida el `X-Webhook-Secret`.
    2.  Consulta al `bot_manager` si la estrategia está en pausa.
    3.  `SignalProcessor` valida confianza y parámetros.
    4.  `OrderRouter` envía la orden a **Alpaca Paper/Live Trading**.

### 2. Fase de Inteligencia (10:00 AM - 10:05 AM)
*   Se ejecuta el `daily_runner.py` vía CRON:
    *   **Phase 1 (Data):** Obtiene historial de órdenes y posiciones desde AlpacaDataSource.
    *   **Phase 2 (Learning):** Detecta el régimen de mercado (Bull/Bear/Volatile).
    *   **Phase 3 (Decision):** Calcula Win Rate y Drawdown. Si se superan los umbrales (ej. DD < -20%), emite veredicto `PAUSE`.
    *   **Phase 4 (Execution):** Si el veredicto es `PAUSE`, cancela órdenes abiertas y actualiza `bot_status.json`.
*   Se disparan notificaciones (Telegram/Logs).

---

## 🛡️ Seguridad y Configuración

### Variables de Entorno (.env)
El sistema utiliza un archivo `.env` para gestionar:
*   **Credenciales:** Alpaca API Key/Secret.
*   **Infraestructura:** Dominio de ngrok y tokens de GitHub.
*   **Umbrales de Riesgo:** `THRESHOLD_WR_PAUSE`, `THRESHOLD_DD_PAUSE`, etc.
*   **Seguridad:** `WEBHOOK_SECRET` para firmar las peticiones de Claude.

### Verificación de Webhook
Todas las peticiones entrantes deben incluir el header:
`X-Webhook-Secret: tu_clave_secreta`

---

## 🛠️ Requisitos e Instalación

1.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```
2.  Configurar el archivo `.env` basado en `.env.example`.
3.  Iniciar el servidor de ejecución:
    ```bash
    python main.py
    ```
4.  Ejecutar el manager manualmente para pruebas:
    ```bash
    python daily_runner.py
    ```

---

## 📈 Estado del Proyecto

- [x] Infraestructura Base (FastAPI + Alpaca Client)
- [x] Pipeline de Ejecución (Signal -> Router -> Alpaca)
- [x] Sistema de Bloqueo/Pausa (Bot Registry)
- [x] Recolección de datos (Alpaca Data Source)
- [ ] Implementación avanzada de Markov Model en `learning_engine.py`
- [ ] Dashboard visual en HTML (Fase F)
- [ ] Integración final de notificaciones de Telegram
