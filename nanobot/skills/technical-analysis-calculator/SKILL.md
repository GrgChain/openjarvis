---
name: technical-analysis-calculator
description: Use when the user requests a calculation or summary of technical analysis indicators (e.g., MA, MACD, KDJ, RSI, Bollinger Bands, Vol) for a specific stock based on local data. Requires a 6-digit stock symbol.
metadata: {"nanobot":{"emoji":"📐","requires":{"bins":["python"]}}}
---

# Technical Analysis Calculator Skill

Follow these instructions to automatically calculate and retrieve a suite of technical analysis metrics for a given stock using local CSV data.

## Execute Indicator Calculator

Run the `scripts/technical_analysis_calculator.py` script. The script calculates major technical indicators including moving averages, MACD, KDJ, RSI, Bollinger Bands, WR, CCI, and BIAS, then outputs the most recent trading day's values.

### Usage

```bash
python scripts/technical_analysis_calculator.py --symbol <STOCK_CODE>
```

### Options

- `--symbol`: Stock symbol (6 digits). Required.
- `--data-dir`: Directory containing stock K-Line CSV files. Default: `kline_data`

### Examples

Calculate indicators for Ping An Bank (000001):
```bash
python scripts/technical_analysis_calculator.py --symbol 000001
```

## Review Output

The script outputs a JSON object containing the latest trading day's technical parameters. Parse this JSON to feed exact numerical indicator thresholds to the agent for further decision-making.