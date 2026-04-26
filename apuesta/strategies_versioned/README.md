# Apuesta Strategies Versioned

Carpeta dedicada para estrategias Pine versionadas y trazables.

## Convencion de nombres

- Formato: `<asset>-<tema>-vNNN.pine`
- Ejemplo: `ETHUSDT-reversal-guard-v002.pine`

## Reglas de versionado

- `v001`: version base funcional.
- `v002+`: mejoras incrementales (filtros, gestion de riesgo, timing).
- No sobrescribir versiones anteriores; crear una nueva version en cada cambio relevante.

## Checklist minimo por version

- Definir timeframe objetivo.
- Definir filtros de tendencia/volatilidad.
- Definir mecanismo anti-overtrading (cooldown).
- Definir guardas anti-reversa inmediata BUY/SELL.
- Confirmar formato JSON de alertas compatible con `apuesta/tradingview_bridge.py`.

## Estrategias actuales

- ETHUSDT-reversal-guard-v002.pine
- ETHUSDT-trend-trail-v003.pine

## Estrategias legacy (no activas)

- BTCUSD-reversal-guard-v001.pine
