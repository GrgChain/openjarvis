---
name: news-sentiment
description: Use when the user requests to fetch, collect, or summarize the latest stock-specific news and telegraphs. It aggregates real-time news from major financial platforms like East Money, Sina Finance, and Cailian Press. Requires a 6-digit stock symbol.
---

# News Sentiment Skill

Follow these instructions to retrieve the latest news and telegraphs for a specific stock.

## Execute News Fetch Script

Run the `scripts/news_sentiment.py` script to fetch aggregated news items.

### Usage

```bash
python scripts/news_sentiment.py --symbol <STOCK_CODE> [--limit <NUMBER>]
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.
- `--limit`: Maximum number of news items to fetch. Default: `30`

### Examples

Fetch latest 30 news items for Ping An Bank (000001):
```bash
python scripts/news_sentiment.py --symbol 000001
```

Fetch only the top 10 news items for a quicker summary:
```bash
python scripts/news_sentiment.py --symbol 000001 --limit 10
```

## Review Output

The script outputs a structured Chinese text report detailing the latest news items, including the headline, publication date/time, source platform, abstract, and original URL. Use this information to summarize recent market events or assess information-level sentiment.
