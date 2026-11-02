#!/usr/bin/env python3
"""Public-data paper simulation: no keys, accounts, or real orders."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import io
import json
import math
import os
from pathlib import Path
import sys
import time

from pt import data, sim, strategies

DATA_DIR = Path(os.environ.get('PT_DATA_DIR', 'data'))
LEDGER_FIELDS = ('time', 'track', 'strategy', 'symbol', 'side', 'price', 'qty', 'fee', 'reason')
EQUITY_FIELDS = ('time', 'track', 'strategy', 'equity')


def date(milliseconds):
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat()


def atomic_write(path, content):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def csv_text(fields, rows):
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def load_candles(start, now):
    candles = data.aligned({s: data.fetch_klines(s, start, now, DATA_DIR) for s in data.SYMBOLS})
    if candles['BTCUSDT'][0]['open_time'] != start:
        raise ValueError('Cache does not cover requested start including indicator warm-up')
    latest = candles['BTCUSDT'][-1]['open_time']
    expected = now // data.INTERVAL_MS * data.INTERVAL_MS - data.INTERVAL_MS
    if latest < expected:
        print(f'WARNING: cached data ends at {date(latest)}; results are not current.', file=sys.stderr)
    return candles


def table(results):
    lines = ['| Modelo | Equity USDT | Retorno % | Máx. drawdown % | Operaciones |',
             '|---|---:|---:|---:|---:|']
    for name, m in results.items():
        lines.append(f"| {name} | {m['equity']:.4f} | {m['return_pct']:.2f} | {m['max_drawdown_pct']:.2f} | {m['trades']} |")
    return '\n'.join(lines)


def backtest(args):
    now = int(time.time() * 1000)
    end_open = now // data.INTERVAL_MS * data.INTERVAL_MS
    start = end_open - (args.days * 6 + 250) * data.INTERVAL_MS
    candles = load_candles(start, now)
    size, begin = len(candles['BTCUSDT']), 250
    if size - begin < 4:
        raise ValueError('Not enough evaluation candles after 250 warm-up bars')
    split = begin + int((size - begin) * 0.7)
    sections = ['# Simulación — sin dinero real', f'Capital por modelo: {args.capital} USDT.']
    if (DATA_DIR / 'SYNTHETIC').exists():
        sections.append('DATOS SINTÉTICOS: prueba de lógica, no resultados de mercado.')
    for label, first, last in (('Período completo', begin, size),
                               ('In-sample (70%)', begin, split),
                               ('Out-of-sample (30%)', split, size)):
        period = f"{date(candles['BTCUSDT'][first]['open_time'])} — {date(candles['BTCUSDT'][last-1]['close_time'])}"
        sections.extend([f'## {label}', period, table(sim.backtest(candles, args.capital, first, last))])
    sections.append('Parámetros fijos, sin optimización. Capital reiniciado en cada período; indicadores con historia previa. '
                    'Equity marcada al último cierre, sin liquidación final. Operaciones = ejecuciones de compra o venta; '
                    'drawdown medido al cierre de cada vela.')
    output = '\n\n'.join(sections) + '\n'
    atomic_write(DATA_DIR / 'backtest_results.md', output)
    print(output)


def record_trade(state, track, name, symbol, timestamp, trade):
    state['ledger'].append(dict(time=date(timestamp), track=track, strategy=name, symbol=symbol, **trade))


def snapshot(state, timestamp):
    for track, info in state['tracks'].items():
        for name, book in info['portfolios'].items():
            state['equity_history'].append(dict(time=date(timestamp), track=track, strategy=name,
                                                equity=sim.equity(book, state['prices'])))


def export_csv(state):
    atomic_write(DATA_DIR / 'ledger.csv', csv_text(LEDGER_FIELDS, state['ledger']))
    atomic_write(DATA_DIR / 'equity.csv', csv_text(EQUITY_FIELDS, state['equity_history']))


def save_state(state):
    # Commit once to authoritative JSON; CSV views can be recovered after a crash.
    atomic_write(DATA_DIR / 'state.json', json.dumps(state, indent=2, allow_nan=False) + '\n')
    export_csv(state)


def tick(args):
    now = int(time.time() * 1000)
    path = DATA_DIR / 'state.json'
    if not path.exists():
        anchor = (now // data.INTERVAL_MS - 300) * data.INTERVAL_MS
        candles = load_candles(anchor, now)
        latest = {s: candles[s][-1] for s in data.SYMBOLS}
        if any(now - c['close_time'] > data.INTERVAL_MS for c in latest.values()):
            raise ValueError('Cannot initialize live paper mode with stale cached prices')
        rate = data.fetch_usdt_ars()
        state = dict(version=1, start_time=now, indicator_start_time=anchor, usdt_ars=rate,
                     synthetic=(DATA_DIR / 'SYNTHETIC').exists(),
                     prices={s: latest[s]['close'] for s in data.SYMBOLS}, tracks={}, ledger=[], equity_history=[])
        for track, capital in (('ARS_10000', 10000 / rate), ('USD_1000', 1000.0)):
            info = dict(initial_usdt=capital, portfolios={})
            state['tracks'][track] = info
            for name in (*strategies.NAMES, *sim.BASELINES):
                book = sim.portfolio(capital, name)
                info['portfolios'][name] = book
                for s in data.SYMBOLS:
                    book[s]['last_processed_open_time'] = latest[s]['open_time']
                    if name in sim.BASELINES:
                        trade = sim.buy(book[s], latest[s]['close'], 1.0)
                        if trade:
                            record_trade(state, track, name, s, now, trade)
        snapshot(state, now)
        save_state(state)
        print('Simulación inicializada; baselines comprados al último cierre. Sin replay histórico.')
    else:
        state = json.loads(path.read_text())
        candles = load_candles(state['indicator_start_time'], now)
        targets = {name: {s: strategies.signals(name, candles[s]) for s in data.SYMBOLS}
                   for name in strategies.NAMES}
        processed = 0
        for i in range(1, len(candles['BTCUSDT'])):
            timestamp = candles['BTCUSDT'][i]['open_time']
            any_new = False
            for track, info in state['tracks'].items():
                for name, book in info['portfolios'].items():
                    for s in data.SYMBOLS:
                        account = book[s]
                        if timestamp <= account['last_processed_open_time']:
                            continue
                        any_new = True
                        if name in strategies.NAMES:
                            for trade in sim.step(account, candles[s][i], targets[name][s][i - 1]):
                                when = candles[s][i]['close_time'] if trade['reason'] == 'stop' else timestamp
                                record_trade(state, track, name, s, when, trade)
                        else:
                            account['last_processed_open_time'] = timestamp
            if any_new:
                processed += 1
                state['prices'] = {s: candles[s][i]['close'] for s in data.SYMBOLS}
                snapshot(state, candles['BTCUSDT'][i]['close_time'])
        snapshot(state, now)
        save_state(state)
        print(f'Simulación: {processed} velas nuevas procesadas. Estado guardado.')
    report(args)


def report(args):
    path = DATA_DIR / 'state.json'
    if not path.exists():
        raise ValueError('No paper state; run tick first')
    state = json.loads(path.read_text())
    export_csv(state)
    with (DATA_DIR / 'equity.csv').open(newline='') as f:
        history = list(csv.DictReader(f))
    if state.get('synthetic'):
        print('DATOS SINTÉTICOS: prueba de lógica, no resultados de mercado.')
    print(f"Simulación — sin dinero real. Inicio: {date(state['start_time'])}")
    print(f"USDT/ARS inicial fijo: {state['usdt_ars']:.4f}. USD se aproxima a USDT.")
    for track, info in state['tracks'].items():
        results = {}
        for name in info['portfolios']:
            values = [float(r['equity']) for r in history if r['track'] == track and r['strategy'] == name]
            count = sum(r['track'] == track and r['strategy'] == name for r in state['ledger'])
            results[name] = sim.metrics(values, info['initial_usdt'], count)
        print(f'\n{track}\n{table(results)}')
        if track == 'ARS_10000':
            print('Equity ARS (tipo de cambio inicial): ' + ', '.join(
                f"{name}: {m['equity'] * state['usdt_ars']:.2f}" for name, m in results.items()))


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return number


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main():
    parser = argparse.ArgumentParser(description='Crypto PAPER trading: simulación, sin dinero real ni API keys')
    sub = parser.add_subparsers(dest='command', required=True)
    bt = sub.add_parser('backtest')
    bt.add_argument('--days', type=positive_int, default=730)
    bt.add_argument('--capital', type=positive_float, default=1000)
    sub.add_parser('tick')
    sub.add_parser('report')
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            globals()[args.command](args)
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
