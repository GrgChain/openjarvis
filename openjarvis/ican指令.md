创建定时任务：工作日9点45分上午自动分析当前雪球持仓并调仓：关注高开的股票，获利很多可减仓实现部分获利，但不执行买入操作，把操作日志记录到工作区trading_log文件夹以md文件保存
```
【雪球自动调仓任务-9点45分】分析持仓并执行获利减仓

任务步骤：
1. 查询雪球当前持仓（使用snowball-trading skill的position命令）
2. 获取持仓股票的实时行情，识别高开股票（涨幅>3%视为高开）
3. 分析各持仓股票的获利情况：
   - 计算每只持仓股票的浮动盈亏比例
   - 获利超过10%的股票视为"获利很多"
4. 执行调仓策略（仅减仓，不买入）：
   - 对于获利很多且高开的股票，减仓50%实现部分获利
   - 使用adjust命令将目标仓位权重降低
5. 记录操作日志到 /root/.nanobot/workspace/trading_log/YYYY-MM-DD.md 文件，包含：
   - 任务执行时间
   - 持仓分析结果
   - 高开股票列表
   - 执行的操作详情
   - 调仓后的持仓状态

注意事项：
- 雪球是T+1交易，注意今日买入的股票不能卖出
- 只执行减仓操作，不执行任何买入
- 确保日志文件以markdown格式保存
```

创建定时任务：工作日10点50分上午自动分析当前雪球持仓并调仓：检查持仓股票风险，卖出不利持仓，买入新的昨天推荐股票，把操作日志记录到工作区trading_log文件夹以md文件保存
```
【雪球自动调仓任务-10点50分】风险检查与买入推荐股票

任务步骤：
1. 查询雪球当前持仓（使用snowball-trading skill的position和balance命令）
2. 检查持仓股票风险（使用risk-assessment skill）：
   - 查询每只持仓股票的限售解禁、大股东减持、重要事件
   - 识别风险较高的持仓（如有重大利空、减持计划等）
3. 卖出不利持仓：
   - 对风险较高的股票，使用adjust命令减仓或清仓（设置weight为0）
   - 优先卖出有风险预警的股票
4. 买入昨日投资决策股票：
   - 读取 /root/.nanobot/workspace/decisions/investment_decision_<昨天日期>.json
   - 获取昨日推荐的优质股票列表
   - 计算可用资金，平均分配买入推荐股票（或使用指定权重）
   - 使用buy命令买入，价格设为市价或略低于当前价
5. 记录操作日志到 /root/.nanobot/workspace/trading_log/morning_trade_YYYY-MM-DD.md：
   - 任务执行时间和市场概况
   - 持仓风险检查结果（有风险的股票列表）
   - 卖出的操作详情（股票代码、数量、原因）
   - 买入的操作详情（股票代码、数量、价格）
   - 调仓前后的持仓对比
   - 账户资金变化

注意事项：
- 雪球是T+1交易，今日买入的股票次日才能卖出
- 卖出操作优先于买入，确保有足够资金
- 如果昨日没有推荐股票文件，则跳过买入步骤
- 确保日志文件以markdown格式保存，便于查阅

```

创建定时任务：工作日14点30分中午自动分析当前雪球持仓并调仓：检查持仓股票风险，卖出不利持仓，买入新的昨天推荐股票，把操作日志记录到工作区trading_log文件夹以md文件保存
```
【雪球自动调仓任务-14点30分】风险检查与买入推荐股票

任务步骤：
1. 查询雪球当前持仓（使用snowball-trading skill的position和balance命令）
2. 检查持仓股票风险（使用risk-assessment skill）：
   - 查询每只持仓股票的限售解禁、大股东减持、重要事件
   - 识别风险较高的持仓（如有重大利空、减持计划、解禁等）
3. 卖出不利持仓：
   - 对风险较高的股票，使用adjust命令清仓（设置weight为0）
   - 对当日表现异常（如大跌超过5%）的股票，考虑减仓
4. 买入昨日投资决策股票：
   - 读取 /root/.nanobot/workspace/decisions/investment_decision_<昨天日期>.json
   - 获取昨日推荐的优质股票列表
   - 计算可用资金，平均分配买入推荐股票
   - 使用buy命令买入，价格设为市价或根据推荐价格
5. 记录操作日志到 /root/.nanobot/workspace/trading_log/afternoon_trade_YYYY-MM-DD.md：
   - 任务执行时间和市场概况
   - 持仓风险检查结果（有风险的股票列表及原因）
   - 卖出的操作详情（股票代码、数量、卖出原因）
   - 买入的操作详情（股票代码、数量、价格）
   - 调仓前后的持仓对比
   - 账户资金变化和收益率

注意事项：
- 雪球是T+1交易，今日买入的股票次日才能卖出
- 卖出操作优先于买入，确保有足够资金
- 如果昨日没有推荐股票文件，则跳过买入步骤
- 14:30接近收盘，交易决策需谨慎
- 确保日志文件以markdown格式保存
```

创建定时任务：工作日16点自动更新今天A股K线数据
```
【自动更新A股K线数据】获取今日收盘数据

任务步骤：
1. 执行K线数据获取脚本，增量更新今日数据：
   - 运行：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/fetch-kline/scripts/fetch_kline.py --start today --end today --out /root/.nanobot/workspace/kline_data
   - 优先使用Tushare API（如已配置TUSHARE_TOKEN）
   - 无token时自动降级使用AKShare（免费）
2. 记录更新日志到 /root/.nanobot/workspace/trading_log/kline_update_YYYY-MM-DD.md：
   - 更新时间和数据来源（Tushare/AKShare）
   - 更新的股票数量
   - 任何错误或异常情况
3. 验证数据完整性：
   - 检查今日数据是否成功写入
   - 确保CSV文件格式正确

注意：
- A股收盘时间为15:00，16点执行可确保数据已同步
- 使用增量更新（today模式）避免重复下载历史数据
- 数据保存在 workspace/kline_data 目录
```

创建定时任务：工作日17点自动执行今天量化策略选股，生成今日推荐股票
```
【量化策略选股】生成今日推荐股票

任务步骤：
1. 执行选股策略扫描（基于16点已更新的K线数据）：
   - 运行：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/stock-selection/scripts/select_stock.py --data-dir /root/.nanobot/workspace/kline_data --out /root/.nanobot/workspace/stock_picks --date today
   - 默认使用多策略组合（BBI、KDJ、MA60、成交量等技术指标）
   - 自动扫描全部A股股票
2. 验证选股结果：
   - 检查输出文件 /root/.nanobot/workspace/stock_picks/picks_今天日期.json 是否生成
   - 统计各策略选出的股票数量
3. 记录选股日志到 /root/.nanobot/workspace/trading_log/stock_selection_YYYY-MM-DD.md：
   - 选股执行时间和数据日期
   - 各策略选股结果统计
   - 推荐股票代码列表
   - 选股策略参数说明

依赖：
- 需要16点的K线数据更新任务已成功执行
- 数据源来自 workspace/kline_data 目录

注意：
- 选股结果供次日10:50的调仓任务使用
- JSON文件格式：{"策略名": ["股票代码1", "股票代码2", ...]}
```

创建定时任务：工作日18点自动分析今日选股结果，生成至少10只强势板块的股票投资决策分析
```
【投资决策分析】强势板块选股深度分析

任务步骤：

**第一步：强势板块分析**
- 运行：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/sector-strength/scripts/score_sectors.py --top 20 --min-score 60
- 获取当日强势板块排名（>=75分强势，60-74分偏强）
- 输出保存到：/root/.nanobot/workspace/sector/sector_strength_YYYYMMDD.json

**第二步：量化选股扫描**
- 运行：python3 /usr/local/lib/python3.12/site-packages/nanobot/skills/stock-selection/scripts/select_stock.py --date today --out stock_picks
- 获取技术面选股结果（BBI、KDJ、MA60、放量等策略）
- 输出保存到：/root/.nanobot/workspace/stock_picks/picks_YYYYMMDD.json

**第三步：筛选强势板块股票池（至少10只）**
- 从选股结果中筛选属于强势板块的股票
- 如果数量不足10只，扩大至偏强板块或增加技术面选股范围
- 生成候选股票列表（至少10只）

**第四步：深度投资决策分析（对每只股票）**
对每个候选股票调用多专家分析：
1. risk-assessment - 风险检查（解禁、减持、重大事件）
2. quarterly-report - 基本面分析（业绩增长、估值PE/PB）
3. news-sentiment - 消息面分析（利好/利空、市场关注度）
4. fund-flow - 资金流向分析（主力进出、吸筹/派发）
5. technical-analysis-calculator - 技术面分析（趋势、动量、支撑压力）
6. market-sentiment - 市场情绪分析（赚钱效应、涨跌停、连板）

**第五步：综合投资决策**
- 模拟多空辩论，综合六大专家观点
- 作为CIO做出最终决策：BUY/ACCUMULATE/HOLD/REDUCE/SELL
- 生成投资评级、置信度、操作建议、目标价、止损位

**第六步：输出结果**
- 投资决策JSON：/root/.nanobot/workspace/decisions/investment_decision_YYYYMMDD.json
- 分析日志：/root/.nanobot/workspace/trading_log/investment_analysis_YYYYMMDD.md
- 包含：选股列表、板块分析、各股决策详情、风险提示

注意事项：
- 确保TUSHARE_TOKEN已配置（提升数据质量）
- 如遇到高风险股票（解禁/减持），直接否决
- 优先选择强势板块+资金流入+技术突破的股票
- 日志记录完整的分析过程和决策依据
```

创建定时任务：工作日20点自动雪球持仓复盘，分析持仓情况，今天交易操作，明天预期判断和风险，复盘结果记录到工作区daily_review文件夹以md文件保存，同时发送到飞书
```
执行雪球持仓复盘任务：
1) 查询雪球持仓和资金情况；
2) 分析持仓盈亏、行业分布；
3) 回顾今日交易操作；
4) 结合市场情况判断明天预期和风险；
5) 将复盘报告保存到 /root/.nanobot/workspace/daily_review/daily_review_YYYY-MM-DD.md；
6) 发送复盘结果到飞书
```