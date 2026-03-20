# 一、增加定时任务（超短形态选股）
创建定时任务：工作日 19:10 自动执行【超短趋势扫描】，筛选明日10只备选标的。
```
【超短形态扫描任务】工作日 19:10 执行

1. 调用 `uptrend-scanner` 技能：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/uptrend-scanner/scripts/scan_uptrend.py --date today --out /root/.nanobot/workspace/uptrend_picks/ --top 10
2. 技术验证：检查产生的 `picks_YYYYMMDD.json` 是否包含具备 MA5/MA10/MA20 多头排列的强势股。
3. 日志记录：保存分析结果至 `/root/.nanobot/workspace/trading_log/uptrend_scan_YYYYMMDD.md`。
```

# 二、增加定时任务（超短线波段策略）
创建定时任务：工作日 9:40, 10:30, 13:30, 14:40 自动执行【超短线波段】持仓滚动评估与新仓位介入。

【雪球超短波段策略】作业流程：
1. **日内监控与评估 (Intraday Monitoring)**：
   - 在 9:40, 10:30, 13:30 重点执行持仓监控，检查是否触发基础止损（-5%）或止盈（3%）。
   - 在 14:40 作为核心决策点，除止损止盈外，从 `uptrend_picks` 中筛选新标的。
2. **备选调取 (High-Velocity Picks)**：
   - 读取 `uptrend_picks/picks_YYYYMMDD.json` (或前一交易日 Picks)。
3. **共振审查 (Expert Synthesis)**：
   - 调用 `investment-decision` 对标的进行多专家合议，优先选择“BUY/ACCUMULATE”评级且资金流向为正的标的。
4. **持仓滚动审计 (Portfolio Review)**：
   - **超短时间止损 (Time Stop)**：识别持仓满 **2 个交易日**且浮动盈亏在 [-1%, +1%]（无波动/弱势）的标的，强制释放流动性。
   - **硬性止损 (Stop Loss)**：有效跌破 MA20 或浮亏达到 -5% 时无条件离场。
5. **获利退出 (Take Profit)**：
   - **分步止盈**：单票盈利达 3%-5% 时执行减仓（锁利 50%）。
   - **动能衰竭**：若股价偏离五日线过远或 RSI > 80，实行动态止盈。
6. **执行操作 (Execution)**：
   - 使用 `snowball-trading` 执行 `buy/sell/adjust`。
   - **仓位管理**：单票上限 10%，总仓位严格对齐 75% 红线。
7. **归档记录**：记录分析及损益预设至 `/root/.nanobot/workspace/trading_log/ultra_short_YYYYMMDD.md`。

# 三、增加定时任务（复盘）
创建定时任务：工作日17点自动雪球持仓复盘，分析持仓情况，今天交易操作，明天预期判断和风险，复盘结果记录到工作区daily_review文件夹以md文件保存，同时发送到飞书
```
执行雪球持仓复盘任务：
1) 查询雪球持仓和资金情况；
2) 分析持仓盈亏、行业分布；
3) 回顾今日交易操作；
4) 结合市场情况判断明天预期和风险；
5) 将复盘报告保存到 /root/.nanobot/workspace/daily_review/daily_review_YYYYMMDD.md；
6) 发送复盘结果到飞书
```

# 四、增加定时任务（K线数据）
创建定时任务：工作日19点自动更新今天A股K线数据
```
【自动更新A股K线数据】获取今日收盘数据

任务步骤：
1. 执行K线数据获取脚本，增量更新今日数据：
   - 运行：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/fetch-kline/scripts/fetch_kline.py --start today --end today --out /root/.nanobot/workspace/kline_data
   - 优先使用Tushare API（如已配置TUSHARE_TOKEN）
   - 无token时自动降级使用AKShare（免费）
2. 记录更新日志到 /root/.nanobot/workspace/trading_log/kline_update_YYYYMMDD.md：
   - 更新时间和数据来源（Tushare/AKShare）
   - 更新的股票数量
   - 任何错误或异常情况
3. 验证数据完整性：
   - 检查今日数据是否成功写入
   - 确保CSV文件格式正确

注意：
- A股收盘时间为15:00，19点执行可确保数据已同步
- 使用增量更新（today模式）避免重复下载历史数据
- 数据保存在 workspace/kline_data 目录
```