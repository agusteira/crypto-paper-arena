# Simulación — sin dinero real

Capital por modelo: 1000 USDT.

DATOS SINTÉTICOS: prueba de lógica, no resultados de mercado.

## Período completo

2024-11-02T20:00:00+00:00 — 2026-11-02T19:59:59.999000+00:00

| Modelo | Equity USDT | Retorno % | Máx. drawdown % | Operaciones |
|---|---:|---:|---:|---:|
| ema_cross | 6299.3648 | 529.94 | 8.59 | 95 |
| rsi_mr | 374.0965 | -62.59 | 62.59 | 90 |
| donchian | 48218.7417 | 4721.87 | 4.45 | 118 |
| buy_hold_btc | 1232.4543 | 23.25 | 28.13 | 1 |
| buy_hold_50_50 | 1291.3733 | 29.14 | 24.00 | 2 |

## In-sample (70%)

2024-11-02T20:00:00+00:00 — 2026-03-28T19:59:59.999000+00:00

| Modelo | Equity USDT | Retorno % | Máx. drawdown % | Operaciones |
|---|---:|---:|---:|---:|
| ema_cross | 3583.8466 | 258.38 | 8.59 | 69 |
| rsi_mr | 504.5223 | -49.55 | 49.55 | 64 |
| donchian | 18067.7543 | 1706.78 | 4.45 | 84 |
| buy_hold_btc | 1352.7949 | 35.28 | 28.13 | 1 |
| buy_hold_50_50 | 1237.0180 | 23.70 | 24.00 | 2 |

## Out-of-sample (30%)

2026-03-28T20:00:00+00:00 — 2026-11-02T19:59:59.999000+00:00

| Modelo | Equity USDT | Retorno % | Máx. drawdown % | Operaciones |
|---|---:|---:|---:|---:|
| ema_cross | 1770.0116 | 77.00 | 8.49 | 27 |
| rsi_mr | 724.6545 | -27.53 | 27.53 | 28 |
| donchian | 2698.0526 | 169.81 | 3.78 | 34 |
| buy_hold_btc | 909.6780 | -9.03 | 28.13 | 1 |
| buy_hold_50_50 | 1056.0786 | 5.61 | 23.96 | 2 |

Parámetros fijos, sin optimización. Capital reiniciado en cada período; indicadores con historia previa. Equity marcada al último cierre, sin liquidación final. Operaciones = ejecuciones de compra o venta; drawdown medido al cierre de cada vela.
