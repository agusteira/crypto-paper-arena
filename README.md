# 🤖 Crypto Paper Arena — SOLO SIMULACIÓN

> ⚠️ **Esto es paper trading: dinero ficticio (US$100).** No hay cuenta en ningún exchange, no hay API keys y el código **no puede enviar órdenes reales**. Solo usa precios públicos.

**Dashboard:** https://agusteira.github.io/crypto-paper-arena/

## Arquitectura (el bot no puede hacer trampa)
- `arena/exchange.py` — **Exchange simulado**: es dueño de los saldos, el log de órdenes y el feed de precios. Ejecuta al precio real actual (Binance público) + 0,05% de slippage en contra + 0,1% de comisión.
- `arena/bot.py` — **Bot**: solo usa `get_prices()`, `get_balance()` y `place_order(symbol, side, qty|usd)`. Recibe únicamente velas 4h ya cerradas (no ve el futuro).
- `arena/market.py` — datos públicos (Binance klines/ticker, CoinGecko para el top 10).
- `run.py` — `tick`, `report`, `backtest`. Genera `docs/index.html` (GitHub Pages).

## Universo
Top 10 por market cap de CoinGecko al inicio, **sin stablecoins** y con par USDT en Binance. Se fija en `data/state.json`.

## Estrategia: momentum top-3 con filtro de tendencia
Cada vela 4h cerrada: si BTC está bajo su EMA de 50 días → 100% USDT. Si no, compra las 3 monedas con mayor retorno a 42 días que estén sobre su EMA de 50 días (33% cada una). Stop-loss 10% bajo la entrada (se revisa en cada tick). Parámetros fijos, no optimizados.

## Comparación
- Hold BTC (US$100 en BTC al inicio)
- Hold top-10 equiponderado (US$10 en cada una)

## Uso
```
python run.py tick      # idempotente: rebalancea solo con velas 4h nuevas; revisa stops cada vez
python run.py report
python run.py backtest  # ~2 años, completo + in-sample 70% / out-of-sample 30%
```
GitHub Actions corre `tick` cada hora y commitea `data/` y `docs/`. Resultados del backtest en `data/backtest.md`.
Nota: el backtest usa el top 10 de hoy → tiene sesgo de supervivencia (favorece a todo, incluido el hold).
