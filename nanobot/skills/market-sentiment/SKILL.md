---
name: market-sentiment
description: Use when the user requests to analyze, fetch, or summarize market sentiment data for a specific stock (e.g., ARBR indicator, turnover rate, market heat, margin trading limit up/down). Requires a 6-digit stock symbol.
---

# Market Sentiment Analysis Skill

Follow these instructions to retrieve and analyze market sentiment for individual stocks using Tushare Pro.

## Execute Sentiment Script

Run the `scripts/market_sentiment.py` script to perform the data fetching and analysis. Ensure the `TUSHARE_TOKEN` environment variable is set.

### Usage

```bash
python scripts/market_sentiment.py --symbol <STOCK_CODE> [--data-dir <DIR>]
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.
- `--data-dir`: Directory containing local stock K-line CSV files (for backfilling ARBR data). Default: `kline_data`

### Examples

Analyze Ping An Bank (000001):
```bash
python scripts/market_sentiment.py --symbol 000001
```

Analyze using specific local K-line data directory:
```bash
python scripts/market_sentiment.py --symbol 000001 --data-dir ./my_custom_kline_dir
```

## Review Output

The script outputs a structured Chinese text report detailing various market sentiment indicators (ARBR, Turnover, Limit Up/Down, etc.) directly to the console. Read this output and use it to answer the user's questions or generate insights.
