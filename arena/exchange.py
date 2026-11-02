"""EXCHANGE SIMULADO. Es dueño de saldos, ledger y feed de precios.
El bot solo puede usar get_prices / get_balance / place_order. Nunca envía órdenes reales."""
import copy
FEE = 0.001      # 0,1% por operación
SLIPPAGE = 0.0005  # 0,05% en contra

class SimExchange:
    def __init__(self, account, price_feed, clock):
        self._acct = account          # {"cash": float, "pos": {sym: qty}, "orders": [...]}
        self._feed = price_feed       # callable -> {sym: precio actual}
        self._clock = clock           # callable -> timestamp ms
        self._px = None

    def get_prices(self):
        if self._px is None: self._px = dict(self._feed())
        return dict(self._px)

    def get_balance(self):
        a = self._acct  # copia: modificarla no cambia el saldo real
        return {"cash": a["cash"], "positions": dict(a["pos"])}

    def equity(self):
        px = self.get_prices()
        return self._acct["cash"] + sum(q * px[s] for s, q in self._acct["pos"].items())

    def place_order(self, symbol, side, qty=None, usd=None, reason=""):
        px = self.get_prices()[symbol]
        a = self._acct
        if side == "buy":
            fill = px * (1 + SLIPPAGE)
            usd = usd if usd is not None else qty * fill * (1 + FEE)
            if usd > a["cash"] + 1e-9: raise ValueError(f"fondos insuficientes: cash {a['cash']:.4f} < {usd:.4f}")
            if usd < 0.01: return None
            fee = usd * FEE / (1 + FEE)
            q = (usd - fee) / fill
            a["cash"] -= usd
            a["pos"][symbol] = a["pos"].get(symbol, 0) + q
        elif side == "sell":
            have = a["pos"].get(symbol, 0)
            q = qty if qty is not None else usd / px
            if q > have * (1 + 1e-9): raise ValueError(f"cantidad insuficiente de {symbol}: {have} < {q}")
            q = min(q, have)
            if q <= 0: return None
            fill = px * (1 - SLIPPAGE)
            gross = q * fill; fee = gross * FEE
            a["cash"] += gross - fee
            a["pos"][symbol] = have - q
            if a["pos"][symbol] * px < 1e-6: a["pos"].pop(symbol)
            usd = gross
        else:
            raise ValueError(side)
        o = {"time": self._clock(), "symbol": symbol, "side": side, "qty": q, "reason": reason,
             "market_price": px, "fill_price": fill, "usd": round(usd, 6), "fee": round(fee, 6)}
        a["orders"].append(o)
        return copy.deepcopy(o)
