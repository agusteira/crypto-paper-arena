# AGENT.md — Reglas para el Bot IA (cuenta `ia`)

⚠️ **Todo es SIMULACIÓN con dinero ficticio (US$100).** No existe ninguna cuenta real ni API key; nunca se envía una orden real.

## Única interfaz permitida
Ejecutar siempre desde cualquier directorio con estas rutas absolutas. Toda la salida es JSON.

```bash
P=/workspace/paper-trader/.venv/bin/python
R=/workspace/paper-trader/run.py

$P $R prices [--n 30]                 # precio actual, cambio 24h/7d y últimos N cierres 4h de las 10 monedas
$P $R candles SOL --n 60              # últimas N velas 4h cerradas (o,h,l,c) de una moneda
$P $R balance --account ia            # cash, posiciones, equity, P&L
$P $R order --account ia --side buy  --symbol SOL --usd 20  --reason "por qué"
$P $R order --account ia --side sell --symbol SOL --qty 0.1 --reason "por qué"
$P $R order --account ia --side sell --symbol SOL --all     --reason "por qué"
$P $R publish                         # marca a mercado todas las cuentas, corre el bot de reglas, regenera el dashboard y pushea
```

## Reglas
1. **Nunca** editar a mano `data/`, `docs/` ni el código. Solo los comandos de arriba.
2. Solo la cuenta `ia`. Universo fijo: BTC, ETH, BNB, XRP, SOL, TRX, HYPE, ZEC, DOGE, LINK (contra USDT). Sin apalancamiento, sin cortos.
3. `--reason` es obligatorio y queda público en el dashboard: explicá la decisión en 1–2 frases.
4. El exchange ejecuta al precio real actual + 0,05% slippage + 0,1% comisión y rechaza órdenes sin fondos (`"ok": false`).
5. Después de operar, correr `publish`. Si `integrity` muestra algo distinto de listas vacías, avisar: hay manipulación.
6. Objetivo: superar al Hold top-10, Hold BTC y al Bot de reglas, con drawdown razonable.

Dashboard: https://agusteira.github.io/crypto-paper-arena/
