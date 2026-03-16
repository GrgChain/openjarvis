#!/usr/bin/env python3
"""
科技股做T策略扫描器 V3.1
历史日线(tushare pro) + 实时行情(sina) 拼接，指标基于盘中实时价格计算
"""

import json
import os
import sys
import argparse
import pandas as pd
import numpy as np
import tushare as ts
from pathlib import Path
from datetime import datetime, timedelta


def load_watchlist():
    """从 SKILL.md frontmatter 的 metadata.nanobot.watchlist 读取股票池"""
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    # 解析 YAML frontmatter 中的 metadata 行
    in_front = False
    for line in text.splitlines():
        if line.strip() == "---":
            if not in_front:
                in_front = True
                continue
            else:
                break
        if in_front and line.startswith("metadata:"):
            meta = json.loads(line[len("metadata:"):].strip())
            return meta["nanobot"]["watchlist"]
    print("Error: 无法从 SKILL.md 读取 watchlist")
    sys.exit(1)


def init_tushare():
    token = os.environ.get("TUSHARE_TOKEN", "")
    if not token:
        print("Error: TUSHARE_TOKEN 环境变量未设置")
        print("  export TUSHARE_TOKEN='your_token_here'")
        sys.exit(1)
    ts.set_token(token)
    return ts.pro_api()


def to_ts_code(code):
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def fetch_realtime(codes):
    """批量获取实时行情 (sina)，返回 {code: {open,high,low,price,volume,pre_close,time}} """
    df = ts.get_realtime_quotes(codes)
    if df is None or df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        result[row['code']] = {
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'price': float(row['price']),
            'volume': float(row['volume']),
            'pre_close': float(row['pre_close']),
            'time': row['time'],
        }
    return result


def fetch_history(pro, code, days=60):
    """获取历史日线 (不含当日)"""
    ts_code = to_ts_code(code)
    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    df = pro.daily(ts_code=ts_code, start_date=start, end_date=today)
    if df is None or df.empty:
        return None
    df = df.sort_values("trade_date").reset_index(drop=True)
    df = df.rename(columns={"vol": "volume", "pct_chg": "change_pct"})
    # 排除当日 (当日用实时数据替代)
    df = df[df['trade_date'] != today]
    return df.tail(days)


def append_realtime_bar(hist_df, rt):
    """将实时行情作为当日 bar 追加到历史数据末尾"""
    if rt['price'] <= 0:
        return hist_df
    today = datetime.now().strftime("%Y%m%d")
    change_pct = (rt['price'] / rt['pre_close'] - 1) * 100 if rt['pre_close'] > 0 else 0
    today_bar = pd.DataFrame([{
        'trade_date': today,
        'open': rt['open'],
        'high': rt['high'],
        'low': rt['low'],
        'close': rt['price'],
        'volume': rt['volume'],
        'change_pct': change_pct,
    }])
    return pd.concat([hist_df, today_bar], ignore_index=True)


# ── 技术指标 ──

def calculate_kdj(df, n=9, m1=3, m2=3):
    low_list = df['low'].rolling(window=n, min_periods=n).min()
    high_list = df['high'].rolling(window=n, min_periods=n).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['k'] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df['d'] = df['k'].ewm(com=m2 - 1, adjust=False).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    return df


def calculate_rsi(df, n=6):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd_diff'] = df['ema_fast'] - df['ema_slow']
    df['macd_dea'] = df['macd_diff'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = (df['macd_diff'] - df['macd_dea']) * 2
    return df


def calculate_bollinger(df, n=20, k=2):
    df['ma20'] = df['close'].rolling(window=n).mean()
    df['std20'] = df['close'].rolling(window=n).std()
    df['upper'] = df['ma20'] + k * df['std20']
    df['lower'] = df['ma20'] - k * df['std20']
    return df


# ── 信号判断 ──

def get_signals(df):
    last = df.iloc[-1]
    signals = []

    KDJ_OVERSOLD = 25
    KDJ_OVERBOUGHT = 80
    if last['j'] < KDJ_OVERSOLD:
        signals.append(("LONG", f"KDJ J({last['j']:.1f}) < {KDJ_OVERSOLD}"))
    elif last['j'] > KDJ_OVERBOUGHT:
        signals.append(("SHORT", f"KDJ J({last['j']:.1f}) > {KDJ_OVERBOUGHT}"))

    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    if last['rsi'] < RSI_OVERSOLD:
        signals.append(("LONG", f"RSI({last['rsi']:.1f}) < {RSI_OVERSOLD}"))
    elif last['rsi'] > RSI_OVERBOUGHT:
        signals.append(("SHORT", f"RSI({last['rsi']:.1f}) > {RSI_OVERBOUGHT}"))

    if last['close'] <= last['lower']:
        signals.append(("LONG", f"Price({last['close']:.2f}) <= BOLL下轨({last['lower']:.2f})"))
    elif last['close'] >= last['upper']:
        signals.append(("SHORT", f"Price({last['close']:.2f}) >= BOLL上轨({last['upper']:.2f})"))

    return signals


# ── 主流程 ──

def scan_stock(pro, code, name, rt):
    hist = fetch_history(pro, code)
    if hist is None or len(hist) < 30:
        return None

    df = append_realtime_bar(hist, rt)
    df = calculate_kdj(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_bollinger(df)

    signals = get_signals(df)
    last = df.iloc[-1]

    return {
        "code": code,
        "name": name,
        "price": float(last['close']),
        "change_pct": float(last['change_pct']),
        "j": float(last['j']),
        "rsi": float(last['rsi']),
        "macd_hist": float(last['macd_hist']),
        "signals": signals,
    }


def main():
    parser = argparse.ArgumentParser(description="T-Trading Scanner (realtime)")
    parser.add_argument("--symbol", type=str, help="扫描指定股票代码")
    args = parser.parse_args()

    pro = init_tushare()
    wl_config = load_watchlist()

    # 构建扫描列表
    watchlist = []
    if args.symbol:
        found = False
        for cat in wl_config.values():
            for item in cat:
                if item['code'] == args.symbol:
                    watchlist.append(item)
                    found = True
                    break
            if found:
                break
        if not found:
            watchlist.append({"code": args.symbol, "name": "Unknown"})
    else:
        for cat in wl_config.values():
            watchlist.extend(cat)

    # 批量获取实时行情
    codes = [item['code'] for item in watchlist]
    realtime = fetch_realtime(codes)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rt_time = next((v['time'] for v in realtime.values() if v['time']), "N/A")
    print(f"--- T-Trading Scan ({now}) 行情时间: {rt_time} ---")
    print(f"{'Code':<8} {'Name':<10} {'Price':>8} {'Chg%':>7} {'J':>7} {'RSI':>7}  Signals")
    print("-" * 80)

    for item in watchlist:
        code = item['code']
        rt = realtime.get(code)
        if not rt or rt['price'] <= 0:
            print(f"{code:<8} {item['name']:<10} {'N/A':>8}")
            continue
        res = scan_stock(pro, code, item['name'], rt)
        if not res:
            print(f"{code:<8} {item['name']:<10} {'N/A':>8}")
            continue
        sigs = " | ".join(f"[{s[0]}] {s[1]}" for s in res['signals']) or "-"
        print(f"{res['code']:<8} {res['name']:<10} {res['price']:>8.2f} {res['change_pct']:>+7.2f} {res['j']:>7.1f} {res['rsi']:>7.1f}  {sigs}")


if __name__ == "__main__":
    main()
