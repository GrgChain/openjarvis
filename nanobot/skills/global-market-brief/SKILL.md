---
name: global-market-brief
description: Use when the user requests a comprehensive global market briefing — combines key-figure news from Yahoo Finance, real-time US stock quotes, and an AI-driven sector impact analysis with 5-level bullish/bearish ratings. No API key required.
metadata: {"nanobot":{"emoji":"🌍","requires":{"bins":["python"]}}}
---

# Global Market Brief

Generate a comprehensive market briefing in three steps: fetch key-figure news, pull real-time stock quotes, then synthesize a sector impact analysis.

> [!IMPORTANT]
> This skill depends on `yahoo-finance` skill scripts. All script paths below are relative to the **yahoo-finance** skill directory: `yahoo-finance/scripts/`.

---

## Step 1 — Fetch Key-Figure News

Fetch the latest 2 news articles per person for these influential figures:

```bash
python yahoo-finance/scripts/yahoo_finance_news.py \
  --queries "Sam Altman" "Greg Brockman" "Elon Musk" "Donald Trump" \
            "Sundar Pichai" "Tim Cook" "Jensen Huang" "Jerome Powell" \
            "Mark Zuckerberg" \
  --limit 2 -v
```

Record all headlines and URLs — you will need them for Step 1.5.

---

## Step 1.5 — Summarize Each Article

For **every** article URL returned in Step 1, fetch the full article content and produce a **1-2 sentence Chinese summary**.

Use web fetch to read each URL, then extract the key point. If a URL fails, summarize based on the headline alone.

> [!IMPORTANT]
> This step is critical — the sector analysis in Step 3 depends on understanding the actual content, not just headlines.

---

## Step 2 — Fetch Real-Time Stock Quotes

Pull real-time quotes for 10 key US stocks spanning AI, cloud, semiconductor, consumer tech, and storage:

```bash
python yahoo-finance/scripts/yahoo_finance_quote.py \
  AAPL GOOGL AMZN NVDA META TSLA COHR MU WDC MSFT
```

Record price, change%, market cap, and PE for each.

---

## Step 3 — Sector Impact Analysis

Using **all** news from Step 1 and quotes from Step 2, produce a structured Markdown analysis in Chinese. Follow this format exactly:

```markdown
# 全球市场简报 — <YYYY-MM-DD>

## 一、关键人物动态

（每人列出 2 篇文章，每篇包含标题、来源、日期和 1-2 句中文摘要）

### Sam Altman
1. **标题** — 来源 | 日期
   摘要：……
2. **标题** — 来源 | 日期
   摘要：……

### Greg Brockman
（同上格式，以此类推 9 人）

## 二、美股核心标的行情
（表格：股票 | 价格 | 涨跌幅 | 市值 | PE）

## 三、板块影响评估

对以下板块逐一评估，给出 **利好/利空等级**（5 级）和理由：

| 板块 | 影响方向 | 等级 | 核心逻辑 |
|------|----------|------|----------|
| AI / 大模型 | 利好 ⬆ 或 利空 ⬇ | ⭐⭐⭐⭐⭐ (1-5) | 一句话理由 |
| 半导体 / 芯片 | ... | ... | ... |
| 云计算 / SaaS | ... | ... | ... |
| 消费电子 | ... | ... | ... |
| 新能源 / 电动车 | ... | ... | ... |
| 存储 / HBM | ... | ... | ... |
| 社交 / 广告 | ... | ... | ... |
| 宏观 / 利率 | ... | ... | ... |

### 等级说明
- ⭐：影响极小，可忽略
- ⭐⭐：轻微影响，短期波动
- ⭐⭐⭐：中等影响，值得关注
- ⭐⭐⭐⭐：显著影响，建议调整策略
- ⭐⭐⭐⭐⭐：重大影响，可能改变趋势

## 四、综合建议
（2-3 句总结当前市场状态和操作建议）
```

### Analysis Rules

1. **Every** sector rating must be grounded in specific news from Step 1 — cite the person or event.
2. Cross-reference quotes from Step 2 — if a sector's stocks are already moving in the direction the news implies, increase confidence; if divergent, note the discrepancy.
3. Be concise — the entire output should fit in one screen (~60 lines).
4. Output language: **Chinese**.

---

## Step 4 — Save Report

Save the final Markdown report to a dated file:

```
reports/global-market-brief-<YYYYMMDD>.md
```

Create the `reports/` directory under this skill folder if it does not exist. Always overwrite if the same date file already exists.
