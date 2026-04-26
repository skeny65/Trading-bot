# Changelog

## v003

- Archivo: ETHUSDT-trend-trail-v003.pine
- Setup activo: `TREND`
- Enfoque: trend-following multi-timeframe con salida por trailing (Supertrend + Chandelier).
- Payload webhook incluye `trail_pct`, `sl_pct` y `max_risk_usdt` para mejor trazabilidad de riesgo.

## v002

- Archivo: ETHUSDT-reversal-guard-v002.pine
- Setup activo: `RG2`
- Cambios clave: VWAP, filtro de volumen, filtro ATR, ADX y RSI mas permisivos, cooldown reducido.
- Objetivo operativo: mayor frecuencia de senales en ETHUSDT sin perder control anti-reversa.

## v001

- Archivo: BTCUSD-reversal-guard-v001.pine
- Setup legacy: `RG1` (no activo)
- Objetivo: reducir reversas BUY/SELL en <= 1 minuto.
- Controles agregados:
  - Cooldown entre senales (`cooldownBars`).
  - Minimo de barras antes de permitir reversal (`minBarsToReverse`).
  - Filtro de tendencia por cruce EMA(9/21).
  - Filtro de fuerza por ADX.
- Formato de alerta JSON compatible con webhook de apuesta.
