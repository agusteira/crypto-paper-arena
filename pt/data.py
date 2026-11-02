"""Public OHLC data with CSV caching; requests is the only dependency."""
import csv
import math
from pathlib import Path
import statistics
import time
import warnings
import requests

INTERVAL_MS = 14400000
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
HOSTS = ('https://api.binance.com', 'https://data-api.binance.vision')
FIELDS = ('open_time', 'open', 'high', 'low', 'close', 'close_time')


def validate(row):
    c = {k: int(row[k]) if k.endswith('time') else float(row[k]) for k in FIELDS}
    if not all(math.isfinite(c[k]) and c[k] > 0 for k in ('open', 'high', 'low', 'close')):
        raise ValueError('Invalid candle price')
    if not c['low'] <= min(c['open'], c['close']) <= max(c['open'], c['close']) <= c['high']:
        raise ValueError('Invalid OHLC range')
    if c['open_time'] % INTERVAL_MS or c['close_time'] != c['open_time'] + INTERVAL_MS - 1:
        raise ValueError('Expected aligned 4h candle')
    return c


def fetch_klines(symbol, start_time, end_time=None, data_dir='data'):
    if symbol not in SYMBOLS:
        raise ValueError('Unsupported symbol')
    now = int(time.time() * 1000)
    end_time = min(now, end_time if end_time is not None else now)
    path = Path(data_dir) / f'klines_{symbol}.csv'
    cached = {}
    if path.exists():
        with path.open(newline='') as f:
            for row in csv.DictReader(f):
                c = validate(row)
                if c['close_time'] <= now:
                    cached[c['open_time']] = c
    cursor = start_time
    while cursor in cached and cached[cursor]['close_time'] <= end_time:
        cursor += INTERVAL_MS
    while cursor + INTERVAL_MS - 1 <= end_time:
        page, errors = None, []
        for host in HOSTS:
            try:
                r = requests.get(host + '/api/v3/klines', params={
                    'symbol': symbol, 'interval': '4h', 'startTime': cursor,
                    'endTime': end_time, 'limit': 1000}, timeout=15)
                r.raise_for_status()
                payload = r.json()
                if not isinstance(payload, list):
                    raise ValueError('Unexpected kline response')
                candidate = [validate(dict(zip(FIELDS, [x[0], x[1], x[2], x[3], x[4], x[6]]))) for x in payload]
                times = [c['open_time'] for c in candidate]
                if times != sorted(set(times)) or any(t < cursor for t in times):
                    raise ValueError('Invalid kline ordering')
                page = candidate
                break
            except (requests.RequestException, ValueError, TypeError, IndexError, KeyError) as exc:
                errors.append(f'{host}: {exc}')
        if page is None:
            warnings.warn(f'{symbol}: network unavailable; using cache. ' + '; '.join(errors))
            break
        if not page:
            break
        for c in page:
            if c['close_time'] <= now:
                cached[c['open_time']] = c
        cursor = page[-1]['open_time'] + INTERVAL_MS
    if cached:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.csv.tmp')
        with tmp.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(cached[t] for t in sorted(cached))
        tmp.replace(path)
    result = [cached[t] for t in sorted(cached) if t >= start_time and cached[t]['close_time'] <= end_time]
    if not result:
        raise RuntimeError(f'No closed candles for {symbol}; provide {path} for offline use')
    return result


def fetch_usdt_ars():
    try:
        r = requests.get('https://criptoya.com/api/usdt/ars/1', timeout=10)
        r.raise_for_status()
        asks = [float(v['ask']) for v in r.json().values() if isinstance(v, dict) and 'ask' in v]
        asks = [v for v in asks if math.isfinite(v) and v > 0]
        if asks:
            return statistics.median(asks)
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        pass
    warnings.warn('USDT/ARS unavailable; using fallback 1450 ARS/USDT')
    return 1450.0


def aligned(candles):
    times = [[c['open_time'] for c in candles[s]] for s in SYMBOLS]
    if times[0] != times[1]:
        raise ValueError('BTC/ETH candles do not align; repair or refresh cache')
    if any(b - a != INTERVAL_MS for a, b in zip(times[0], times[0][1:])):
        raise ValueError('Missing 4h candles; repair or refresh cache')
    return candles
