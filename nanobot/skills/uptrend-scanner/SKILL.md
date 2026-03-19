---
name: uptrend-scanner
description: Use when the user asks to find stocks in an uptrend, scan for trending-up stocks, or identify bullish-trending A-share securities based on technical indicators (MA alignment, MACD, slope, volume-price). 当用户要求筛选上升趋势股票、寻找趋势向上标的时触发。
metadata: {"nanobot":{"emoji":"📈","requires":{"bins":["python"]}}}
---

# Uptrend Scanner（上升趋势股票筛选）

扫描本地 K 线数据，基于多维度技术指标综合评分，筛选出处于上升趋势的股票。

## Run

```bash
python3 scripts/uptrend_scanner.py [--data-dir <DIR>] [--tickers <TICKERS>] [--min-score <N>] [--top <N>]
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--data-dir` | K 线 CSV 数据目录 | `kline_data` |
| `--tickers` | `all` 或逗号分隔的股票代码 | `all` |
| `--min-score` | 最低趋势评分（0-100） | `60` |
| `--top` | 返回前 N 只股票（0 = 不限） | `20` |
| `--output` | 输出文件路径 | `uptrend_<YYYY-MM-DD>.json` |

## Scoring Dimensions

| 维度 | 权重 | 说明 |
|------|------|------|
| 均线多头排列 | 25% | MA5 > MA10 > MA20 > MA60 |
| 价格站上均线 | 20% | 收盘价 > MA20 且 > MA60 |
| 均线斜率 | 20% | MA20 / MA60 最近 N 日斜率为正 |
| MACD 趋势 | 20% | DIF > 0，DIF > DEA，MACD 柱为正 |
| 量价配合 | 15% | 上涨日放量、下跌日缩量 |

**趋势等级：**
- `≥ 80`：🔥 强上升趋势
- `60-79`：📈 上升趋势
- `40-59`：➡️ 震荡偏多
- `< 40`：不输出

## Example Output

```json
{
  "date": "2026-03-18",
  "count": 2,
  "min_score": 60,
  "stocks": [
    {
      "code": "600519",
      "score": 85.0,
      "tier": "强上升趋势",
      "ma_alignment": 100.0,
      "price_above_ma": 100.0,
      "ma_slope": 80.0,
      "macd_trend": 75.0,
      "volume_price": 70.0,
      "tags": ["均线多头", "MACD金叉", "量价齐升"]
    },
    {
      "code": "000858",
      "score": 68.5,
      "tier": "上升趋势",
      "ma_alignment": 75.0,
      "price_above_ma": 100.0,
      "ma_slope": 60.0,
      "macd_trend": 50.0,
      "volume_price": 55.0,
      "tags": ["价格站上MA60"]
    }
  ]
}
```

## Use In Analysis

当用户询问"哪些股票处于上升趋势"或"帮我找趋势向上的股票"：
1. 确保已有最新 K 线数据（可先执行 `fetch-kline` skill）
2. 运行 `uptrend_scanner.py`
3. 按 `score` 降序展示结果，包含趋势等级和信号标签
4. 可结合 `fund-flow`、`news-sentiment` 等 skill 做进一步分析
