"""
MiniQMT 交易功能示例
演示如何使用xttrader模块进行下单、撤单、查询等操作
"""

import time
import datetime
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    """交易回调类"""
    
    def __init__(self):
        self.order_records = []
        self.trade_records = []
    
    def on_disconnected(self):
        """连接断开回调"""
        print(f"[{datetime.datetime.now()}] 连接断开")
    
    def on_stock_order(self, order):
        """委托回报推送"""
        print(f"[{datetime.datetime.now()}] 委托回调:")
        print(f"  股票: {order.stock_code}")
        print(f"  订单号: {order.order_id}")
        print(f"  状态: {order.order_status}")
        print(f"  委托量: {order.order_volume}")
        print(f"  已成交: {order.traded_volume}")
        self.order_records.append(order)
    
    def on_stock_trade(self, trade):
        """成交变动推送"""
        print(f"[{datetime.datetime.now()}] 成交回调:")
        print(f"  股票: {trade.stock_code}")
        print(f"  订单号: {trade.order_id}")
        print(f"  成交量: {trade.traded_volume}")
        print(f"  成交价: {trade.traded_price}")
        self.trade_records.append(trade)
    
    def on_order_error(self, order_error):
        """委托失败推送"""
        print(f"[{datetime.datetime.now()}] 委托失败:")
        print(f"  订单号: {order_error.order_id}")
        print(f"  错误码: {order_error.error_id}")
        print(f"  错误信息: {order_error.error_msg}")
    
    def on_cancel_error(self, cancel_error):
        """撤单失败推送"""
        print(f"[{datetime.datetime.now()}] 撤单失败:")
        print(f"  订单号: {cancel_error.order_id}")
        print(f"  错误码: {cancel_error.error_id}")
        print(f"  错误信息: {cancel_error.error_msg}")
    
    def on_order_stock_async_response(self, response):
        """异步下单回报推送"""
        print(f"[{datetime.datetime.now()}] 异步下单回报:")
        print(f"  账号: {response.account_id}")
        print(f"  订单号: {response.order_id}")
        print(f"  序号: {response.seq}")
    
    def on_cancel_order_stock_async_response(self, response):
        """异步撤单回报推送"""
        print(f"[{datetime.datetime.now()}] 异步撤单回报:")
        print(f"  订单号: {response.order_id}")
        print(f"  序号: {response.seq}")
    
    def on_account_status(self, status):
        """账号状态主推"""
        print(f"[{datetime.datetime.now()}] 账号状态变更:")
        print(f"  账号: {status.account_id}")
        print(f"  类型: {status.account_type}")
        print(f"  状态: {status.status}")


def init_trader(path, session_id, account_id, account_type='STOCK'):
    """
    初始化交易对象
    
    Args:
        path: MiniQMT客户端路径
        session_id: 会话编号
        account_id: 资金账号
        account_type: 账号类型
    
    Returns:
        (xt_trader, account) 元组
    """
    # 创建交易对象
    xt_trader = XtQuantTrader(path, session_id)
    
    # 创建账号对象
    account = StockAccount(account_id, account_type)
    
    # 创建并注册回调
    callback = MyXtQuantTraderCallback()
    xt_trader.register_callback(callback)
    
    # 启动交易线程
    xt_trader.start()
    
    # 建立连接
    connect_result = xt_trader.connect()
    if connect_result != 0:
        raise Exception(f"连接失败，错误码: {connect_result}")
    print("连接成功")
    
    # 订阅交易主推
    subscribe_result = xt_trader.subscribe(account)
    if subscribe_result != 0:
        raise Exception(f"订阅失败，错误码: {subscribe_result}")
    print("订阅成功")
    
    return xt_trader, account, callback


def query_asset_demo(xt_trader, account):
    """查询资产示例"""
    print("\n" + "=" * 50)
    print("查询资产")
    print("=" * 50)
    
    asset = xt_trader.query_stock_asset(account)
    
    if asset:
        print(f"账号类型: {asset.account_type}")
        print(f"资金账号: {asset.account_id}")
        print(f"可用金额: {asset.cash:.2f}")
        print(f"冻结金额: {asset.frozen_cash:.2f}")
        print(f"持仓市值: {asset.market_value:.2f}")
        print(f"总资产: {asset.total_asset:.2f}")
    else:
        print("查询资产失败")
    
    return asset


def query_positions_demo(xt_trader, account):
    """查询持仓示例"""
    print("\n" + "=" * 50)
    print("查询持仓")
    print("=" * 50)
    
    positions = xt_trader.query_stock_positions(account)
    
    print(f"共有 {len(positions)} 个持仓")
    
    for pos in positions[:5]:  # 只显示前5个
        print(f"\n股票: {pos.stock_code}")
        print(f"  总持仓: {pos.volume}")
        print(f"  可用持仓: {pos.can_use_volume}")
        print(f"  成本价: {pos.avg_price:.3f}")
        print(f"  开仓价: {pos.open_price:.3f}")
        print(f"  市值: {pos.market_value:.2f}")
    
    return positions


def query_orders_demo(xt_trader, account):
    """查询委托示例"""
    print("\n" + "=" * 50)
    print("查询当日委托")
    print("=" * 50)
    
    orders = xt_trader.query_stock_orders(account)
    
    print(f"共有 {len(orders)} 笔委托")
    
    for order in orders[:5]:  # 只显示前5个
        print(f"\n订单号: {order.order_id}")
        print(f"  股票: {order.stock_code}")
        print(f"  类型: {order.order_type}")
        print(f"  状态: {order.order_status}")
        print(f"  委托量: {order.order_volume}")
        print(f"  已成交: {order.traded_volume}")
        print(f"  价格: {order.price}")
    
    return orders


def query_trades_demo(xt_trader, account):
    """查询成交示例"""
    print("\n" + "=" * 50)
    print("查询当日成交")
    print("=" * 50)
    
    trades = xt_trader.query_stock_trades(account)
    
    print(f"共有 {len(trades)} 笔成交")
    
    for trade in trades[:5]:  # 只显示前5个
        print(f"\n成交号: {trade.trade_id}")
        print(f"  股票: {trade.stock_code}")
        print(f"  订单号: {trade.order_id}")
        print(f"  成交量: {trade.traded_volume}")
        print(f"  成交价: {trade.traded_price}")
        print(f"  时间: {trade.trade_time}")
    
    return trades


def buy_stock_demo(xt_trader, account, stock_code, price, volume):
    """买入股票示例"""
    print("\n" + "=" * 50)
    print(f"买入股票: {stock_code}")
    print("=" * 50)
    
    # 同步下单
    order_id = xt_trader.order_stock(
        account=account,
        stock_code=stock_code,
        order_type=xtconstant.STOCK_BUY,
        order_volume=volume,
        price_type=xtconstant.FIX_PRICE,
        price=price,
        strategy_name='demo_strategy',
        order_remark='买入演示'
    )
    
    if order_id > 0:
        print(f"下单成功，订单号: {order_id}")
    else:
        print(f"下单失败，错误码: {order_id}")
    
    return order_id


def sell_stock_demo(xt_trader, account, stock_code, price, volume):
    """卖出股票示例"""
    print("\n" + "=" * 50)
    print(f"卖出股票: {stock_code}")
    print("=" * 50)
    
    # 同步下单
    order_id = xt_trader.order_stock(
        account=account,
        stock_code=stock_code,
        order_type=xtconstant.STOCK_SELL,
        order_volume=volume,
        price_type=xtconstant.FIX_PRICE,
        price=price,
        strategy_name='demo_strategy',
        order_remark='卖出演示'
    )
    
    if order_id > 0:
        print(f"下单成功，订单号: {order_id}")
    else:
        print(f"下单失败，错误码: {order_id}")
    
    return order_id


def buy_stock_async_demo(xt_trader, account, stock_code, price, volume):
    """异步买入股票示例"""
    print("\n" + "=" * 50)
    print(f"异步买入股票: {stock_code}")
    print("=" * 50)
    
    # 异步下单
    seq = xt_trader.order_stock_async(
        account=account,
        stock_code=stock_code,
        order_type=xtconstant.STOCK_BUY,
        order_volume=volume,
        price_type=xtconstant.FIX_PRICE,
        price=price,
        strategy_name='demo_strategy',
        order_remark='异步买入演示'
    )
    
    print(f"异步下单请求已发送，序号: {seq}")
    print("请在on_order_stock_async_response回调中查看结果")
    
    return seq


def cancel_order_demo(xt_trader, account, order_id):
    """撤单示例"""
    print("\n" + "=" * 50)
    print(f"撤单: {order_id}")
    print("=" * 50)
    
    result = xt_trader.cancel_order_stock(account, order_id)
    
    if result == 0:
        print("撤单成功")
    else:
        print(f"撤单失败，错误码: {result}")
    
    return result


def query_specific_order_demo(xt_trader, account, order_id):
    """查询指定委托示例"""
    print("\n" + "=" * 50)
    print(f"查询指定委托: {order_id}")
    print("=" * 50)
    
    order = xt_trader.query_stock_order(account, order_id)
    
    if order:
        print(f"订单号: {order.order_id}")
        print(f"股票: {order.stock_code}")
        print(f"状态: {order.order_status}")
        print(f"委托量: {order.order_volume}")
        print(f"已成交: {order.traded_volume}")
    else:
        print("未找到该委托")
    
    return order


def query_specific_position_demo(xt_trader, account, stock_code):
    """查询指定持仓示例"""
    print("\n" + "=" * 50)
    print(f"查询指定持仓: {stock_code}")
    print("=" * 50)
    
    position = xt_trader.query_stock_position(account, stock_code)
    
    if position:
        print(f"股票: {position.stock_code}")
        print(f"总持仓: {position.volume}")
        print(f"可用持仓: {position.can_use_volume}")
        print(f"成本价: {position.avg_price:.3f}")
    else:
        print(f"未持有 {stock_code}")
    
    return position


if __name__ == '__main__':
    # ============================================
    # 配置参数（请根据实际情况修改）
    # ============================================
    
    # MiniQMT客户端路径
    # 券商版: userdata_mini
    # 投研版: userdata
    PATH = r'D:\迅投极速交易终端 睿智融科版\userdata_mini'
    
    # 资金账号
    ACCOUNT_ID = '1000000365'
    
    # 账号类型: STOCK, CREDIT, FUTURE, STOCK_OPTION, FUTURE_OPTION
    ACCOUNT_TYPE = 'STOCK'
    
    # 演示用的股票代码
    DEMO_STOCK = '600000.SH'
    
    # ============================================
    
    print("MiniQMT 交易功能演示")
    print("=" * 50)
    
    # 生成session_id
    session_id = int(time.time())
    print(f"Session ID: {session_id}")
    
    try:
        # 初始化交易对象
        xt_trader, account, callback = init_trader(
            PATH, session_id, ACCOUNT_ID, ACCOUNT_TYPE
        )
        
        # 查询资产
        asset = query_asset_demo(xt_trader, account)
        
        # 查询持仓
        positions = query_positions_demo(xt_trader, account)
        
        # 查询当日委托
        orders = query_orders_demo(xt_trader, account)
        
        # 查询当日成交
        trades = query_trades_demo(xt_trader, account)
        
        # 查询指定持仓
        position = query_specific_position_demo(xt_trader, account, DEMO_STOCK)
        
        # ============================================
        # 以下操作会实际下单，请谨慎使用
        # ============================================
        
        # # 买入股票（100股，价格10.5）
        # order_id = buy_stock_demo(xt_trader, account, DEMO_STOCK, 10.5, 100)
        #
        # # 等待委托回报
        # time.sleep(2)
        #
        # # 查询该委托
        # query_specific_order_demo(xt_trader, account, order_id)
        #
        # # 撤单
        # cancel_order_demo(xt_trader, account, order_id)
        
        # ============================================
        
        # 阻塞线程接收主推（实际使用时）
        # xt_trader.run_forever()
        
        print("\n演示完成")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        # 停止交易对象
        if 'xt_trader' in locals():
            xt_trader.stop()
            print("交易对象已停止")
