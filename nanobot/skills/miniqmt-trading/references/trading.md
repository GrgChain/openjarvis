# XtQuant 交易模块 (xttrader) 参考

## 运行逻辑

XtQuant封装了策略交易所需要的Python API接口，可以和MiniQMT客户端交互进行：
- 报单、撤单
- 查询资产、委托、成交、持仓
- 接收资金、委托、成交和持仓等变动的主推消息

## 初始化流程

```python
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

# 1. 创建交易对象
path = 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini'  # 客户端路径
session_id = 123456  # 会话编号，不同策略用不同编号
xt_trader = XtQuantTrader(path, session_id)

# 2. 创建账号对象
acc = StockAccount('1000000365')  # 资金账号
# acc = StockAccount('1000000365', 'STOCK')  # 指定账号类型

# 3. 创建并注册回调
callback = MyXtQuantTraderCallback()
xt_trader.register_callback(callback)

# 4. 启动交易线程
xt_trader.start()

# 5. 建立连接
connect_result = xt_trader.connect()  # 返回0表示成功

# 6. 订阅交易主推
subscribe_result = xt_trader.subscribe(acc)  # 返回0表示成功

# 7. 阻塞线程接收主推
xt_trader.run_forever()
```

**账号类型：**
- `STOCK` - 股票账号（默认）
- `CREDIT` - 信用账号
- `FUTURE` - 期货账号
- `STOCK_OPTION` - 股票期权账号
- `FUTURE_OPTION` - 期货期权账号
- `HUGANGTONG` - 沪港通
- `SHENGANGTONG` - 深港通

## 回调类定义

```python
class MyXtQuantTraderCallback(XtQuantTraderCallback):
    
    def on_disconnected(self):
        """连接断开回调"""
        print("连接断开")
    
    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        """
        print(f"委托回调: {order.stock_code}, 状态: {order.order_status}")
    
    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        """
        print(f"成交回调: {trade.stock_code}, 成交量: {trade.traded_volume}")
    
    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error: XtOrderError对象
        """
        print(f"委托失败: {order_error.error_msg}")
    
    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError对象
        """
        print(f"撤单失败: {cancel_error.error_msg}")
    
    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse对象
        """
        print(f"异步下单回报: {response.order_id}")
    
    def on_cancel_order_stock_async_response(self, response):
        """
        异步撤单回报推送
        :param response: XtCancelOrderResponse对象
        """
        print(f"异步撤单回报: {response.order_id}")
    
    def on_account_status(self, status):
        """
        账号状态主推
        :param status: XtAccountStatus对象
        """
        print(f"账号状态: {status.account_id}, 状态: {status.status}")

    def on_smt_appointment_async_response(self, response):
        """
        约券申请异步回报
        :param response: XtSmtAppointmentResponse对象
        """
        print(f"约券申请回报: {response.apply_id}, 成功: {response.success}")
```

## 数据结构说明

### XtAsset（资产）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| cash | float | 可用金额 |
| frozen_cash | float | 冻结金额 |
| market_value | float | 持仓市值 |
| total_asset | float | 总资产 |

### XtOrder（委托）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码 |
| order_id | int | 订单编号 |
| order_sysid | str | 柜台合同编号 |
| order_time | int | 报单时间 |
| order_type | int | 委托类型 |
| order_volume | int | 委托数量 |
| price_type | int | 报价类型 |
| price | float | 委托价格 |
| traded_volume | int | 成交数量 |
| traded_price | float | 成交均价 |
| order_status | int | 委托状态 |
| status_msg | str | 委托状态描述 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注 |
| direction | int | 多空方向 |
| offset_flag | int | 交易操作 |

### XtTrade（成交）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码 |
| order_type | int | 委托类型 |
| traded_id | str | 成交编号 |
| traded_time | int | 成交时间 |
| traded_price | float | 成交均价 |
| traded_volume | int | 成交数量 |
| traded_amount | float | 成交金额 |
| order_id | int | 订单编号 |
| order_sysid | str | 柜台合同编号 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注 |
| direction | int | 多空方向 |
| offset_flag | int | 交易操作 |

### XtPosition（持仓）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码 |
| volume | int | 持仓数量 |
| can_use_volume | int | 可用数量 |
| open_price | float | 开仓价 |
| avg_price | float | 成本价 |
| market_value | float | 市值 |
| frozen_volume | int | 冻结数量 |
| on_road_volume | int | 在途股份 |
| yesterday_volume | int | 昨夜拥股 |
| direction | int | 多空方向 |

### XtPositionStatistics（期货持仓统计）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_id | str | 账户 |
| exchange_id | str | 市场代码 |
| product_id | str | 品种代码 |
| instrument_id | str | 合约代码 |
| direction | int | 多空方向 |
| position | int | 持仓数量 |
| yesterday_position | int | 昨仓数量 |
| today_position | int | 今仓数量 |
| can_close_vol | int | 可平数量 |
| position_cost | float | 持仓成本 |
| avg_price | float | 持仓均价 |
| position_profit | float | 持仓盈亏 |
| float_profit | float | 浮动盈亏 |
| used_margin | float | 已使用保证金 |
| close_profit | float | 平仓盈亏 |

### XtOrderResponse（异步下单委托反馈）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| order_id | int | 订单编号 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注 |
| seq | int | 异步下单的请求序号 |

### XtCancelOrderResponse（异步撤单委托反馈）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| order_id | int | 订单编号 |
| order_sysid | str | 柜台委托编号 |
| cancel_result | int | 撤单结果（0成功，-1失败） |
| seq | int | 异步撤单的请求序号 |

### XtOrderError（下单失败错误）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| order_id | int | 订单编号 |
| error_id | int | 下单失败错误码 |
| error_msg | str | 下单失败具体信息 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注 |

### XtCancelError（撤单失败错误）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| order_id | int | 订单编号 |
| market | int | 交易市场 |
| order_sysid | str | 柜台委托编号 |
| error_id | int | 撤单失败错误码 |
| error_msg | str | 撤单失败具体信息 |

### XtCreditDetail（信用账号资产）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| m_dBalance | float | 总资产 |
| m_dAvailable | float | 可用金额 |
| m_dMarketValue | float | 总市值 |
| m_dFetchBalance | float | 可取金额 |
| m_dTotalDebt | float | 总负债 |
| m_dPerAssurescaleValue | float | 维持担保比例 |
| m_dAssureAsset | float | 净资产 |
| m_dFinDebt | float | 融资负债 |
| m_dFinEnableQuota | float | 融资可用额度 |
| m_dSloEnableQuota | float | 融券可用额度 |

### XtStkCompacts（负债合约）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| compact_type | int | 合约类型 |
| open_date | int | 开仓日期 |
| business_vol | int | 合约证券数量 |
| real_compact_vol | int | 未还合约数量 |
| business_balance | float | 合约金额 |
| instrument_id | str | 证券代码 |
| compact_id | str | 合约编号 |

### XtCreditSubjects（融资融券标的）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| slo_status | int | 融券状态 |
| fin_status | int | 融资状态 |
| slo_ratio | float | 融券保证金比例 |
| fin_ratio | float | 融资保证金比例 |
| instrument_id | str | 证券代码 |

### XtCreditSloCode（可融券数据）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| enable_amount | int | 融券可融数量 |
| instrument_id | str | 证券代码 |

### XtCreditAssure（标的担保品）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| assure_status | int | 是否可做担保 |
| assure_ratio | float | 担保品折算比例 |
| instrument_id | str | 证券代码 |

### XtAccountStatus（账号状态）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| status | int | 账号状态 |

### XtAccountInfo（账号信息）

| 属性 | 类型 | 说明 |
|------|------|------|
| account_type | int | 账号类型 |
| account_id | str | 资金账号 |
| platform_id | int | 平台号 |
| login_status | int | 账号状态 |

### XtSmtAppointmentResponse（约券相关异步接口的反馈）

| 属性 | 类型 | 说明 |
|------|------|------|
| seq | int | 异步请求序号 |
| success | bool | 申请是否成功 |
| msg | str | 反馈信息 |
| apply_id | str | 资券申请编号 |

## 下单接口

### 同步下单

```python
order_id = xt_trader.order_stock(
    account=acc,
    stock_code='600000.SH',
    order_type=xtconstant.STOCK_BUY,
    order_volume=100,
    price_type=xtconstant.FIX_PRICE,
    price=10.5,
    strategy_name='my_strategy',
    order_remark='测试下单'
)
```

**参数说明：**
- `account` - StockAccount对象
- `stock_code` - 合约代码，如`600000.SH`
- `order_type` - 委托类型（见下方常量表）
- `order_volume` - 委托数量（股票为100的整数倍）
- `price_type` - 报价类型
- `price` - 委托价格
- `strategy_name` - 策略名称（可选）
- `order_remark` - 投资备注（可选）

**返回值：** 订单编号（大于0成功，-1失败）

### 异步下单

```python
seq = xt_trader.order_stock_async(
    account=acc,
    stock_code='600000.SH',
    order_type=xtconstant.STOCK_BUY,
    order_volume=100,
    price_type=xtconstant.FIX_PRICE,
    price=10.5,
    strategy_name='my_strategy',
    order_remark='测试下单'
)
```

**返回值：** 请求序号seq，可通过`on_order_stock_async_response`回调获取订单编号

### 同步撤单

```python
result = xt_trader.cancel_order_stock(acc, order_id)
```

**返回值：** 0表示成功

### 异步撤单

```python
seq = xt_trader.cancel_order_stock_async(acc, order_id)
```

### 根据柜台合同编号撤单（同步）

```python
result = xt_trader.cancel_order_stock_sysid(acc, market, order_sysid)
```

**参数说明：**
- `market` - 交易市场，如`xtconstant.SH_MARKET`
- `order_sysid` - 券商柜台的合同编号

**返回值：** 0表示成功，-1表示失败

### 根据柜台合同编号撤单（异步）

```python
seq = xt_trader.cancel_order_stock_sysid_async(acc, market, order_sysid)
```

**返回值：** 撤单请求序号

### 资金划拨

```python
success, msg = xt_trader.fund_transfer(account, transfer_direction, price)
```

**参数说明：**
- `transfer_direction` - 划拨方向，见划拨方向常量
- `price` - 划拨金额

**返回值：** (success, msg)
- `success` - bool，划拨操作是否成功
- `msg` - str，反馈信息

### 外部交易数据录入

```python
result = xt_trader.sync_transaction_from_external(operation, data_type, account, deal_list)
```

**参数说明：**
- `operation` - 操作类型："UPDATE","REPLACE","ADD","DELETE"
- `data_type` - 数据类型："DEAL"
- `deal_list` - 成交列表，每一项是Deal成交对象的参数字典

**返回值：** dict，结果反馈信息

**示例：**
```python
deal_list = [
    {'m_strExchangeID':'SF', 'm_strInstrumentID':'ag2407',
     'm_strTradeID':'123456', 'm_strOrderSysID':'1234566',
     'm_dPrice':7600, 'm_nVolume':1,
     'm_strTradeDate': '20240627'}
]
resp = xt_trader.sync_transaction_from_external('ADD', 'DEAL', acc, deal_list)
```

## 查询接口

### 查询资产

```python
asset = xt_trader.query_stock_asset(acc)
```

**返回对象XtAsset属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `cash` - 可用金额
- `frozen_cash` - 冻结金额
- `market_value` - 持仓市值
- `total_asset` - 总资产

### 查询持仓

```python
# 查询全部持仓
positions = xt_trader.query_stock_positions(acc)

# 查询指定股票持仓
position = xt_trader.query_stock_position(acc, '600000.SH')
```

**返回对象XtPosition属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `stock_code` - 证券代码
- `volume` - 总持仓量
- `can_use_volume` - 可用持仓量
- `open_price` - 开仓价
- `avg_price` - 成本价
- `market_value` - 市值
- `direction` - 多空方向（期货用）

### 查询委托

```python
# 查询当日全部委托
orders = xt_trader.query_stock_orders(acc)

# 查询可撤委托
orders = xt_trader.query_stock_orders(acc, cancelable_only=True)

# 查询指定委托
order = xt_trader.query_stock_order(acc, order_id)
```

**返回对象XtOrder属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `stock_code` - 证券代码
- `order_id` - 订单编号
- `order_sysid` - 柜台合同编号
- `order_time` - 报单时间
- `order_type` - 委托类型
- `order_volume` - 委托数量
- `price_type` - 报价类型
- `price` - 委托价格
- `order_status` - 委托状态
- `traded_volume` - 已成交数量
- `traded_price` - 成交均价

### 查询成交

```python
trades = xt_trader.query_stock_trades(acc)
```

**返回对象XtTrade属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `stock_code` - 证券代码
- `order_id` - 订单编号
- `trade_id` - 成交编号
- `trade_time` - 成交时间
- `traded_volume` - 成交数量
- `traded_price` - 成交价格
- `direction` - 多空方向
- `offset_flag` - 交易操作

### 期货持仓统计查询

```python
positions = xt_trader.query_position_statistics(acc)
```

**返回对象XtPositionStatistics属性：**
- `account_id` - 账户
- `exchange_id` - 市场代码
- `product_id` - 品种代码
- `instrument_id` - 合约代码
- `direction` - 多空方向
- `position` - 持仓数量
- `yesterday_position` - 昨仓数量
- `today_position` - 今仓数量
- `can_close_vol` - 可平数量
- `position_cost` - 持仓成本
- `avg_price` - 持仓均价
- `position_profit` - 持仓盈亏
- `float_profit` - 浮动盈亏
- `used_margin` - 已使用保证金
- `close_profit` - 平仓盈亏

### 信用资产查询

```python
credit_detail = xt_trader.query_credit_detail(acc)
```

**返回对象XtCreditDetail属性：**
- `account_id` - 资金账号
- `m_dBalance` - 总资产
- `m_dAvailable` - 可用金额
- `m_dMarketValue` - 总市值
- `m_dTotalDebt` - 总负债
- `m_dPerAssurescaleValue` - 维持担保比例
- `m_dAssureAsset` - 净资产
- `m_dFinDebt` - 融资负债
- `m_dFinEnableQuota` - 融资可用额度
- `m_dSloEnableQuota` - 融券可用额度

### 负债合约查询

```python
compacts = xt_trader.query_stk_compacts(acc)
```

**返回对象XtStkCompacts属性：**
- `account_id` - 资金账号
- `compact_type` - 合约类型
- `open_date` - 开仓日期
- `business_vol` - 合约证券数量
- `real_compact_vol` - 未还合约数量
- `business_balance` - 合约金额
- `instrument_id` - 证券代码
- `compact_id` - 合约编号

### 融资融券标的查询

```python
subjects = xt_trader.query_credit_subjects(acc)
```

**返回对象XtCreditSubjects属性：**
- `account_id` - 资金账号
- `slo_status` - 融券状态
- `fin_status` - 融资状态
- `slo_ratio` - 融券保证金比例
- `fin_ratio` - 融资保证金比例
- `instrument_id` - 证券代码

### 可融券数据查询

```python
slo_codes = xt_trader.query_credit_slo_code(acc)
```

**返回对象XtCreditSloCode属性：**
- `account_id` - 资金账号
- `enable_amount` - 融券可融数量
- `instrument_id` - 证券代码

### 标的担保品查询

```python
assures = xt_trader.query_credit_assure(acc)
```

**返回对象XtCreditAssure属性：**
- `account_id` - 资金账号
- `assure_status` - 是否可做担保
- `assure_ratio` - 担保品折算比例
- `instrument_id` - 证券代码

### 新股申购额度查询

```python
limit_data = xt_trader.query_new_purchase_limit(acc)
```

**返回值：** dict，新股申购额度数据集
- `KCB` - 科创板可申购股数
- `SH` - 上海可申购股数
- `SZ` - 深圳可申购股数

### 当日新股信息查询

```python
ipo_data = xt_trader.query_ipo_data()
```

**返回值：** dict，新股新债信息数据集
- `name` - 品种名称
- `type` - 品种类型（STOCK-股票，BOND-债券）
- `minPurchaseNum` - 最小申购额度
- `maxPurchaseNum` - 最大申购额度
- `purchaseDate` - 申购日期
- `issuePrice` - 发行价

### 账号信息查询

```python
account_infos = xt_trader.query_account_infos()
```

**返回对象XtAccountInfo属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `platform_id` - 平台号
- `login_status` - 账号状态

### 账号状态查询

```python
account_status = xt_trader.query_account_status()
```

**返回对象XtAccountStatus属性：**
- `account_type` - 账号类型
- `account_id` - 资金账号
- `status` - 账号状态

### 普通柜台资金查询

```python
result = xt_trader.query_com_fund(acc)
```

**返回值：** dict，包含以下字段：
- `success` - bool
- `currentBalance` - 当前余额
- `enableBalance` - 可用余额
- `fetchBalance` - 可取金额
- `assetBalance` - 总资产
- `marketValue` - 市值

### 普通柜台持仓查询

```python
positions = xt_trader.query_com_position(acc)
```

**返回值：** list，持仓信息列表，每个元素包含：
- `stockCode` - 证券代码
- `stockName` - 证券名称
- `totalAmt` - 总量
- `enableAmount` - 可用量
- `costPrice` - 成本价
- `marketValue` - 市值

### 通用数据导出

```python
result = xt_trader.export_data(acc, result_path, data_type, start_time=None, end_time=None, user_param={})
```

**参数说明：**
- `result_path` - 导出路径，如'C:\\deal.csv'
- `data_type` - 数据类型，如'deal'
- `start_time` - 开始时间（可选）
- `end_time` - 结束时间（可选）

### 通用数据查询

```python
data = xt_trader.query_data(acc, result_path, data_type, start_time=None, end_time=None, user_param={})
```

**说明：** 利用export_data接口导出数据后再读取其中的数据内容，读取完毕后删除导出的文件

### 券源行情查询

```python
quoters = xt_trader.smt_query_quoter(acc)
```

**返回值：** list，券源信息列表，每个元素包含：
- `code` - 证券代码
- `codeName` - 证券代码名称
- `enableSloAmountT0` - T+0可融券数量
- `enableSloAmountT3` - T+3可融券数量
- `usedRate` - 资券使用利率

### 库存券约券申请

```python
seq = xt_trader.smt_negotiate_order_async(account, src_group_id, order_code, date, amount, apply_rate, dict_param={})
```

**参数说明：**
- `src_group_id` - 来源组编号
- `order_code` - 证券代码
- `date` - 期限天数
- `amount` - 委托数量
- `apply_rate` - 资券申请利率
- `dict_param` - 可选参数字典（subFareRate-提前归还利率，fineRate-罚息利率）

**返回值：** 请求序号seq，通过`on_smt_appointment_async_response`回调获取结果
- `offset_flag` - 交易操作

## 委托类型常量

### 股票

| 常量 | 值 | 说明 |
|------|-----|------|
| `STOCK_BUY` | 23 | 买入 |
| `STOCK_SELL` | 24 | 卖出 |

### 信用交易

| 常量 | 说明 |
|------|------|
| `CREDIT_BUY` | 担保品买入 |
| `CREDIT_SELL` | 担保品卖出 |
| `CREDIT_FIN_BUY` | 融资买入 |
| `CREDIT_SLO_SELL` | 融券卖出 |
| `CREDIT_BUY_SECU_REPAY` | 买券还券 |
| `CREDIT_DIRECT_SECU_REPAY` | 直接还券 |
| `CREDIT_SELL_SECU_REPAY` | 卖券还款 |
| `CREDIT_DIRECT_CASH_REPAY` | 直接还款 |

### 期货（六键风格）

| 常量 | 说明 |
|------|------|
| `FUTURE_OPEN_LONG` | 开多 |
| `FUTURE_CLOSE_LONG_HISTORY` | 平昨多 |
| `FUTURE_CLOSE_LONG_TODAY` | 平今多 |
| `FUTURE_OPEN_SHORT` | 开空 |
| `FUTURE_CLOSE_SHORT_HISTORY` | 平昨空 |
| `FUTURE_CLOSE_SHORT_TODAY` | 平今空 |

### 股票期权

| 常量 | 说明 |
|------|------|
| `STOCK_OPTION_BUY_OPEN` | 买入开仓 |
| `STOCK_OPTION_SELL_CLOSE` | 卖出平仓 |
| `STOCK_OPTION_SELL_OPEN` | 卖出开仓 |
| `STOCK_OPTION_BUY_CLOSE` | 买入平仓 |
| `STOCK_OPTION_COVERED_OPEN` | 备兑开仓 |
| `STOCK_OPTION_COVERED_CLOSE` | 备兑平仓 |
| `STOCK_OPTION_CALL_EXERCISE` | 认购行权 |
| `STOCK_OPTION_PUT_EXERCISE` | 认沽行权 |

### ETF申赎

| 常量 | 说明 |
|------|------|
| `ETF_PURCHASE` | 申购 |
| `ETF_REDEMPTION` | 赎回 |

## 报价类型常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `FIX_PRICE` | 11 | 指定价 |
| `LATEST_PRICE` | 5 | 最新价 |
| `MARKET_PEER_PRICE_FIRST` | - | 对手方最优价格 |
| `MARKET_MINE_PRICE_FIRST` | - | 本方最优价格 |

## 委托状态常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `ORDER_UNREPORTED` | 48 | 未报 |
| `ORDER_WAIT_REPORTING` | 49 | 待报 |
| `ORDER_REPORTED` | 50 | 已报 |
| `ORDER_REPORTED_CANCEL` | 51 | 已报待撤 |
| `ORDER_PARTSUCC_CANCEL` | 52 | 部成待撤 |
| `ORDER_PART_CANCEL` | 53 | 部撤 |
| `ORDER_CANCELED` | 54 | 已撤 |
| `ORDER_PART_SUCC` | 55 | 部成 |
| `ORDER_SUCCEEDED` | 56 | 已成 |
| `ORDER_JUNK` | 57 | 废单 |
| `ORDER_UNKNOWN` | 255 | 未知 |

## 账号状态常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `ACCOUNT_STATUS_INVALID` | -1 | 无效 |
| `ACCOUNT_STATUS_OK` | 0 | 正常 |
| `ACCOUNT_STATUS_WAITING_LOGIN` | 1 | 连接中 |
| `ACCOUNT_STATUS_LOGINING` | 2 | 登陆中 |
| `ACCOUNT_STATUS_FAIL` | 3 | 失败 |
| `ACCOUNT_STATUS_INITING` | 4 | 初始化中 |
| `ACCOUNT_STATUS_CORRECTING` | 5 | 数据刷新校正中 |
| `ACCOUNT_STATUS_CLOSED` | 6 | 收盘后 |
| `ACCOUNT_STATUS_ASSIS_FAIL` | 7 | 穿透副链接断开 |
| `ACCOUNT_STATUS_DISABLEBYSYS` | 8 | 系统停用（密码错误超限） |
| `ACCOUNT_STATUS_DISABLEBYUSER` | 9 | 用户停用 |

## 划拨方向常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `FUNDS_TRANSFER_NORMAL_TO_SPEED` | 510 | 资金划拨-普通柜台到极速柜台 |
| `FUNDS_TRANSFER_SPEED_TO_NORMAL` | 511 | 资金划拨-极速柜台到普通柜台 |
| `NODE_FUNDS_TRANSFER_SH_TO_SZ` | 512 | 节点资金划拨-上海节点到深圳节点 |
| `NODE_FUNDS_TRANSFER_SZ_TO_SH` | 513 | 节点资金划拨-深圳节点到上海节点 |

## 多空方向常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `DIRECTION_FLAG_LONG` | 48 | 多 |
| `DIRECTION_FLAG_SHORT` | 49 | 空 |

## 交易操作常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `OFFSET_FLAG_OPEN` | 48 | 买入，开仓 |
| `OFFSET_FLAG_CLOSE` | 49 | 卖出，平仓 |
| `OFFSET_FLAG_FORCECLOSE` | 50 | 强平 |
| `OFFSET_FLAG_CLOSETODAY` | 51 | 平今 |
| `OFFSET_FLAG_ClOSEYESTERDAY` | 52 | 平昨 |
| `OFFSET_FLAG_FORCEOFF` | 53 | 强减 |
| `OFFSET_FLAG_LOCALFORCECLOSE` | 54 | 本地强平 |

## 高级设置

### 开启主动请求专用线程

在回调函数中调用同步查询接口时，需要开启此选项：

```python
xt_trader.set_relaxed_response_order_enabled(True)
```

这样可以避免在`on_stock_order`等回调中调用`query_xxx`函数时卡住回调线程。

### 停止运行

```python
xt_trader.stop()
```

## 注意事项

1. **路径配置**：券商版MiniQMT指向`userdata_mini`，投研版指向`userdata`
2. **session_id**：不同策略使用不同的会话编号，避免冲突
3. **回调处理**：交易回调中调用同步查询需开启`set_relaxed_response_order_enabled`
4. **股票数量**：股票委托数量必须是100的整数倍
5. **市价类型**：市价类型只在实盘环境生效，模拟环境不支持
