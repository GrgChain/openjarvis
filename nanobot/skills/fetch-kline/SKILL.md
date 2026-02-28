---
name: fetch-kline
description: Use when the user requests to fetch, download, or sync historical daily K-line (candlestick) data for Chinese stocks (A-shares) using the Tushare API. Supports incremental updates and filtering out specific boards (e.g., ChiNext/gem, STAR market).
---

# Fetch Kline Data

Follow these instructions to fetch daily K-line data for Chinese stocks.

## Execute Fetch Script

Run the `scripts/fetch_kline.py` script to perform the data fetching. Ensure the `TUSHARE_TOKEN` environment variable is set.

### Options

- `--start`: Start date (YYYYMMDD) or 'today'. Default: `20200101`
- `--end`: End date (YYYYMMDD) or 'today'. Default: `today`
- `--exclude-boards`: Space-separated list of boards to exclude (`gem`, `star`, `bj`). Default: None
- `--out`: Output directory for the generated CSV files. Default: `kline_data`
- `--workers`: Number of concurrent download threads. Default: `6`

### Examples

Fetch data for all stocks (incremental update):
```bash
python3 scripts/fetch_kline.py
```

Fetch data from 2023-01-01 to today, excluding GEM and STAR boards:
```bash
python3 scripts/fetch_kline.py --start 20230101 --exclude-boards gem star
```

Save data to a specific directory:
```bash
python3 scripts/fetch_kline.py --out ./my_custom_kline_dir
```

## Check Output

The script generates CSV files (one per stock) in the specified `--out` directory.
Each CSV contains the following columns: `date`, `open`, `close`, `high`, `low`, `volume`.
