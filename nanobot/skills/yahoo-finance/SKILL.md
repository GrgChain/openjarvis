---
name: yahoo-finance
description: Use when the user requests financial news or real-time stock quotes from Yahoo Finance. Supports news search by keyword/ticker and batch stock quote fetching (price, change, volume, market cap, PE, 52-week range, extended hours). No API key required.
metadata: {"nanobot":{"emoji":"📰","requires":{"bins":["python"]}}}
---

# Yahoo Finance News & Quotes

Fetch latest financial news and real-time stock quotes from Yahoo Finance.

---

## 1. 新闻 — `yahoo_finance_news.py`

Fetch latest financial news with automatic retry and batch support.

### Usage

**Single query:**
```bash
python scripts/yahoo_finance_news.py --query <KEYWORD> [--limit <NUMBER>]
```

**Batch mode:**
```bash
python scripts/yahoo_finance_news.py --queries <KEYWORD1> <KEYWORD2> ... [--limit <NUMBER>]
```

### Options

- `--query`: Single search keyword or stock ticker (default: "stock market")
- `--queries`: Multiple keywords for batch fetching
- `--limit`: Max news items per query (default: 20)
- `--json`: Output raw JSON format
- `-v, --verbose`: Show progress messages in batch mode

### Examples

```bash
# Default query
python scripts/yahoo_finance_news.py

# Single query with limit
python scripts/yahoo_finance_news.py --query "Elon Musk" --limit 10

# Batch mode with progress
python scripts/yahoo_finance_news.py --queries AAPL TSLA NVDA "AI stocks" --limit 5 -v

# JSON output for parsing
python scripts/yahoo_finance_news.py --query AAPL --json
```

### Features

- Automatic retry on network errors (2 retries with 1s delay)
- Batch mode with rate limiting (0.3s between requests)
- Progress indicator for batch queries
- JSON output option for programmatic use

---

## 2. 实时行情 — `yahoo_finance_quote.py`

Fetch real-time stock quotes with cookie/crumb authentication and caching.

### Usage

```bash
python scripts/yahoo_finance_quote.py <SYMBOL1> [SYMBOL2] ... [--json]
```

### Options

- `--json`: Output raw JSON format

### Output Fields

价格、涨跌额、涨跌幅、开盘、最高、最低、昨收、成交量、均量、市值、PE、远期PE、EPS、股息率、52周高低、盘前/盘后行情、市场状态。

### Examples

```bash
# Single stock
python scripts/yahoo_finance_quote.py AAPL

# Multiple stocks
python scripts/yahoo_finance_quote.py AAPL MSFT GOOGL AMZN NVDA META TSLA

# US major indices
python scripts/yahoo_finance_quote.py ^DJI ^GSPC ^IXIC

# JSON output
python scripts/yahoo_finance_quote.py AAPL TSLA --json
```

### Features

- Cookie/crumb authentication with 5-minute cache
- Automatic retry on failures (2 retries with 1s delay)
- Extended hours data (pre-market and post-market)
- Batch quote fetching (multiple symbols in one request)
- Human-readable number formatting (T/B/M suffixes)

---

## Review Output

- **News**: Headline, publisher, time, related tickers, URL
- **Quotes**: Price, change, OHLC, volume, market cap, PE, 52-week range, extended hours
