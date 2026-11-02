"""Causal indicators returning long/flat targets, with full warm-up."""
NAMES = ('ema_cross', 'rsi_mr', 'donchian')


def ema(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    value = sum(values[:period]) / period
    out[period - 1] = value
    for i in range(period, len(values)):
        value += 2 / (period + 1) * (values[i] - value)
        out[i] = value
    return out


def sma(values, period):
    out, total = [None] * len(values), 0.0
    for i, value in enumerate(values):
        total += value
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def rsi(values, period=14):
    out = [None] * len(values)
    if len(values) <= period:
        return out
    changes = [b - a for a, b in zip(values, values[1:])]
    gain = sum(max(c, 0) for c in changes[:period]) / period
    loss = sum(max(-c, 0) for c in changes[:period]) / period
    for i in range(period, len(values)):
        if i > period:
            gain = (gain * (period - 1) + max(changes[i - 1], 0)) / period
            loss = (loss * (period - 1) + max(-changes[i - 1], 0)) / period
        out[i] = 100 - 100 / (1 + gain / loss) if loss else (100.0 if gain else 50.0)
    return out


def ema_cross(close, high, low):
    fast, slow, trend = (ema(close, p) for p in (20, 50, 200))
    return [int(t is not None and f > s and c > t) for c, f, s, t in zip(close, fast, slow, trend)]


def rsi_mr(close, high, low):
    target, out = 0, []
    for c, r, t in zip(close, rsi(close), sma(close, 200)):
        if r is not None and t is not None:
            if r > 55:
                target = 0
            elif r < 30 and c > t:
                target = 1
        out.append(target)
    return out


def donchian(close, high, low):
    target, out = 0, []
    for i, c in enumerate(close):
        if i >= 20:
            if c > max(high[i - 20:i]):
                target = 1
            elif c < min(low[i - 10:i]):
                target = 0
        out.append(target)
    return out


def signals(name, candles):
    if name not in NAMES:
        raise ValueError('Unknown strategy')
    return globals()[name](*[[c[k] for c in candles] for k in ('close', 'high', 'low')])
