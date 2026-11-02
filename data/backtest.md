# Backtest (velas 4h, fee 0,1% + slippage 0,05%, capital US$100)

Universo: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, SOLUSDT, TRXUSDT, HYPEUSDT, ZECUSDT, DOGEUSDT, LINKUSDT

Parámetros fijos, no optimizados. Monedas sin historial completo entran cuando empiezan a cotizar (el hold top-10 solo compra las que existían al inicio).


## Período completo: 2024-11-03 00:00 UTC → 2026-11-02 16:00 UTC

| Cuenta | Retorno % | Max DD % | Órdenes |
|---|---|---|---|
| Bot (momentum top-3) | 289.4 | -49.5 | 884 |
| Hold BTC | 13.2 | -53.4 | 1 |
| Hold top-10 equiponderado | 392.1 | -58.1 | 9 |

## In-sample (primer 70%): 2024-11-03 00:00 UTC → 2026-03-28 20:00 UTC

| Cuenta | Retorno % | Max DD % | Órdenes |
|---|---|---|---|
| Bot (momentum top-3) | 158.0 | -49.5 | 598 |
| Hold BTC | -2.3 | -49.8 | 1 |
| Hold top-10 equiponderado | 71.2 | -58.1 | 9 |

## Out-of-sample (último 30%): 2026-03-28 20:00 UTC → 2026-11-02 16:00 UTC

| Cuenta | Retorno % | Max DD % | Órdenes |
|---|---|---|---|
| Bot (momentum top-3) | 50.9 | -34.3 | 286 |
| Hold BTC | 16.6 | -29.3 | 1 |
| Hold top-10 equiponderado | 61.7 | -29.7 | 9 |