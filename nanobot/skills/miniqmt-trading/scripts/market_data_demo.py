"""
MiniQMT 行情数据获取示例
演示如何使用xtdata模块获取历史行情、实时行情、财务数据等
"""

from xtquant import xtdata
import pandas as pd
import time


def demo_download_history_data():
    """演示下载历史K线数据"""
    print("=" * 50)
    print("演示：下载历史K线数据")
    print("=" * 50)
    
    # 下载单只股票日线数据
    stock_code = '600000.SH'
    xtdata.download_history_data(
        stock_code=stock_code,
        period='1d',
        start_time='20240101',
        end_time='',
        incrementally=False
    )
    print(f"已下载 {stock_code} 的日线数据")
    
    # 下载多只股票数据
    stock_list = ['000001.SZ', '000002.SZ']
    for code in stock_list:
        xtdata.download_history_data(code, period='1d', start_time='20240101')
    print(f"已下载 {len(stock_list)} 只股票的日线数据")


def demo_get_market_data():
    """演示获取行情数据"""
    print("\n" + "=" * 50)
    print("演示：获取行情数据")
    print("=" * 50)
    
    # 先下载数据
    stock_code = '600000.SH'
    xtdata.download_history_data(stock_code, period='1d', start_time='20240101')
    
    # 获取日线数据
    data = xtdata.get_market_data(
        field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[stock_code],
        period='1d',
        start_time='20240101',
        count=-1,
        dividend_type='front_ratio'
    )
    
    print(f"获取到字段: {list(data.keys())}")
    print(f"收盘价数据:\n{data['close']}")
    
    # 使用get_market_data_ex获取数据
    data_ex = xtdata.get_market_data_ex(
        field_list=['open', 'high', 'low', 'close', 'volume'],
        stock_list=[stock_code],
        period='1d',
        start_time='20240101'
    )
    
    print(f"\n使用get_market_data_ex获取的数据:")
    print(data_ex[stock_code].head())


def demo_get_full_tick():
    """演示获取全推数据（分笔数据）"""
    print("\n" + "=" * 50)
    print("演示：获取全推数据")
    print("=" * 50)
    
    stock_list = ['600000.SH', '000001.SZ']
    tick_data = xtdata.get_full_tick(stock_list)
    
    for code, data in tick_data.items():
        print(f"\n股票: {code}")
        print(f"  最新价: {data.get('lastPrice', 'N/A')}")
        print(f"  开盘价: {data.get('open', 'N/A')}")
        print(f"  最高价: {data.get('high', 'N/A')}")
        print(f"  最低价: {data.get('low', 'N/A')}")
        print(f"  成交量: {data.get('volume', 'N/A')}")
        
        # 买卖五档
        bid_prices = data.get('bidPrice', [])
        bid_vols = data.get('bidVol', [])
        ask_prices = data.get('askPrice', [])
        ask_vols = data.get('askVol', [])
        
        print(f"  买一: {bid_prices[0] if bid_prices else 'N/A'} / {bid_vols[0] if bid_vols else 'N/A'}")
        print(f"  卖一: {ask_prices[0] if ask_prices else 'N/A'} / {ask_vols[0] if ask_vols else 'N/A'}")


def demo_subscribe_quote():
    """演示订阅实时行情"""
    print("\n" + "=" * 50)
    print("演示：订阅实时行情")
    print("=" * 50)
    
    # 定义回调函数
    def on_data(datas):
        for stock_code, data_list in datas.items():
            print(f"收到 {stock_code} 的数据更新，共 {len(data_list)} 条")
            if data_list:
                print(f"  最新数据: {data_list[-1]}")
    
    # 订阅单股行情
    stock_code = '600000.SH'
    seq = xtdata.subscribe_quote(
        stock_code=stock_code,
        period='1m',
        start_time='',
        end_time='',
        count=0,
        callback=on_data
    )
    
    print(f"订阅成功，订阅号: {seq}")
    
    # 等待接收数据（实际使用时用xtdata.run()阻塞）
    print("等待3秒接收数据...")
    time.sleep(3)
    
    # 反订阅
    xtdata.unsubscribe_quote(seq)
    print("已反订阅")


def demo_sector_data():
    """演示板块数据获取"""
    print("\n" + "=" * 50)
    print("演示：板块数据获取")
    print("=" * 50)
    
    # 下载板块数据
    xtdata.download_sector_data()
    
    # 获取板块列表
    sector_list = xtdata.get_sector_list()
    print(f"共有 {len(sector_list)} 个板块")
    
    # 显示部分板块
    print("\n部分板块列表:")
    for sector in sector_list[:10]:
        print(f"  {sector}")
    
    # 获取沪深A股列表
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"\n沪深A股共有 {len(stocks)} 只股票")
    print(f"前5只: {stocks[:5]}")
    
    # 获取申万一级行业成分股
    try:
        sw_stocks = xtdata.get_stock_list_in_sector('SW1银行')
        print(f"\n银行行业共有 {len(sw_stocks)} 只股票")
        print(f"前5只: {sw_stocks[:5]}")
    except:
        print("\n银行行业数据获取失败")


def demo_financial_data():
    """演示财务数据获取"""
    print("\n" + "=" * 50)
    print("演示：财务数据获取")
    print("=" * 50)
    
    stock_code = '600000.SH'
    
    # 下载财务数据
    xtdata.download_financial_data([stock_code])
    
    # 获取财务数据
    financial_data = xtdata.get_financial_data(
        stock_list=[stock_code],
        table_list=['BalanceSheet', 'IncomeStatement']
    )
    
    print(f"获取到 {len(financial_data)} 只股票的财务数据")
    
    if stock_code in financial_data:
        data = financial_data[stock_code]
        print(f"\n{stock_code} 的财务报表:")
        for table_name, table_data in data.items():
            print(f"\n{table_name}:")
            if isinstance(table_data, pd.DataFrame):
                print(table_data.head())
            else:
                print(table_data)


def demo_instrument_info():
    """演示合约信息获取"""
    print("\n" + "=" * 50)
    print("演示：合约信息获取")
    print("=" * 50)
    
    stock_code = '600000.SH'
    info = xtdata.get_instrument_detail(stock_code)
    
    print(f"\n{stock_code} 的合约信息:")
    key_fields = [
        'InstrumentName', 'InstrumentCode', 'ExchangeCode',
        'ProductType', 'PriceTick', 'UpperLimitPrice', 
        'LowerLimitPrice', 'VolumeMultiple'
    ]
    
    for key in key_fields:
        if key in info:
            print(f"  {key}: {info[key]}")


def demo_trading_calendar():
    """演示交易日历获取"""
    print("\n" + "=" * 50)
    print("演示：交易日历获取")
    print("=" * 50)
    
    # 获取交易日列表
    trading_dates = xtdata.get_trading_dates(
        start_time='20240101',
        end_time='20241231'
    )
    print(f"2024年共有 {len(trading_dates)} 个交易日")
    print(f"前10个交易日: {trading_dates[:10]}")
    
    # 获取节假日
    holidays = xtdata.get_holidays(
        start_time='20240101',
        end_time='20241231'
    )
    print(f"\n2024年共有 {len(holidays)} 个节假日")


def demo_dividend_data():
    """演示除权除息数据"""
    print("\n" + "=" * 50)
    print("演示：除权除息数据")
    print("=" * 50)
    
    stock_code = '600000.SH'
    divid_factors = xtdata.get_divid_factors(stock_code)
    
    print(f"\n{stock_code} 的除权因子:")
    print(divid_factors.head(10))


if __name__ == '__main__':
    # 设置不显示欢迎信息
    xtdata.enable_hello = False
    
    # 运行所有演示
    demo_download_history_data()
    demo_get_market_data()
    demo_get_full_tick()
    demo_sector_data()
    demo_financial_data()
    demo_instrument_info()
    demo_trading_calendar()
    demo_dividend_data()
    
    print("\n" + "=" * 50)
    print("所有演示完成")
    print("=" * 50)
