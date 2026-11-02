#!/usr/bin/env python3
"""Crypto Paper Arena — SOLO SIMULACIÓN. Nunca opera con dinero real."""
import json, sys, time, os, html, datetime as dt
from arena import market, bot
from arena.exchange import SimExchange
from arena import integrity
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE = os.path.join(D, "state.json")
CAPITAL = 100.0
BAR = 4 * 3600 * 1000

def now_ms(): return int(time.time() * 1000)
def iso(ms): return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def new_acct(): return {"cash": CAPITAL, "pos": {}, "orders": []}
def load(): return json.load(open(STATE))
def save(s):
    json.dump(s, open(STATE + ".tmp", "w"), indent=1); os.replace(STATE + ".tmp", STATE)

def history(syms, bars=bot.TREND + bot.LOOKBACK + 10):
    start = now_ms() - (bars + 2) * BAR
    return {s: market.klines(s, "4h", start) for s in syms}

def buy_baselines(st, px):
    syms = [u["symbol"] for u in st["universe"]]
    ex = SimExchange(st["accounts"]["hold_btc"], lambda: px, now_ms); ex.place_order("BTCUSDT", "buy", usd=CAPITAL)
    ex = SimExchange(st["accounts"]["hold_top10"], lambda: px, now_ms)
    for s in syms: ex.place_order(s, "buy", usd=CAPITAL / len(syms))

def ensure_ia(st):
    if "ia" not in st["accounts"]:
        st["accounts"]["ia"] = new_acct(); st["ia_start"] = now_ms()

def out(o): print(json.dumps(o, ensure_ascii=False, indent=1))

def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default

def sym(x):
    x = x.upper(); return x if x.endswith("USDT") else x + "USDT"

def cmd_prices():
    st = load(); syms = [u["symbol"] for u in st["universe"]]
    px = market.prices(syms); n = int(arg("--n", 30))
    res = {}
    for s in syms:
        k = market.klines(s, "4h", now_ms() - 45 * BAR)
        c = [x["c"] for x in k]
        res[s] = {"price": px[s], "chg_24h_pct": round((px[s] / c[-6] - 1) * 100, 2),
                  "chg_7d_pct": round((px[s] / c[-42] - 1) * 100, 2), "last_4h_closes": c[-n:]}
    out({"time": iso(now_ms()), "prices": res})

def cmd_candles():
    s = sym(sys.argv[2]); n = int(arg("--n", 60))
    k = market.klines(s, "4h", now_ms() - (n + 2) * BAR)[-n:]
    out({"symbol": s, "interval": "4h", "candles": [{"time": iso(x["t"]), **{j: x[j] for j in "ohlc"}} for x in k]})

def cmd_balance():
    st = load(); ensure_ia(st); a = arg("--account", "ia"); acct = st["accounts"][a]
    px = market.prices([u["symbol"] for u in st["universe"]])
    ex = SimExchange(acct, lambda: px, now_ms); b = ex.get_balance(); eq = ex.equity()
    out({"account": a, "cash_usdt": b["cash"], "positions": {s: {"qty": q, "value_usd": q * px[s]} for s, q in b["positions"].items()},
         "equity_usd": eq, "pnl_usd": eq - CAPITAL, "pnl_pct": (eq / CAPITAL - 1) * 100, "orders": len(acct["orders"])})

def cmd_order():
    import fcntl
    a = arg("--account", "ia"); side = arg("--side"); s = sym(arg("--symbol", "")); reason = arg("--reason")
    if a != "ia": return out({"ok": False, "error": "solo la cuenta ia acepta órdenes manuales"})
    if side not in ("buy", "sell") or not reason: return out({"ok": False, "error": "requiere --side buy|sell y --reason"})
    lock = open(os.path.join(D, ".lock"), "w"); fcntl.flock(lock, fcntl.LOCK_EX)
    st = load(); ensure_ia(st)
    if s not in [u["symbol"] for u in st["universe"]]: return out({"ok": False, "error": f"{s} fuera del universo"})
    acct = st["accounts"]["ia"]
    usd, qty = arg("--usd"), arg("--qty")
    if "--all" in sys.argv: qty = acct["pos"].get(s, 0)
    try:
        ex = SimExchange(acct, lambda: market.prices([s]), now_ms)
        o = ex.place_order(s, side, qty=float(qty) if qty is not None else None, usd=float(usd) if usd is not None else None, reason=reason)
    except Exception as e:
        return out({"ok": False, "error": str(e)})
    if not o: return out({"ok": False, "error": "orden vacía"})
    save(st); out({"ok": True, "fill": o, "cash_usdt": acct["cash"]})

def cmd_publish():
    import subprocess
    cmd_tick(); root = os.path.dirname(os.path.abspath(__file__))
    g = ["git", "-C", root, "-c", "user.name=agusteira", "-c", "user.email=124114633+agusteira@users.noreply.github.com"]
    subprocess.run(g + ["add", "data", "docs"], check=True)
    subprocess.run(g + ["commit", "-qm", "publish " + iso(now_ms())])
    r = subprocess.run(g + ["push", "-q"], capture_output=True, text=True)
    out({"ok": r.returncode == 0, "pushed": r.returncode == 0, "error": r.stderr[-300:] or None, "integrity": load()["integrity"]})

def cmd_tick():
    os.makedirs(D, exist_ok=True)
    if not os.path.exists(STATE):
        uni, skipped = market.top_universe(10)
        st = {"start": now_ms(), "capital_usd": CAPITAL, "universe": uni, "skipped": skipped,
              "accounts": {"bot": new_acct(), "hold_btc": new_acct(), "hold_top10": new_acct()},
              "bot_memo": {}, "last_bar": 0, "equity": []}
        buy_baselines(st, market.prices([u["symbol"] for u in uni]))
    else:
        st = load()
    ensure_ia(st)
    syms = [u["symbol"] for u in st["universe"]]
    px = market.prices(syms)                       # precio real actual
    hist = history(syms)
    last_bar = max(k["t"] for k in hist["BTCUSDT"])
    new_bar = last_bar > st["last_bar"]
    closes = {s: [k["c"] for k in v] for s, v in hist.items()}
    ex = SimExchange(st["accounts"]["bot"], lambda: px, now_ms)
    orders = bot.step(ex, closes, st["bot_memo"], rebalance=new_bar)
    if new_bar: st["last_bar"] = last_bar
    snap = {"time": now_ms()}
    for k, a in st["accounts"].items():
        snap[k] = round(SimExchange(a, lambda: px, now_ms).equity(), 4)
    st["equity"].append(snap); st["last_prices"] = px
    st["integrity"] = {k: integrity.check(a, CAPITAL) for k, a in st["accounts"].items()}
    save(st); dashboard(st)
    print(f"tick {iso(snap['time'])}: vela nueva={new_bar} órdenes={len(orders)} equity={snap}")

def dd(xs):
    m, peak = 0, xs[0] if xs else 0
    for x in xs: peak = max(peak, x); m = min(m, x / peak - 1)
    return m * 100

NAMES = {"ia": "Bot IA", "bot": "Bot reglas (momentum top-3)", "hold_btc": "Hold BTC", "hold_top10": "Hold top-10 equiponderado"}
def summary(st):
    rows = []
    for k, a in st["accounts"].items():
        e = [x[k] for x in st["equity"] if x.get(k) is not None]
        if not e: e = [CAPITAL]
        rows.append((NAMES[k], e[-1], e[-1] - CAPITAL, (e[-1] / CAPITAL - 1) * 100, dd(e), len(a["orders"])))
    return rows

def cmd_report():
    st = load()
    print(f"Inicio: {iso(st['start'])}  | último tick: {iso(st['equity'][-1]['time'])}  | ticks: {len(st['equity'])}")
    print(f"{'Cuenta':28} {'Equity':>9} {'P&L US$':>9} {'Ret %':>8} {'MaxDD %':>8} {'Órdenes':>8}")
    for r in summary(st): print(f"{r[0]:28} {r[1]:9.2f} {r[2]:9.2f} {r[3]:8.2f} {r[4]:8.2f} {r[5]:8d}")
    print("Posiciones bot:", st["accounts"]["bot"]["pos"] or "100% USDT")

def dashboard(st):
    docs = os.path.join(os.path.dirname(D), "docs"); os.makedirs(docs, exist_ok=True)
    px = st["last_prices"]; E = html.escape
    def holds(k):
        a = st["accounts"][k]
        r = "".join(f"<tr><td>{s}</td><td>{q:.6g}</td><td>${q*px[s]:.2f}</td></tr>" for s, q in a["pos"].items())
        return (r or "<tr><td colspan=3>Sin posiciones</td></tr>") + f"<tr><td>USDT (cash)</td><td></td><td>${a['cash']:.2f}</td></tr>"
    def log(k, n=200):
        os_ = st["accounts"][k]["orders"][-n:]
        return "".join(f"<tr><td>{iso(o['time'])}</td><td>{o['symbol']}</td><td>{o['side']}</td><td>${o['usd']:.2f}</td><td>{o['fill_price']:.6g}</td><td>${o['fee']:.4f}</td><td>{E(o.get('reason',''))}</td></tr>" for o in reversed(os_)) or "<tr><td colspan=7>Sin operaciones todavía</td></tr>"
    TH = "<tr><th>Hora</th><th>Par</th><th>Lado</th><th>US$</th><th>Precio</th><th>Fee</th><th>Razón</th></tr>"
    S = summary(st)
    rows = "".join(f"<tr><td>{'<b>'+n+'</b>' if n=='Bot IA' else n}</td><td>${e:.2f}</td><td class={'g' if p>=0 else 'r'}>{p:+.2f} US$ ({r:+.2f}%)</td><td>{d:.2f}%</td><td>{o}</td></tr>" for n,e,p,r,d,o in S)
    ia = [r for r in S if r[0] == "Bot IA"][0]
    bad = {k: v for k, v in st.get("integrity", {}).items() if v}
    integ = f"<p class=bad>❌ INTEGRIDAD: saldos no coinciden con el log de fills: {E(json.dumps(bad, ensure_ascii=False))}</p>" if bad else "<p class=g>✅ Integridad OK: saldos recalculados desde el log de fills coinciden.</p>"
    ia0 = st.get("ia_start", 0)
    eqs = [x for x in st["equity"] if x["time"] >= ia0 - 1]
    data = json.dumps({"t": [iso(x["time"]) for x in eqs], **{k: [x.get(k) for x in eqs] for k in NAMES}})
    uni = ", ".join(u["symbol"].replace("USDT","") for u in st["universe"])
    page = f"""<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Crypto Paper Arena</title><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>body{{font-family:system-ui;margin:12px;background:#0d1117;color:#e6edf3}}table{{border-collapse:collapse;width:100%;font-size:13px;margin-bottom:18px}}td,th{{border-bottom:1px solid #30363d;padding:5px;text-align:left}}.g{{color:#3fb950}}.r{{color:#f85149}}.bad{{background:#5a1e1e;padding:8px}}.w{{background:#3d2e00;padding:8px;border-radius:6px}}.s{{overflow-x:auto}}.big{{font-size:30px;font-weight:700}}.card{{background:#161b22;border:1px solid #58a6ff;border-radius:10px;padding:12px;margin:10px 0}}</style>
<h2>🤖 Crypto Paper Arena</h2><p class=w>⚠️ SIMULACIÓN: dinero ficticio (US$100 por cuenta). No se envía ninguna orden real.</p>
<div class=card><div>🧠 <b>Bot IA</b> (desde {iso(ia0)})</div><div class=big>${ia[1]:.2f}</div><div class={'g' if ia[2]>=0 else 'r'}>{ia[2]:+.2f} US$ ({ia[3]:+.2f}%) · Max DD {ia[4]:.2f}% · {ia[5]} órdenes</div></div>
{integ}
<p>Actualizado: {iso(st['equity'][-1]['time'])}<br>Universo: {uni}</p>
<canvas id=c height=220></canvas>
<h3>Ranking</h3><div class=s><table><tr><th>Cuenta</th><th>Equity</th><th>P&L</th><th>Max DD</th><th>Órdenes</th></tr>{rows}</table></div>
<h3>Posiciones Bot IA</h3><div class=s><table><tr><th>Par</th><th>Cantidad</th><th>Valor</th></tr>{holds('ia')}</table></div>
<h3>Órdenes Bot IA (con razón)</h3><div class=s><table>{TH}{log('ia')}</table></div>
<h3>Posiciones Bot reglas</h3><div class=s><table><tr><th>Par</th><th>Cantidad</th><th>Valor</th></tr>{holds('bot')}</table></div>
<h3>Órdenes Bot reglas</h3><div class=s><table>{TH}{log('bot', 50)}</table></div>
<script>const d={data};new Chart(c,{{type:'line',data:{{labels:d.t,datasets:[{{label:'Bot IA',data:d.ia,borderColor:'#3fb950',borderWidth:3}},{{label:'Bot reglas',data:d.bot,borderColor:'#58a6ff'}},{{label:'Hold BTC',data:d.hold_btc,borderColor:'#f7931a'}},{{label:'Hold top-10',data:d.hold_top10,borderColor:'#a371f7'}}]}},options:{{spanGaps:true,pointRadius:2,scales:{{x:{{ticks:{{maxTicksLimit:6,color:'#8b949e'}}}},y:{{ticks:{{color:'#8b949e'}}}}}},plugins:{{legend:{{labels:{{color:'#e6edf3'}}}}}}}}}});</script></html>"""
    open(os.path.join(docs, "index.html"), "w").write(page)

def cmd_backtest(days=730):
    if os.path.exists(STATE): uni = load()["universe"]
    else: uni, _ = market.top_universe(10)
    syms = [u["symbol"] for u in uni]
    warm = bot.TREND + bot.LOOKBACK + 5
    start = now_ms() - (days * 6 + warm) * BAR
    K = {s: market.klines(s, "4h", start) for s in syms}
    times = [k["t"] for k in K["BTCUSDT"]]
    idx = {s: {k["t"]: k for k in K[s]} for s in syms}
    def run(i0, i1):
        accts = {"bot": new_acct(), "hold_btc": new_acct(), "hold_top10": new_acct()}
        memo, curve = {}, {k: [] for k in accts}
        def opens(i): return {s: idx[s][times[i]]["o"] for s in syms if times[i] in idx[s]}
        live0 = [s for s in syms if times[i0+1] in idx[s]]
        p0 = opens(i0 + 1)
        e = SimExchange(accts["hold_btc"], lambda: p0, lambda: times[i0+1]); e.place_order("BTCUSDT", "buy", usd=CAPITAL)
        e = SimExchange(accts["hold_top10"], lambda: p0, lambda: times[i0+1])
        for s in live0: e.place_order(s, "buy", usd=CAPITAL / len(live0))
        for i in range(i0, i1 - 1):
            t = times[i]
            hist = {s: [idx[s][x]["c"] for x in times[max(0,i-warm):i+1] if x in idx[s]] for s in syms if t in idx[s]}
            p = opens(i + 1)   # se ejecuta en la apertura de la vela siguiente
            for s in list(accts["bot"]["pos"]): p.setdefault(s, idx[s][t]["c"])
            ex = SimExchange(accts["bot"], lambda: p, lambda: times[i+1])
            bot.step(ex, {s: h for s, h in hist.items() if s in p}, memo)
            for k, a in accts.items():
                pp = {**{s: idx[s][t]["c"] for s in syms if t in idx[s]}}
                curve[k].append(a["cash"] + sum(q * pp.get(s, 0) for s, q in a["pos"].items()))
        return {k: (curve[k][-1] / CAPITAL - 1) * 100 for k in accts}, {k: dd(curve[k]) for k in accts}, {k: len(a["orders"]) for k, a in accts.items()}
    i_start = warm
    split = i_start + int((len(times) - i_start) * 0.7)
    out = [f"# Backtest (velas 4h, fee 0,1% + slippage 0,05%, capital US$100)\n", f"Universo: {', '.join(syms)}\n",
           "Parámetros fijos, no optimizados. Monedas sin historial completo entran cuando empiezan a cotizar (el hold top-10 solo compra las que existían al inicio).\n"]
    for name, a, b2 in [("Período completo", i_start, len(times)), ("In-sample (primer 70%)", i_start, split + 1), ("Out-of-sample (último 30%)", split, len(times))]:
        r, d, n = run(a, b2)
        out.append(f"\n## {name}: {iso(times[a])} → {iso(times[b2-1])}\n\n| Cuenta | Retorno % | Max DD % | Órdenes |\n|---|---|---|---|")
        for k in r: out.append(f"| {NAMES[k]} | {r[k]:.1f} | {d[k]:.1f} | {n[k]} |")
    txt = "\n".join(out); print(txt); os.makedirs(D, exist_ok=True); open(os.path.join(D, "backtest.md"), "w").write(txt)

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"prices": cmd_prices, "candles": cmd_candles, "balance": cmd_balance, "order": cmd_order, "publish": cmd_publish, "tick": cmd_tick, "report": cmd_report, "backtest": cmd_backtest}[c]()
