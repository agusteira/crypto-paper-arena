import contextlib
import copy
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import requests
import run
from pt import data, sim, strategies

BASE = 1700006400000 // data.INTERVAL_MS * data.INTERVAL_MS


def candles(n, start=BASE, scale=1):
    out = []
    for i in range(n):
        p = scale * (100 + i * .03 + 8 * math.sin(i / 13))
        op = scale * (100 + max(0, i - 1) * .03 + 8 * math.sin(max(0, i - 1) / 13))
        t = start + i * data.INTERVAL_MS
        out.append(dict(open_time=t, open=op, high=max(p, op) * 1.01,
                        low=min(p, op) * .99, close=p, close_time=t + data.INTERVAL_MS - 1))
    return out


class Indicators(unittest.TestCase):
    def test_prefix_invariance(self):
        bars = candles(400)
        for name in strategies.NAMES:
            full = strategies.signals(name, bars)
            self.assertTrue(set(full) <= {0, 1})
            for size in (10, 21, 200, 275, 399):
                self.assertEqual(full[:size], strategies.signals(name, bars[:size]))

    def test_prior_donchian(self):
        bars = [dict(close=100, high=101, low=99) for _ in range(20)]
        bars += [dict(close=102, high=103, low=100), dict(close=98, high=102, low=97)]
        self.assertEqual(strategies.signals('donchian', bars)[-2:], [1, 0])

    def test_indicators(self):
        self.assertEqual(strategies.ema([1, 2, 3, 4], 3), [None, None, 2, 3])
        self.assertEqual(strategies.rsi([1] * 30)[14:], [50] * 16)
        self.assertEqual(strategies.rsi(list(range(30)))[14:], [100] * 16)
        self.assertEqual(strategies.rsi(list(range(30, 0, -1)))[14:], [0] * 16)


class Execution(unittest.TestCase):
    def test_stop_and_fresh_signal(self):
        account = sim.sleeve(1000)
        bar = dict(open=100, low=99, open_time=1)
        self.assertEqual(len(sim.step(account, bar, 1)), 1)
        self.assertAlmostEqual(account['cash'], 50)
        self.assertAlmostEqual(account['entry'], 100.05)
        stop = account['stop']
        trades = sim.step(account, dict(open=100, low=90, open_time=2), 1)
        self.assertEqual(trades[0]['reason'], 'stop')
        self.assertAlmostEqual(trades[0]['price'], stop * .9995)
        self.assertEqual(sim.step(account, bar, 1), [])
        self.assertEqual(sim.step(account, bar, 0), [])
        self.assertEqual(len(sim.step(account, bar, 1)), 1)

    def test_entry_bar_stop(self):
        account = sim.sleeve(1000)
        trades = sim.step(account, dict(open=100, low=90, open_time=1), 1)
        self.assertEqual([t['side'] for t in trades], ['BUY', 'SELL'])
        self.assertAlmostEqual(account['cash'], 50 + trades[1]['qty'] * trades[1]['price'] * .999)
        self.assertEqual(account['qty'], 0)

    def test_next_open(self):
        bars = [dict(open_time=i, open=p, close=p, high=p, low=p) for i, p in enumerate([100, 110, 120])]
        with patch('pt.sim.signals', return_value=[1, 0, 0]):
            m = sim.backtest({s: bars for s in data.SYMBOLS}, 1000)['ema_cross']
        qty = 475 / (110 * 1.0005 * 1.001)
        self.assertAlmostEqual(m['equity'], 2 * (25 + qty * 120 * .9995 * .999))
        self.assertEqual(m['trades'], 4)

    def test_baseline_costs_drawdown(self):
        bars = [dict(open_time=0, open=100, close=100, high=100, low=100)]
        m = sim.backtest({s: bars for s in data.SYMBOLS}, 1000)['buy_hold_btc']
        self.assertAlmostEqual(m['equity'], 1000 / (1.0005 * 1.001))
        self.assertEqual(m['trades'], 1)
        self.assertAlmostEqual(sim.drawdown([110, 88, 99], 100), 20)


class Data(unittest.TestCase):
    def test_pagination_fallback_closed_filter(self):
        bars = candles(1002)
        now = bars[-1]['open_time'] + 1000
        calls = []
        def get(url, params, timeout):
            calls.append((url, params['startTime']))
            if url.startswith(data.HOSTS[0]):
                raise requests.ConnectionError('offline')
            selected = [b for b in bars if b['open_time'] >= params['startTime']][:1000]
            rows = [[b['open_time'], b['open'], b['high'], b['low'], b['close'], 0, b['close_time']] for b in selected]
            return Mock(json=lambda: rows, raise_for_status=lambda: None)
        with tempfile.TemporaryDirectory() as directory, patch('pt.data.time.time', return_value=now / 1000), patch('pt.data.requests.get', side_effect=get):
            result = data.fetch_klines('BTCUSDT', BASE, now, directory)
            self.assertEqual(len(result), 1001)
            self.assertIn((data.HOSTS[1] + '/api/v3/klines', bars[1000]['open_time']), calls)
            self.assertEqual(result, data.fetch_klines('BTCUSDT', BASE, now, directory))
            self.assertEqual(len(calls), 4)

    def test_ars(self):
        response = Mock(json=lambda: {'a': {'ask': 1300}, 'b': {'ask': 1500}, 'c': {'ask': 1700}, 'd': {'ask': -2}})
        with patch('pt.data.requests.get', return_value=response):
            self.assertEqual(data.fetch_usdt_ars(), 1500)
        with patch('pt.data.requests.get', side_effect=requests.Timeout), self.assertWarns(UserWarning):
            self.assertEqual(data.fetch_usdt_ars(), 1450)

    def test_reject_gaps(self):
        bars = candles(3)
        with self.assertRaises(ValueError):
            data.aligned({s: [bars[0], bars[2]] for s in data.SYMBOLS})


class Persistent(unittest.TestCase):
    def test_initialization_catchup_idempotence_recovery(self):
        n = 300
        first_now = BASE + n * data.INTERVAL_MS + 1000
        source = {s: candles(n + 4, scale=j + 1) for j, s in enumerate(data.SYMBOLS)}
        def fetch(symbol, start, end, directory):
            return [b for b in source[symbol] if b['open_time'] >= start and b['close_time'] <= end]
        with tempfile.TemporaryDirectory() as directory, patch.object(run, 'DATA_DIR', Path(directory)), patch('run.data.fetch_klines', side_effect=fetch), patch('run.data.fetch_usdt_ars', return_value=1450), patch('run.time.time', return_value=first_now / 1000) as clock, contextlib.redirect_stdout(io.StringIO()):
            run.tick(None)
            state = json.loads((Path(directory) / 'state.json').read_text())
            self.assertEqual(len(state['ledger']), 6)
            self.assertEqual(len(state['equity_history']), 10)
            for info in state['tracks'].values():
                for name in strategies.NAMES:
                    self.assertTrue(all(v['qty'] == 0 for v in info['portfolios'][name].values()))
            clock.return_value = (first_now + 4 * data.INTERVAL_MS) / 1000
            run.tick(None)
            state = json.loads((Path(directory) / 'state.json').read_text())
            books, ledger = copy.deepcopy(state['tracks']), copy.deepcopy(state['ledger'])
            self.assertEqual(len(state['equity_history']), 60)
            (Path(directory) / 'ledger.csv').write_text('interrupted')
            run.tick(None)
            repeated = json.loads((Path(directory) / 'state.json').read_text())
            self.assertEqual(repeated['tracks'], books)
            self.assertEqual(repeated['ledger'], ledger)
            with (Path(directory) / 'ledger.csv').open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), len(ledger))
            for info in repeated['tracks'].values():
                for book in info['portfolios'].values():
                    self.assertTrue(all(a['last_processed_open_time'] == source['BTCUSDT'][-1]['open_time'] for a in book.values()))


if __name__ == '__main__':
    unittest.main()
