"""
MiniQMT 批量数据下载示例
演示如何批量下载股票行情数据、财务数据等
"""

from xtquant import xtdata
from multiprocessing import Process
import time
import pandas as pd


def download_sector_info():
    """下载行业板块数据"""
    print("下载行业板块数据...")
    # 使用client方法下载，避免卡死问题
    client = xtdata.get_client()
    client.down_all_sector_data()
    print("行业板块数据下载完成")


def get_all_stock_list(include_bj=True):
    """
    获取所有股票列表
    
    Args:
        include_bj: 是否包含北交所股票
    
    Returns:
        股票代码列表
    """
    # 获取沪深A股
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    
    if include_bj:
        # 获取北交所股票
        bj_stocks = xtdata.get_stock_list_in_sector('BJ')
        stock_list.extend(bj_stocks)
    
    print(f"获取到 {len(stock_list)} 只股票")
    return stock_list


def download_single_stock(stock_code, period, start_time, end_time=''):
    """
    下载单只股票的历史数据
    
    Args:
        stock_code: 股票代码
        period: 周期
        start_time: 开始时间
        end_time: 结束时间
    """
    try:
        xtdata.download_history_data(
            stock_code=stock_code,
            period=period,
            start_time=start_time,
            end_time=end_time
        )
        return True
    except Exception as e:
        print(f"下载 {stock_code} 失败: {e}")
        return False


def download_stock_group(stock_group, period, start_time, end_time=''):
    """
    下载一组股票的历史数据
    
    Args:
        stock_group: 股票代码列表
        period: 周期
        start_time: 开始时间
        end_time: 结束时间
    """
    xtdata.enable_hello = False
    
    for stock_code in stock_group:
        download_single_stock(stock_code, period, start_time, end_time)


def download_stock_group_increment(stock_group, period):
    """
    增量下载一组股票的历史数据
    
    Args:
        stock_group: 股票代码列表
        period: 周期
    """
    xtdata.enable_hello = False
    
    for stock_code in stock_group:
        try:
            xtdata.download_history_data(
                stock_code=stock_code,
                period=period,
                incrementally=True
            )
        except Exception as e:
            print(f"增量下载 {stock_code} 失败: {e}")


def multi_download(stock_pool, period, start_time='', end_time='', group_size=500):
    """
    多进程批量下载历史数据
    
    Args:
        stock_pool: 股票代码列表
        period: 周期
        start_time: 开始时间
        end_time: 结束时间
        group_size: 每组股票数量
    """
    # 分组
    stock_groups = []
    for i in range(0, len(stock_pool), group_size):
        group = stock_pool[i:i + group_size]
        stock_groups.append(group)
    
    print(f"将 {len(stock_pool)} 只股票分为 {len(stock_groups)} 组，每组约 {group_size} 只")
    
    # 创建进程
    processes = []
    for i, group in enumerate(stock_groups):
        print(f"创建第 {i+1} 组下载进程...")
        p = Process(
            target=download_stock_group,
            args=(group, period, start_time, end_time)
        )
        p.start()
        processes.append(p)
    
    # 等待所有进程完成
    for i, p in enumerate(processes):
        p.join()
        print(f"第 {i+1} 组下载完成")
    
    print("所有数据下载完成")


def multi_download_increment(stock_pool, period, group_size=500):
    """
    多进程增量下载历史数据
    
    Args:
        stock_pool: 股票代码列表
        period: 周期
        group_size: 每组股票数量
    """
    # 分组
    stock_groups = []
    for i in range(0, len(stock_pool), group_size):
        group = stock_pool[i:i + group_size]
        stock_groups.append(group)
    
    print(f"将 {len(stock_pool)} 只股票分为 {len(stock_groups)} 组")
    
    # 创建进程
    processes = []
    for i, group in enumerate(stock_groups):
        print(f"创建第 {i+1} 组下载进程...")
        p = Process(
            target=download_stock_group_increment,
            args=(group, period)
        )
        p.start()
        processes.append(p)
    
    # 等待所有进程完成
    for i, p in enumerate(processes):
        p.join()
        print(f"第 {i+1} 组下载完成")
    
    print("所有数据下载完成")


def first_time_download():
    """首次全量下载数据"""
    print("=" * 60)
    print("首次全量下载数据")
    print("=" * 60)
    
    t_begin = time.time()
    
    # 设置不显示欢迎信息
    xtdata.enable_hello = False
    
    # 下载板块数据
    download_sector_info()
    
    # 获取股票列表
    stock_pool = get_all_stock_list(include_bj=True)
    
    # 下载日线数据（从1990年开始）
    period = '1d'
    start_time = '19900101'
    end_time = ''
    
    print(f"\n开始下载日线数据...")
    multi_download(stock_pool, period, start_time, end_time)
    
    t_end = time.time()
    print(f"\n下载完成，总耗时: {t_end - t_begin:.2f} 秒")


def daily_increment_download():
    """每日增量下载数据"""
    print("=" * 60)
    print("每日增量下载数据")
    print("=" * 60)
    
    t_begin = time.time()
    
    # 设置不显示欢迎信息
    xtdata.enable_hello = False
    
    # 下载板块数据
    download_sector_info()
    
    # 获取股票列表
    stock_pool = get_all_stock_list(include_bj=True)
    
    # 增量下载日线数据
    period = '1d'
    
    print(f"\n开始增量下载日线数据...")
    multi_download_increment(stock_pool, period)
    
    t_end = time.time()
    print(f"\n下载完成，总耗时: {t_end - t_begin:.2f} 秒")


def download_financial_data_all(stock_list):
    """
    下载所有财务数据
    
    Args:
        stock_list: 股票代码列表
    """
    print("=" * 60)
    print("下载财务数据")
    print("=" * 60)
    
    xtdata.enable_hello = False
    
    # 分批下载
    batch_size = 100
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        print(f"下载第 {i//batch_size + 1} 批财务数据 ({len(batch)} 只)...")
        xtdata.download_financial_data(batch)
    
    print("财务数据下载完成")


def download_minute_data(stock_list, periods=['1m', '5m']):
    """
    下载分钟线数据
    
    Args:
        stock_list: 股票代码列表
        periods: 周期列表
    """
    print("=" * 60)
    print("下载分钟线数据")
    print("=" * 60)
    
    xtdata.enable_hello = False
    
    for period in periods:
        print(f"\n下载 {period} 数据...")
        for i, stock_code in enumerate(stock_list):
            if (i + 1) % 100 == 0:
                print(f"  已下载 {i+1}/{len(stock_list)}")
            xtdata.download_history_data(
                stock_code=stock_code,
                period=period,
                start_time='20240101',
                incrementally=True
            )
    
    print("分钟线数据下载完成")


def get_hq_data(code, start_time, end_time, period='1d', dividend_type='front_ratio'):
    """
    获取行情数据并转换为DataFrame
    
    Args:
        code: 股票代码
        start_time: 开始时间
        end_time: 结束时间
        period: 周期
        dividend_type: 复权方式
    
    Returns:
        DataFrame
    """
    xtdata.enable_hello = False
    
    history_data = xtdata.get_market_data_ex(
        ['open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[code],
        period=period,
        start_time=start_time,
        end_time=end_time,
        dividend_type=dividend_type,
        fill_data=False
    )
    
    df = history_data[code]
    
    # 转换时间格式
    if 'd' in period:
        df.index = pd.to_datetime(df.index.astype(str), format='%Y%m%d')
    elif 'm' in period or 'h' in period:
        df.index = pd.to_datetime(df.index.astype(str), format='%Y%m%d%H%M%S')
    
    df['date'] = df.index
    
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]


def download_etf_list():
    """下载ETF申赎清单数据"""
    print("=" * 60)
    print("下载ETF申赎清单数据")
    print("=" * 60)
    
    xtdata.enable_hello = False
    xtdata.download_etf_info()
    print("ETF数据下载完成")


def download_cb_data_all():
    """下载可转债数据"""
    print("=" * 60)
    print("下载可转债数据")
    print("=" * 60)
    
    xtdata.enable_hello = False
    xtdata.download_cb_data()
    print("可转债数据下载完成")


if __name__ == '__main__':
    # ============================================
    # 选择下载模式
    # ============================================
    
    # 首次全量下载（时间较长）
    is_first_download = False
    
    # 每日增量下载
    is_daily_increment = True
    
    # 下载财务数据
    download_financial = False
    
    # 下载分钟线数据
    download_minute = False
    
    # ============================================
    
    if is_first_download:
        first_time_download()
    
    if is_daily_increment:
        daily_increment_download()
    
    if download_financial:
        stock_list = get_all_stock_list(include_bj=True)
        download_financial_data_all(stock_list[:1000])  # 只下载前1000只
    
    if download_minute:
        stock_list = get_all_stock_list(include_bj=True)
        download_minute_data(stock_list[:100])  # 只下载前100只
    
    print("\n所有任务完成")
