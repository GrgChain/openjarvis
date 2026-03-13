---
name: quarterly-report
description: Use when the user requests to fetch, analyze, or summarize quarterly financial reports (income statement, balance sheet, cash flow, financial indicators) for a specific Chinese A-share stock. Requires a 6-digit stock symbol.
metadata: {"nanobot":{"emoji":"📋","requires":{"bins":["python"]}}}
---

# Quarterly Report Skill

Follow these instructions to retrieve the latest 8-period comprehensive quarterly financial reports for a stock using akshare.

## Execute Quarterly Report Script

Run the `scripts/quarterly_report_data.py` script to fetch all related financial tables and indicators.

### Usage

```bash
python scripts/quarterly_report_data.py --symbol <STOCK_CODE>
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.

### Examples

Fetch the latest 8 quarterly reports for Ping An Bank (000001):
```bash
python scripts/quarterly_report_data.py --symbol 000001
```

## Review Output

The script outputs a structured Chinese text report that summarizes the Income Statement, Balance Sheet, Cash Flow Statement, and Key Financial Indicators for the last 8 quarters. Use this comprehensive fundamental dataset to identify financial trends or assist the user with deep-dive analysis.
