---
name: fund-flow
description: Use when the user requests to analyze, fetch, or summarize individual stock fund flow data, including net inflows/outflows of main force (主力), super large (超大), large (大), medium (中), and small (小) orders. Requires a 6-digit stock symbol.
metadata: {"nanobot":{"emoji":"💹","requires":{"bins":["python"]}}}
---

# Fund Flow Analysis Skill

Follow these instructions to retrieve and analyze the fund flow data for individual stocks using Tushare Pro.

## Execute Fund Flow Script

Run the `scripts/fund_flow.py` script to perform the data fetching and analysis. Ensure the `TUSHARE_TOKEN` environment variable is set.

### Usage

```bash
python scripts/fund_flow.py --symbol <STOCK_CODE> [--days <DAYS>]
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.
- `--days`: Number of recent trading days to analyze. Default: `30`

### Examples

Analyze Ping An Bank (000001) for the default 30 days:
```bash
python scripts/fund_flow.py --symbol 000001
```

Analyze recent 60 trading days:
```bash
python scripts/fund_flow.py --symbol 000001 --days 60
```

## Review Output

The script outputs a structured Chinese text report detailing daily fund flows and statistical summaries directly to the console. Read this output and use it to answer the user's questions or generate insights.
