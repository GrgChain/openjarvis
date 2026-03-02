# XtQuant 行情模块 (xtdata) 参考

## 运行逻辑

xtdata提供和MiniQmt的交互接口，本质是和MiniQmt建立连接，由MiniQmt处理行情数据请求，再把结果回传返回到python层。

**关键原则：**
- 对于数据获取接口，使用时需要先确保MiniQmt已有所需要的数据
- 如果数据不足可以通过`download_`接口补充，再调用数据获取接口获取
- 订阅接收到的数据一般会保存下来，同种数据不需要再单独补充

## 接口分类

| 功能 | 接口前缀 | 说明 |
|------|----------|------|
| 订阅 | `subscribe_` | 订阅实时行情 |
| 反订阅 | `unsubscribe_` | 取消订阅 |
| 获取数据 | `get_` | 从缓存获取数据 |
| 下载数据 | `download_` | 下载数据到本地 |

## 行情数据接口

### 下载历史数据

```python
xtdata.download_history_data(
    stock_code='600000.SH',
    period='1d',
    start_time='20240101',
    end_time='',
    incrementally=False
)
```

**参数说明：**
- `stock_code` - 合约代码，如`600000.SH`
- `period` - 周期：`tick`, `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w`, `1mon`
- `start_time` - 起始时间，格式`YYYYMMDD`或`YYYYMMDDHHMMSS`
- `end_time` - 结束时间，空字符串表示最新
- `incrementally` - 是否增量下载

### 获取行情数据

```python
data = xtdata.get_market_data(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['600000.SH', '000001.SZ'],
    period='1d',
    start_time='20240101',
    end_time='',
    count=-1,
    dividend_type='front_ratio',
    fill_data=True
)
```

**返回格式：**
```python
{
    'open': DataFrame,
    'high': DataFrame,
    'low': DataFrame,
    'close': DataFrame,
    'volume': DataFrame
}
```

每个DataFrame的index为时间，columns为股票代码。

### 获取行情数据 (增强版)

```python
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['600000.SH'],
    period='1d',
    start_time='20240101',
    end_time='',
    count=-1,
    dividend_type='front_ratio',
    fill_data=False
)
```

返回格式：`{stock_code: DataFrame}`

### 订阅单股行情

```python
def on_data(datas):
    """
    回调函数
    datas格式: {stock_code: [data1, data2, ...]}
    """
    for stock_code in datas:
        print(stock_code, datas[stock_code])

seq = xtdata.subscribe_quote(
    stock_code='600000.SH',
    period='1d',
    start_time='',
    end_time='',
    count=0,
    callback=on_data
)
```

**返回值：** 订阅号(大于0成功，-1失败)

### 订阅全推行情

```python
def on_data(datas):
    """
    datas格式: {stock1: data1, stock2: data2, ...}
    """
    for stock_code in datas:
        print(stock_code, datas[stock_code])

# 订阅全市场
seq = xtdata.subscribe_whole_quote(['SH', 'SZ'], callback=on_data)

# 订阅指定合约
seq = xtdata.subscribe_whole_quote(['600000.SH', '000001.SZ'], callback=on_data)
```

### 反订阅

```python
xtdata.unsubscribe_quote(seq)
```

### 获取全推数据

```python
# 获取当前最新全推数据（分笔）
tick_data = xtdata.get_full_tick(['600000.SH', '000001.SZ'])
```

返回格式：
```python
{
    '600000.SH': {
        'lastPrice': 10.5,
        'open': 10.3,
        'high': 10.6,
        'low': 10.2,
        'volume': 123456,
        'bidPrice': [10.4, 10.39, 10.38, ...],
        'bidVol': [100, 200, 300, ...],
        'askPrice': [10.41, 10.42, 10.43, ...],
        'askVol': [150, 250, 350, ...]
    }
}
```

### 阻塞线程接收回调

```python
xtdata.run()
```

用于订阅模式后阻塞主线程，保持程序运行。

## 财务数据接口

### 下载财务数据

```python
xtdata.download_financial_data(stock_list=['600000.SH'])
```

### 获取财务数据

```python
financial_data = xtdata.get_financial_data(
    stock_list=['600000.SH'],
    table_list=['BalanceSheet', 'IncomeStatement', 'CashFlowStatement']
)
```

**财务报表类型：**
- `BalanceSheet` - 资产负债表
- `IncomeStatement` - 利润表
- `CashFlowStatement` - 现金流量表
- `CapitalStructure` - 股本结构
- `Top10Stockholders` - 十大股东
- `Top10TradableStockholders` - 十大流通股东
- `InstitutionalHoldings` - 机构持股
- `ShareChg` - 股本变动
- `Dividend` - 分红指标
- `Allotment` - 配股指标

## 合约信息接口

### 获取合约详细信息

```python
info = xtdata.get_instrument_detail('600000.SH')
```

返回字段包括：
- `InstrumentName` - 合约名称
- `InstrumentCode` - 合约代码
- `ExchangeCode` - 交易所代码
- `ProductType` - 产品类型
- `PriceTick` - 最小变动价位
- `UpperLimitPrice` - 涨停价
- `LowerLimitPrice` - 跌停价
- `VolumeMultiple` - 合约乘数

### 获取板块列表

```python
# 下载板块数据
xtdata.download_sector_data()

# 获取所有板块列表
sector_list = xtdata.get_sector_list()
```

### 获取板块成分股

```python
# 获取沪深A股列表
stocks = xtdata.get_stock_list_in_sector('沪深A股')

# 获取行业板块成分股
stocks = xtdata.get_stock_list_in_sector('SW1银行')

# 获取概念板块成分股
stocks = xtdata.get_stock_list_in_sector('GN人工智能')
```

**常用板块：**
- `沪深A股` - 沪深A股全部股票
- `SH` - 上交所全部股票
- `SZ` - 深交所全部股票
- `BJ` - 北交所全部股票
- `SW1xxx` - 申万一级行业
- `SW2xxx` - 申万二级行业
- `GNxxx` - 概念板块

## 其他常用接口

### 获取交易日历

```python
# 获取交易日列表
trading_dates = xtdata.get_trading_dates(start_time='20240101', end_time='20241231')

# 获取节假日
holidays = xtdata.get_holidays(start_time='20240101', end_time='20241231')
```

### 获取除权因子

```python
divid_factors = xtdata.get_divid_factors('600000.SH')
```

### 获取可转债信息

```python
# 下载可转债数据
xtdata.download_cb_data()

# 获取可转债信息
cb_info = xtdata.get_cb_info('110043.SH')
```

### 获取ETF申赎清单

```python
# 下载ETF数据
xtdata.download_etf_info()

# 获取ETF信息
etf_info = xtdata.get_etf_info('510050.SH')
```

### 获取指数成分权重

```python
# 下载指数成分权重信息
xtdata.download_index_weight()

# 获取指数成分权重
weights = xtdata.get_index_weight('000300.SH')
# 返回: {stock_code: weight, ...}
```

### 获取新股申购信息

```python
ipo_info = xtdata.get_ipo_info('20240101', '20241231')
# 返回: [{securityCode, codeName, market, onlineSubMaxQty, publishPrice, ...}, ...]
```

### 获取节假日数据

```python
# 下载节假日数据
xtdata.download_holiday_data()

# 获取节假日列表
holidays = xtdata.get_holidays()
# 返回: ['20240101', '20240210', ...]
```

### 获取交易日历

```python
trading_calendar = xtdata.get_trading_calendar('SH', '20240101', '20241231')
# 返回: 交易日列表
```

## 板块管理接口

### 创建板块目录

```python
folder_name = xtdata.create_sector_folder('', '我的自选', overwrite=True)
```

### 创建板块

```python
sector_name = xtdata.create_sector('', '科技板块', overwrite=True)
```

### 添加成分股到板块

```python
xtdata.add_sector('科技板块', ['000001.SZ', '600000.SH', '000858.SZ'])
```

### 移除板块成分股

```python
xtdata.remove_stock_from_sector('科技板块', ['000001.SZ'])
```

### 移除板块

```python
xtdata.remove_sector('科技板块')
```

### 重置板块

```python
xtdata.reset_sector('科技板块', ['600000.SH', '000858.SZ'])
```

## 模型相关接口（投研版）

### 订阅模型

```python
def on_model_data(datas):
    print(datas)

sub_id = xtdata.subscribe_formula(
    formula_name='MA',
    stock_code='000300.SH',
    period='1d',
    start_time='',
    end_time='',
    count=-1,
    dividend_type='none',
    extend_param={'MA:n1': 5},
    callback=on_model_data
)
```

### 反订阅模型

```python
xtdata.unsubscribe_formula(sub_id)
```

### 调用模型

```python
result = xtdata.call_formula(
    formula_name='MA',
    stock_code='000300.SH',
    period='1d',
    start_time='20240101',
    end_time='',
    count=-1,
    dividend_type='none',
    extend_param={'MA:n1': 5}
)
# 返回: {'dbt': 0, 'timelist': [...], 'outputs': {'var1': [...], 'var2': [...]}}
```

### 批量调用模型

```python
results = xtdata.call_formula_batch(
    formula_names=['MA', 'MACD'],
    stock_codes=['000300.SH', '000001.SZ'],
    period='1d',
    extend_params=[{'MA:n1': 5}, {'MACD:short': 12}]
)
```

### 生成因子数据

```python
xtdata.generate_index_data(
    formula_name='MA',
    formula_param={'n1': 5},
    stock_list=['000300.SH', '000001.SZ'],
    period='1d',
    dividend_type='none',
    start_time='20240101',
    end_time='20241231',
    fill_mode='fixed',
    fill_value=float('nan'),
    result_path='C:\\factor_data.feather'
)
```

## 周期类型说明

### Level1数据周期

| 周期 | 说明 |
|------|------|
| `tick` | 分笔数据 |
| `1m` | 1分钟线 |
| `5m` | 5分钟线 |
| `15m` | 15分钟线 |
| `30m` | 30分钟线 |
| `1h` | 1小时线 |
| `1d` | 日线 |
| `1w` | 周线 |
| `1mon` | 月线 |
| `1q` | 季度线 |
| `1hy` | 半年线 |
| `1y` | 年线 |

### 投研版特色数据周期

| 周期 | 说明 |
|------|------|
| `warehousereceipt` | 期货仓单 |
| `futureholderrank` | 期货席位 |
| `interactiveqa` | 互动问答 |
| `transactioncount1m` | 逐笔成交统计1分钟级 |
| `transactioncount1d` | 逐笔成交统计日级 |
| `delistchangebond` | 退市可转债信息 |
| `replacechangebond` | 待发可转债信息 |
| `specialtreatment` | ST变更历史 |
| `northfinancechange1m` | 港股通资金流向1分钟级 |
| `northfinancechange1d` | 港股通资金流向日级 |
| `dividendplaninfo` | 红利分配方案信息 |
| `historycontract` | 过期合约列表 |
| `optionhistorycontract` | 期权历史信息 |
| `historymaincontract` | 历史主力合约 |
| `stoppricedata` | 涨跌停数据 |
| `snapshotindex` | 快照指标数据 |

## 除权方式说明

| 类型 | 说明 |
|------|------|
| `none` | 不复权 |
| `front` | 前复权 |
| `back` | 后复权 |
| `front_ratio` | 等比前复权 |
| `back_ratio` | 等比后复权 |

## 数据字段说明

### tick - 分笔数据字段

| 字段名 | 说明 |
|--------|------|
| `time` | 时间戳 |
| `lastPrice` | 最新价 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `lastClose` | 前收盘价 |
| `amount` | 成交总额 |
| `volume` | 成交总量 |
| `pvolume` | 原始成交总量 |
| `stockStatus` | 证券状态 |
| `openInt` | 持仓量 |
| `lastSettlementPrice` | 前结算 |
| `askPrice` | 委卖价（列表） |
| `bidPrice` | 委买价（列表） |
| `askVol` | 委卖量（列表） |
| `bidVol` | 委买量（列表） |
| `transactionNum` | 成交笔数 |

### K线数据字段（1m/5m/1d等）

| 字段名 | 说明 |
|--------|------|
| `time` | 时间戳 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 成交量 |
| `amount` | 成交额 |
| `settelementPrice` | 今结算 |
| `openInterest` | 持仓量 |
| `preClose` | 前收价 |
| `suspendFlag` | 停牌标记（0-正常，1-停牌，-1-当日起复牌） |

### Level2实时行情快照（l2quote）

| 字段名 | 说明 |
|--------|------|
| `time` | 时间戳 |
| `lastPrice` | 最新价 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `amount` | 成交额 |
| `volume` | 成交总量 |
| `transactionNum` | 成交笔数 |
| `pe` | 市盈率 |
| `askPrice` | 多档委卖价 |
| `bidPrice` | 多档委买价 |
| `askVol` | 多档委卖量 |
| `bidVol` | 多档委买量 |

### Level2逐笔委托（l2order）

| 字段名 | 说明 |
|--------|------|
| `time` | 时间戳 |
| `price` | 委托价 |
| `volume` | 委托量 |
| `entrustNo` | 委托号 |
| `entrustType` | 委托类型 |
| `entrustDirection` | 委托方向 |

### Level2逐笔成交（l2transaction）

| 字段名 | 说明 |
|--------|------|
| `time` | 时间戳 |
| `price` | 成交价 |
| `volume` | 成交量 |
| `amount` | 成交额 |
| `tradeIndex` | 成交记录号 |
| `buyNo` | 买方委托号 |
| `sellNo` | 卖方委托号 |
| `tradeType` | 成交类型 |
| `tradeFlag` | 成交标志 |

## 数据字典

### 证券状态

| 值 | 含义 |
|----|------|
| 0, 10 | 未知 |
| 11 | 开盘前 |
| 12 | 集合竞价时段 |
| 13 | 连续交易 |
| 14 | 休市 |
| 15 | 闭市 |
| 16 | 波动性中断 |
| 17 | 临时停牌 |
| 18 | 收盘集合竞价 |
| 19 | 盘中集合竞价 |
| 20 | 暂停交易至闭市 |
| 21 | 获取字段异常 |
| 22 | 盘后固定价格行情 |
| 23 | 盘后固定价格行情完毕 |

### 委托类型（逐笔委托）

| 值 | 含义 |
|----|------|
| 0 | 未知 |
| 1 | 正常交易业务 |
| 2 | 即时成交剩余撤销 |
| 3 | ETF基金申报 |
| 4 | 最优五档即时成交剩余撤销 |
| 5 | 全额成交或撤销 |
| 6 | 本方最优价格 |
| 7 | 对手方最优价格 |

### 委托方向（逐笔委托）

| 值 | 含义 |
|----|------|
| 1 | 买入 |
| 2 | 卖出 |
| 3 | 撤买（上交所） |
| 4 | 撤卖（上交所） |

### 成交标志（逐笔成交）

| 值 | 含义 |
|----|------|
| 0 | 未知 |
| 1 | 外盘 |
| 2 | 内盘 |
| 3 | 撤单（深交所） |

### 现金替代标志（ETF申赎）

| 值 | 含义 |
|----|------|
| 0 | 禁止现金替代（必须有股票） |
| 1 | 允许现金替代（先用股票，不足用现金） |
| 2 | 必须现金替代 |
| 3 | 非沪市退补现金替代 |
| 4 | 非沪市必须现金替代 |
| 5 | 非沪深退补现金替代 |
| 6 | 非沪深必须现金替代 |
| 7 | 港市退补现金替代 |
| 8 | 港市必须现金替代 |

## 请求限制

- **单股订阅**：建议不超过50只，更多请使用全推订阅
- **全推订阅**：支持全市场订阅，流量和处理效率优于单股订阅
- **板块数据**：静态信息更新频率低，按周或按日定期下载即可
