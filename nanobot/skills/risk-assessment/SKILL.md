---
name: risk-assessment
description: Use when the user requests to fetch, assess, or check specific risk data for a stock, including upcoming lifting bans (限售解禁), recent shareholder reductions (大股东减持), and important corporate events (重要事件). Requires a 6-digit stock symbol.
metadata: {"nanobot":{"emoji":"⚠️","requires":{"bins":["python"]}}}
---

# Risk Assessment Skill

Follow these instructions to retrieve stock risk profiles using the iFind/Wencai backend (`pywencai`).

## Execute Risk Assessment Script

Run the `scripts/risk_assessment.py` script to fetch multi-dimensional risk data.

### Usage

```bash
python scripts/risk_assessment.py --symbol <STOCK_CODE>
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.

### Examples

Check risk parameters for Ping An Bank (000001):
```bash
python scripts/risk_assessment.py --symbol 000001
```

## Review Output

The script outputs a structured Chinese text report detailing any pending lifting bans, shareholder reductions, and significant company events. Use this output to summarize potential short-term constraints or liquidity pressures on the given stock.
