"""Generate an explicitly labeled OFFLINE fixture, never used automatically."""
import argparse
import csv
import math
from pathlib import Path
import time

INTERVAL_MS = 14400000


def main():
    parser = argparse.ArgumentParser(description='Create SYNTHETIC 4h OHLC fixtures for offline verification')
    parser.add_argument('directory', type=Path)
    parser.add_argument('--days', type=int, default=730)
    args = parser.parse_args()
    if args.days <= 0:
        parser.error('--days must be positive')
    directory = args.directory
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        parser.error('use an empty directory to avoid overwriting market data')
    count = args.days * 6 + 250
    end = int(time.time() * 1000) // INTERVAL_MS * INTERVAL_MS
    for symbol, base, phase in (('BTCUSDT', 30000, 0), ('ETHUSDT', 1800, 1.3)):
        previous = base
        with (directory / f'klines_{symbol}.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=('open_time', 'open', 'high', 'low', 'close', 'close_time'))
            writer.writeheader()
            for i in range(count):
                t = end - (count - i) * INTERVAL_MS
                close = base * math.exp(i * .00007 + .14 * math.sin(i / 37 + phase) + .03 * math.sin(i / 5))
                low = min(previous, close) * (.92 if i % 131 == 0 else .996)
                writer.writerow(dict(open_time=t, open=previous, high=max(previous, close) * 1.004,
                                     low=low, close=close, close_time=t + INTERVAL_MS - 1))
                previous = close
    (directory / 'SYNTHETIC').write_text('Synthetic OHLC fixtures. NOT market data.\n')
    print(f'SYNTHETIC: {count} candles per symbol in {directory}')


if __name__ == '__main__':
    main()
