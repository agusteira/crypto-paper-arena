"""Recalcula saldos desde el log de fills y compara con el estado guardado."""
def check(acct, capital):
    cash, pos = capital, {}
    for o in acct["orders"]:
        if o["side"] == "buy":
            cash -= o["usd"]; pos[o["symbol"]] = pos.get(o["symbol"], 0) + o["qty"]
        else:
            cash += o["usd"] - o["fee"]; pos[o["symbol"]] = pos.get(o["symbol"], 0) - o["qty"]
    probs = []
    if abs(cash - acct["cash"]) > 0.01: probs.append(f"cash {acct['cash']:.4f} != recalculado {cash:.4f}")
    for s in set(pos) | set(acct["pos"]):
        a, b = acct["pos"].get(s, 0), pos.get(s, 0)
        if abs(a - b) > 1e-6 * max(1, abs(b)) and not (abs(b) < 1e-9 and s not in acct["pos"]):
            probs.append(f"{s} qty {a} != recalculado {b}")
    return probs
