【全球市场简报】获取并生成全球市场分析报告

【全球市场简报-每日8点】获取并生成全球市场分析报告：
1. 获取关键人物新闻（Sam Altman, Greg Brockman, Elon Musk, Donald Trump, Sundar Pichai, Tim Cook, Jensen Huang, Jerome Powell, Mark Zuckerberg），每人最新2篇
2. 获取美股核心标的实时行情：AAPL GOOGL AMZN NVDA META TSLA COHR MU WDC MSFT
3. 综合所有新闻和行情数据，生成结构化分析报告（包含关键人物动态、美股行情、板块影响评估5级评分、综合建议）
4. 将报告保存到工作区下的reports/global-market-brief-YYYY-MM-DD.md
报告格式要求：中文输出，包含AI/大模型、半导体/芯片、云计算/SaaS、消费电子、新能源/电动车、存储/HBM、社交/广告、宏观/利率等板块的影响评估



创建雪球模拟盘做T策略定时任务 9:45 10:15 10:45 11:15 13:45 14:15

【雪球做T策略】执行任务：
1. 读取今天的全球市场简报报告（/root/.nanobot/workspace/global-market-brief/reports/global-market-brief-YYYYMMDD.md）作为今日基调
2. 执行做T策略扫描：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/intraday-t-trading/scripts/t_trading_scanner.py --json
3. 结合全球市场简报和扫描结果，生成做T策略报告（包含正T/倒T信号、风险提示、仓位建议），保存到/root/.nanobot/workspace/t-trading-report/t-trading-report-YYYYMMDD-hhmm.md
4. 根据做T策略报告中的LONG/SHORT信号，在雪球模拟盘上执行相应做T操作（使用snowball-trading skill的adjust/buy/sell命令）
5. 严格遵守做T策略报告中的时间窗口：
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
6. 保存操作日志到 /root/.nanobot/workspace/trading-log/t-trading-YYYYMMDD-hhmm.md


