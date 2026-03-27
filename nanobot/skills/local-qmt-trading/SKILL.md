---
name: local-qmt-trading
description: 本地QMT量化交易REST API。用于A股买入卖出下单、撤销委托、查询持仓、查询资金、查询当日委托和成交记录。基于miniQMT，支持限价单和市价单，支持多账户。当用户需要执行真实股票交易（买入、卖出、撤单）、查看持仓、查看账户资金、查看委托成交记录时使用此技能。
metadata: {"nanobot":{"emoji":"💰","requires":{"bins":["python"]}}}
---

# 本地 QMT 量化交易

通过 Python 脚本调用 QMT 量化交易 REST API，执行 A 股交易和查询。

**环境变量：** `QMT_API_URL` — API 基地址（默认 `http://192.168.20.158:8001`）

> **多账户** 所有命令支持 `--account-id` 指定目标账户，不传则使用默认账户。

---

## 使用方法

### 健康检查

```bash
python scripts/qmt_trading.py health
```

### 查询账户资金

```bash
python scripts/qmt_trading.py assets
python scripts/qmt_trading.py assets --account-id 40126355
```

### 查询当前持仓

```bash
python scripts/qmt_trading.py positions
```

### 买入下单

**限价买入：**
```bash
python scripts/qmt_trading.py buy --stock-code 600519.SH --quantity 100 --price 1800.0
```

**市价买入：**
```bash
python scripts/qmt_trading.py buy --stock-code 000001.SZ --quantity 500 --price-type market
```

### 卖出下单

**限价卖出：**
```bash
python scripts/qmt_trading.py sell --stock-code 600519.SH --quantity 100 --price 1850.0
```

**市价卖出：**
```bash
python scripts/qmt_trading.py sell --stock-code 600519.SH --quantity 100 --price-type market
```

### 撤销委托

```bash
python scripts/qmt_trading.py cancel --order-id 12345
python scripts/qmt_trading.py cancel --order-id 12345 --account-id 40126355
```

### 查询当日委托

```bash
python scripts/qmt_trading.py orders
```

### 查询当日成交

```bash
python scripts/qmt_trading.py trades
```

### 查询历史成交

```bash
python scripts/qmt_trading.py history --start-date 20260301 --end-date 20260312
```

---

## 买卖参数

| 参数 | 必填 | 说明 |
|------|------|------|
| --stock-code | ✅ | 股票代码，沪市`.SH`，深市`.SZ` |
| --quantity | ✅ | 数量（股），A股最小100股 |
| --price | | 价格，限价单必填>0，市价单可不传 |
| --price-type | | `limit`(限价/默认) 或 `market`(市价) |
| --account-id | | 目标账户ID |
| --strategy-name | | 策略名称 |
| --order-remark | | 订单备注 |

## 撤单参数

| 参数 | 必填 | 说明 |
|------|------|------|
| --order-id | ✅ | 要撤销的订单ID（从 orders 查询获取） |
| --account-id | | 目标账户ID |

## 重要规则

1. **股票代码格式**：沪市 `XXXXXX.SH`，深市 `XXXXXX.SZ`
2. **最小交易单位**：100 股
3. **T+1 规则**：当日买入当日不可卖
4. **下单确认**：submitted 仅表示已提交，需查 orders/trades 确认成交
5. **可卖判断**：卖出前查持仓 `can_use_volume`
6. **撤单时机**：只能撤销未完全成交的委托（状态为未报/待报/已报/部成）
