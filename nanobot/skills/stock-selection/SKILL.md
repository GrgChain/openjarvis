---
name: stock-selection
description: Use when the user requests to run quantitative stock selection strategies or identify potential trading opportunities based on technical analysis (e.g., BBI, KDJ, MA60, Volume).
metadata: {"nanobot":{"emoji":"🔍","requires":{"bins":["python"]}}}
---

# Stock Selection Skill

Follow these instructions to execute systematic technical strategies and scan for stock picks.

## Execute Strategy Scanner

Run the `scripts/select_stock.py` script. The script automatically loads available strategies and parameters from `scripts/configs.json`.

### Usage

```bash
python scripts/select_stock.py [--date <YYYY-MM-DD>] [--tickers <TICKERS>] [--data-dir <DIR>]
```

### Options

- `--data-dir`: Directory containing pre-fetched K-line CSV files. Default: `kline_data`
- `--date`: The specific trade date to analyze (YYYY-MM-DD). Default: latest date available in the data files.
- `--tickers`: Comma-separated list of stock codes to scan, or `all`. Default: `all`
- `--out`: Output directory for strategy results. Default: `stock_picks`

### Examples

Scan all stocks on the latest date using default paths:
```bash
python scripts/select_stock.py
```

Scan all stocks for a specific date (e.g., 2026-02-06):
```bash
python scripts/select_stock.py --date 2026-02-06
```

## Review Output

The script outputs matching stock codes for each active strategy directly to the console. Results are also saved to `stock_picks/picks_<DATE>.json` as a dictionary mapping strategy names to lists of selected stock symbols. You can use these arrays to perform further downstream queries (like fund-flow or news-sentiment filtering) or present them directly to the user.
