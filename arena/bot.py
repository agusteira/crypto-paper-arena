"""BOT: momentum con filtro de tendencia. Solo ve velas cerradas pasadas y la interfaz del exchange."""
LOOKBACK = 42 * 6     # momentum de 42 días (velas 4h)
TREND = 50 * 6        # EMA de 50 días
TOP_K = 3
STOP = 0.10           # stop-loss 10% bajo el precio de entrada
MAX_W = 0.33          # máx 33% del capital por moneda

def ema(xs, n):
    k, e = 2 / (n + 1), xs[0]
    for x in xs[1:]: e = x * k + e * (1 - k)
    return e

def targets(hist):
    """hist: {sym: [cierres pasados]} -> set de símbolos a mantener."""
    btc = hist.get("BTCUSDT")
    if not btc or len(btc) < TREND or btc[-1] < ema(btc[-TREND:], TREND):
        return set()  # régimen bajista: todo a USDT
    scores = {}
    for s, c in hist.items():
        if len(c) <= max(LOOKBACK, TREND): continue
        if c[-1] > ema(c[-TREND:], TREND):
            m = c[-1] / c[-1 - LOOKBACK] - 1
            if m > 0: scores[s] = m
    return set(sorted(scores, key=scores.get, reverse=True)[:TOP_K])

def step(ex, hist, memo, rebalance=True):
    """memo: dict del bot (precios de entrada). Devuelve lista de órdenes."""
    px, bal, done = ex.get_prices(), ex.get_balance(), []
    entries = memo.setdefault("entry", {})
    for s, q in list(bal["positions"].items()):   # stop-loss
        if s in entries and px[s] < entries[s] * (1 - STOP):
            done.append(ex.place_order(s, "sell", qty=q, reason="stop-loss")); entries.pop(s, None)
            memo.setdefault("stopped", []).append(s)
    if not rebalance: return [o for o in done if o]
    want = targets(hist) - set(memo.get("stopped", []))
    memo["stopped"] = [s for s in memo.get("stopped", []) if s in targets(hist)]
    bal = ex.get_balance()
    for s, q in bal["positions"].items():
        if s not in want:
            done.append(ex.place_order(s, "sell", qty=q, reason="sale del top-3")); entries.pop(s, None)
    eq = ex.equity()
    for s in sorted(want):
        if s not in ex.get_balance()["positions"]:
            o = ex.place_order(s, "buy", usd=min(eq * MAX_W, ex.get_balance()["cash"]), reason="entra al top-3 momentum")
            if o: entries[s] = o["fill_price"]; done.append(o)
    return [o for o in done if o]
