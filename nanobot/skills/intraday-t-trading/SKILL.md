---
name: intraday-t-trading
description: Execute intraday T-trading (做T) strategies for tech stocks. Use when the user requests to perform day trading, scalp trading, or intraday buy-low-sell-high operations on volatile tech stocks (CPO, semiconductor, optics). Provides signal generation, position sizing, risk management, and execution checklists for both "正T" (buy-first) and "倒T" (sell-first) operations.
metadata: {"nanobot":{"emoji":"📈","requires":{"bins":["python"],"env":["TUSHARE_TOKEN"]},"stocks":["300308","688205","688195","300620","300757","688313","688498","688048","000988","002281","603986","688008","300456","600330","688025","000021"]}}
---

# 科技股做T交易策略 (Tech Stock Intraday T-Trading)

本Skill为光通信/CPO和半导体板块16只核心科技股提供日内做T策略框架。
股票池、指标阈值、仓位规则等参数见 `configs.json`。

## 买入信号 (正T - Buy First)

必须同时满足:
1. **KDJ超卖**: J值 < oversold_buy
2. **价格位置**: 股价 ≤ BOLL下轨 × lower_buy_ratio 或触碰MA30支撑
3. **量能确认**: 量比 < contraction_threshold (缩量回调)
4. **大盘环境**: 涨跌家数比 > 1:2
5. **时间窗口**: 10:00-10:30 或 13:30-14:00

## 卖出信号 (倒T - Sell First)

必须同时满足:
1. **KDJ超买**: J值 > overbought_sell
2. **价格位置**: 股价 ≥ BOLL上轨 × upper_sell_ratio 或触碰前高压力
3. **量能异常**: 量比 > expansion_threshold (放量滞涨)
4. **持仓状态**: 已有盈利

买回条件: 价格回落1.5%-2%，或J值<30，或触及BOLL下轨

## 风险控制

- 正T止损: -1.5%，立即止损，当日不再做T该标的
- 倒T止损: +2.0%，放弃买回，保留现金
- 当日总亏损 >3%: 停止所有做T
- 连续错误3次: 暂停策略，复盘调整

### 禁止做T条件
- 财报/重大事件前3天
- 股价位于MA60下方
- 当日板块跌幅 > 3%
- 个股低开 > 4%
- 涨跌停板附近
- 成交量萎缩至近期20%以下

## 执行流程

需要设置 `TUSHARE_TOKEN` 环境变量，数据通过 tushare pro API 实时获取。

```bash
# 扫描所有关注标的
python scripts/t_trading_scanner.py

# 扫描特定标的
python scripts/t_trading_scanner.py --symbol 300308
```

### 盘中时间窗口

| 时间段 | 操作 | 说明 |
|-------|------|------|
| 9:30-10:00 | 观察 | 避免开盘波动 |
| 10:00-10:30 | 正T/倒T | 第一黄金窗口 |
| 10:30-13:30 | 观察 | 少操作 |
| 13:30-14:00 | 正T/倒T | 第二黄金窗口 |
| 14:00-14:30 | 减仓 | 逐步降低仓位 |
| 14:30后 | 禁止新开 | 只平仓 |

## 快速口诀

**正T**: J值25下缩量买，下轨附近入两点卖，一点五止损纪律牢
**倒T**: J值80上放量卖，两点买回不追高，突破两放弃现金王
**停手**: 大盘跌超2%全停，个股跌停不碰，连错三把先冷静，尾盘半小时不新开
