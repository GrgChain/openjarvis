---
name: miniqmt-trading
description: MiniQMT量化交易开发技能，基于迅投XtQuant库提供行情数据获取(xtdata)和交易执行(xttrader)功能。用于开发股票、期货、期权等量化交易策略，支持历史/实时行情数据下载、K线/分笔数据获取、财务数据查询、自动下单/撤单、持仓查询、资产查询等。适用于需要连接MiniQMT客户端进行量化交易的场景。
metadata: {"nanobot":{"emoji":"🤖","requires":{"bins":["python"]}}}
---

# MiniQMT 量化交易开发指南

## 概述

MiniQMT是基于迅投QMT的极简量化交易终端，通过XtQuant Python库提供行情和交易API。

**运行依赖：**
- 已安装MiniQMT客户端并启动
- Python 3.6-3.12 (64位)
- 安装xtquant库

**核心模块：**
- `xtdata` - 行情数据模块：K线、分笔、财务数据、合约信息等
- `xttrader` - 交易模块：下单、撤单、查询、主推消息

## 快速开始

### 1. 行情数据获取

```python
from xtquant import xtdata

# 下载历史数据（必须先下载才能获取）
xtdata.download_history_data('600000.SH', period='1d', start_time='20240101')

# 获取行情数据
data = xtdata.get_market_data(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['600000.SH'],
    period='1d',
    start_time='20240101',
    count=-1
)
```

### 2. 交易功能

```python
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

# 初始化交易对象
path = 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini'
session_id = 123456
xt_trader = XtQuantTrader(path, session_id)

# 创建账号
acc = StockAccount('1000000365')  # 资金账号

# 注册回调并启动
callback = MyXtQuantTraderCallback()
xt_trader.register_callback(callback)
xt_trader.start()
xt_trader.connect()
xt_trader.subscribe(acc)

# 下单
order_id = xt_trader.order_stock(
    acc, '600000.SH', xtconstant.STOCK_BUY, 
    100, xtconstant.FIX_PRICE, 10.5
)
```

## 详细功能参考

### 行情模块 (xtdata)

详见 [references/market_data.md](references/market_data.md)

**主要功能：**
- 历史K线数据下载/获取 (`download_history_data`, `get_market_data`)
- 实时行情订阅 (`subscribe_quote`, `subscribe_whole_quote`)
- 分笔数据获取 (`get_full_tick`)
- 财务数据下载/获取 (`download_financial_data`, `get_financial_data`)
- 板块/行业数据 (`download_sector_data`, `get_stock_list_in_sector`)
- 合约基础信息 (`get_instrument_detail`)

### 交易模块 (xttrader)

详见 [references/trading.md](references/trading.md)

**主要功能：**
- 同步/异步下单 (`order_stock`, `order_stock_async`)
- 撤单 (`cancel_order_stock`)
- 资产查询 (`query_stock_asset`)
- 持仓查询 (`query_stock_positions`, `query_stock_position`)
- 委托查询 (`query_stock_orders`, `query_stock_order`)
- 成交查询 (`query_stock_trades`)
- 主推消息回调 (`on_stock_order`, `on_stock_trade`等)

## 常用常量

### 委托类型 (xtconstant)

```python
# 股票
STOCK_BUY = 23      # 买入
STOCK_SELL = 24     # 卖出

# 期货
FUTURE_OPEN_LONG = 0    # 开多
FUTURE_CLOSE_LONG_TODAY = 1   # 平今多
FUTURE_CLOSE_LONG_HISTORY = 2 # 平昨多
FUTURE_OPEN_SHORT = 3     # 开空
FUTURE_CLOSE_SHORT_TODAY = 4  # 平今空
FUTURE_CLOSE_SHORT_HISTORY = 5 # 平昨空
```

### 报价类型

```python
FIX_PRICE = 11      # 指定价
LATEST_PRICE = 5    # 最新价
```

### 委托状态

```python
ORDER_UNREPORTED = 48       # 未报
ORDER_REPORTED = 50         # 已报
ORDER_PART_SUCC = 55        # 部成
ORDER_SUCCEEDED = 56        # 已成
ORDER_CANCELED = 54         # 已撤
ORDER_JUNK = 57             # 废单
```

## 示例代码

详见 [scripts/](../scripts/) 目录：

- `market_data_demo.py` - 行情数据获取示例
- `trading_demo.py` - 交易功能示例
- `data_download.py` - 批量数据下载示例

## 注意事项

1. **数据下载**：使用`get_market_data`前必须先调用`download_history_data`下载数据到本地
2. **订阅限制**：单股订阅数量建议不超过50，更多请使用全推订阅
3. **路径配置**：券商版指向`userdata_mini`，投研版指向`userdata`
4. **session_id**：不同策略使用不同的会话编号
5. **回调处理**：交易回调中调用同步查询需开启`set_relaxed_response_order_enabled`

## 数据字典速查

### 合约代码格式

- 股票：`000001.SZ`, `600000.SH`
- 期货：`rb2405.SF`, `IF2403.IF`
- 期权：`510050.SH` (ETF期权), `sc2403C465.INE` (商品期权)

### 周期类型

- `tick` - 分笔数据
- `1m`, `5m`, `15m`, `30m`, `1h` - 分钟/小时线
- `1d`, `1w`, `1mon`, `1q`, `1hy`, `1y` - 日/周/月/季/半年/年线

### 除权方式

- `none` - 不复权
- `front` - 前复权
- `back` - 后复权
- `front_ratio` - 等比前复权
- `back_ratio` - 等比后复权
