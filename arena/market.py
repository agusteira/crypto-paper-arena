"""Datos de mercado públicos (sin API keys)."""
import time, requests
HOSTS = ["https://data-api.binance.vision", "https://api.binance.com", "https://api1.binance.com"]
STABLES = {"usdt","usdc","usds","dai","usde","usd1","fdusd","tusd","pyusd","busd","usdd","frax","usdp","gusd","rlusd","usdtb","bfusd","usdf","usyc","buidl","usdg","eurc","xaut","paxg"}

def _get(path, params=None):
    err = None
    for h in HOSTS:
        try:
            r = requests.get(h + path, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            err = f"{h}: {r.status_code}"
        except Exception as e:
            err = e
    raise RuntimeError(f"Binance público no disponible: {err}")

def klines(symbol, interval="4h", start_ms=None, limit=1000):
    """Velas CERRADAS solamente."""
    out, now = [], int(time.time() * 1000)
    while True:
        p = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_ms is not None: p["startTime"] = start_ms
        rows = _get("/api/v3/klines", p)
        rows = [r for r in rows if r[6] < now]
        out += [{"t": r[0], "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4])} for r in rows]
        if start_ms is None or len(rows) < limit - 1: break
        start_ms = rows[-1][0] + 1
    return out

def prices(symbols):
    import json
    d = _get("/api/v3/ticker/price", {"symbols": json.dumps(symbols, separators=(",", ":"))})
    return {x["symbol"]: float(x["price"]) for x in d}

def top_universe(n=10):
    cg = requests.get("https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 60, "page": 1}, timeout=20).json()
    listed = {s["symbol"] for s in _get("/api/v3/exchangeInfo")["symbols"] if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"}
    uni, skipped = [], []
    for c in cg:
        s = c["symbol"].lower()
        if s in STABLES or abs((c["current_price"] or 0) - 1) < 0.02:
            skipped.append(f"{s} (stablecoin)"); continue
        pair = s.upper() + "USDT"
        if pair not in listed:
            skipped.append(f"{s} (sin par USDT en Binance)"); continue
        uni.append({"symbol": pair, "coingecko_id": c["id"], "rank": c["market_cap_rank"]})
        if len(uni) == n: break
    return uni, skipped
