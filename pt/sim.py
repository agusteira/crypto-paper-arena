"""Shared execution engine for historical and persistent paper portfolios."""
from .data import SYMBOLS
from .strategies import NAMES, signals

FEE = 0.001
SLIPPAGE = 0.0005
MAX_POSITION = 0.95
STOP = 0.05
BASELINES = ('buy_hold_btc', 'buy_hold_50_50')


def sleeve(cash):
    return dict(cash=cash, qty=0.0, entry=None, stop=None,
                blocked=False, last_processed_open_time=None)


def portfolio(capital, name):
    return {s: sleeve(capital if name == 'buy_hold_btc' and s == 'BTCUSDT' else
                      0 if name == 'buy_hold_btc' else capital / 2) for s in SYMBOLS}


def equity(book, prices):
    return sum(v['cash'] + v['qty'] * prices[s] for s, v in book.items())


def buy(account, price, fraction=MAX_POSITION):
    fill = price * (1 + SLIPPAGE)
    qty = account['cash'] * fraction / (fill * (1 + FEE))
    if qty <= 0:
        return None
    fee = qty * fill * FEE
    account['cash'] -= qty * fill + fee
    account.update(qty=qty, entry=fill, stop=fill * (1 - STOP))
    return dict(side='BUY', price=fill, qty=qty, fee=fee, reason='entry')


def sell(account, price, reason):
    fill = price * (1 - SLIPPAGE)
    qty = account['qty']
    fee = qty * fill * FEE
    account['cash'] += qty * fill - fee
    account.update(qty=0.0, entry=None, stop=None)
    return dict(side='SELL', price=fill, qty=qty, fee=fee, reason=reason)


def step(account, candle, previous_target):
    """Fill previous close target at open, then test low, including entry bar.

    A stopped position requires target=0 before a new target=1 can enter.
    The allocation cap applies at entry; positions are not rebalanced.
    """
    trades = []
    if not previous_target:
        account['blocked'] = False
        if account['qty']:
            trades.append(sell(account, candle['open'], 'signal'))
    elif not account['qty'] and not account['blocked']:
        trade = buy(account, candle['open'])
        if trade:
            trades.append(trade)
    if account['qty'] and candle['low'] <= account['stop']:
        trades.append(sell(account, account['stop'], 'stop'))
        account['blocked'] = True
    account['last_processed_open_time'] = candle['open_time']
    return trades


def drawdown(values, initial):
    peak, worst = initial, 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = max(worst, (peak - value) / peak * 100)
    return worst


def metrics(values, initial, trades):
    return dict(equity=values[-1] if values else initial,
                return_pct=(values[-1] / initial - 1) * 100 if values else 0,
                max_drawdown_pct=drawdown(values, initial), trades=trades)


def backtest(candles, capital, start=0, end=None):
    """Independent fresh capital per model/period, previous history for warm-up.

    First evaluation close produces the first decision. No end liquidation.
    """
    end = len(candles[SYMBOLS[0]]) if end is None else end
    results = {}
    for name in (*NAMES, *BASELINES):
        book = portfolio(capital, name)
        targets = {s: signals(name, candles[s]) for s in SYMBOLS} if name in NAMES else {}
        values, count = [], 0
        for i in range(start, end):
            for s in SYMBOLS:
                c = candles[s][i]
                if name in BASELINES:
                    if i == start and buy(book[s], c['open'], 1.0):
                        count += 1
                elif i > start:
                    count += len(step(book[s], c, targets[s][i - 1]))
            values.append(equity(book, {s: candles[s][i]['close'] for s in SYMBOLS}))
        results[name] = metrics(values, capital, count)
    return results
