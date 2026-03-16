#!/usr/bin/env python3
"""
科技股做T策略扫描器 V4.0
历史日线(tushare pro) + 实时行情(sina) 拼接，综合评分系统
支持 --json 结构化输出
"""

import json
import os
import sys
import argparse
import traceback
import pandas as pd
import numpy as np
import tushare as ts
from pathlib import Path
from datetime import datetime, timedelta


# ── 配置 ──

TIME_WINDOWS = [
    ("09:30", "10:00", "观察期",       False, "避免开盘波动"),
    ("10:00", "10:30", "黄金窗口1",    True,  "第一黄金窗口：正T/倒T"),
    ("10:30", "13:30", "观察期",       False, "少操作"),
    ("13:30", "14:00", "黄金窗口2",    True,  "第二黄金窗口：正T/倒T"),
    ("14:00", "14:30", "减仓期",       True,  "逐步降低仓位"),
    ("14:30", "15:00", "禁止新开",     False, "只平仓，不新开"),
]


def load_watchlist():
    """从 SKILL.md frontmatter 的 metadata.nanobot.watchlist 读取股票池"""
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error: 无法读取 SKILL.md: {e}")
        sys.exit(1)
    in_front = False
    for line in text.splitlines():
        if line.strip() == "---":
            if not in_front:
                in_front = True
                continue
            else:
                break
        if in_front and line.startswith("metadata:"):
            try:
                meta = json.loads(line[len("metadata:"):].strip())
                return meta["nanobot"]["watchlist"]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error: SKILL.md metadata 解析失败: {e}")
                sys.exit(1)
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


# ── 时间窗口 ──

def classify_time_window(time_str):
    """根据行情时间返回当前所处窗口"""
    try:
        parts = time_str.strip().split(":")
        hh, mm = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return {"window": "unknown", "tradeable": False, "label": "无法解析时间"}

    t = f"{hh:02d}:{mm:02d}"

    if t < "09:30":
        return {"window": "pre_market", "tradeable": False, "label": "盘前"}
    if t >= "15:00":
        return {"window": "post_market", "tradeable": False, "label": "盘后"}
    # 午休
    if "11:30" <= t < "13:00":
        return {"window": "lunch_break", "tradeable": False, "label": "午休"}

    for start, end, name, tradeable, desc in TIME_WINDOWS:
        if start <= t < end:
            return {"window": name, "tradeable": tradeable, "label": desc}

    return {"window": "other", "tradeable": False, "label": "非交易窗口"}


# ── 数据获取 ──

def fetch_realtime(codes):
    """批量获取实时行情 (sina)，返回 {code: {open,high,low,price,volume,pre_close,time}}"""
    try:
        df = ts.get_realtime_quotes(codes)
        if df is None or df.empty:
            return {}
    except Exception as e:
        print(f"Warning: 实时行情获取失败: {e}")
        return {}
    result = {}
    for _, row in df.iterrows():
        try:
            result[row['code']] = {
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'price': float(row['price']),
                'volume': float(row['volume']),
                'pre_close': float(row['pre_close']),
                'time': row['time'],
            }
        except (ValueError, KeyError):
            continue
    return result


def fetch_history(pro, code, days=90):
    """获取历史日线 (不含当日)，默认90天确保足够计算MA60"""
    ts_code = to_ts_code(code)
    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    try:
        df = pro.daily(ts_code=ts_code, start_date=start, end_date=today)
        if df is None or df.empty:
            return None
    except Exception as e:
        print(f"Warning: 历史数据获取失败 ({code}): {e}")
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


def calculate_ma60(df):
    df['ma60'] = df['close'].rolling(window=60).mean()
    return df


# ── 量比计算 ──

def calculate_volume_ratio(hist_df, rt):
    """计算量比：当日实时量 / 20日均量
    注意：sina 返回股数，tushare vol 单位是手（1手=100股），需要转换
    """
    # hist_df volume 已被 rename，单位是手(tushare)
    recent = hist_df.tail(20)
    if len(recent) < 5:
        return {"volume_ratio": 0.0, "current_vol": 0.0, "avg_20d_vol": 0.0}

    avg_20d_vol = recent['volume'].mean()  # 单位: 手
    # sina 实时 volume 是股数，转手
    current_vol = rt['volume'] / 100.0

    if avg_20d_vol <= 0:
        return {"volume_ratio": 0.0, "current_vol": current_vol, "avg_20d_vol": 0.0}

    volume_ratio = current_vol / avg_20d_vol
    return {
        "volume_ratio": round(volume_ratio, 2),
        "current_vol": round(current_vol, 0),
        "avg_20d_vol": round(avg_20d_vol, 0),
    }


# ── 禁止条件检查 ──

def check_forbidden_conditions(df, rt, code):
    """检查 SKILL.md 定义的禁止做T条件，返回警告列表"""
    warnings = []
    last = df.iloc[-1]

    # 1. 股价低于 MA60
    if pd.notna(last.get('ma60')) and last['close'] < last['ma60']:
        warnings.append(f"股价({last['close']:.2f})低于MA60({last['ma60']:.2f})")

    # 2. 低开 >4%
    if rt['pre_close'] > 0:
        gap_pct = (rt['open'] / rt['pre_close'] - 1) * 100
        if gap_pct < -4:
            warnings.append(f"低开{gap_pct:.1f}%，超过-4%阈值")

    # 3. 接近涨跌停
    if rt['pre_close'] > 0:
        # 688开头科创板 ±20%，其余 ±10%
        limit_pct = 20.0 if code.startswith("688") else 10.0
        upper_limit = rt['pre_close'] * (1 + limit_pct / 100)
        lower_limit = rt['pre_close'] * (1 - limit_pct / 100)
        price = rt['price']
        if price > 0:
            dist_upper = (upper_limit - price) / upper_limit * 100
            dist_lower = (price - lower_limit) / lower_limit * 100
            if dist_upper < 1:
                warnings.append(f"接近涨停(距{dist_upper:.1f}%)")
            if dist_lower < 1:
                warnings.append(f"接近跌停(距{dist_lower:.1f}%)")

    # 4. 量能严重萎缩（量比 <0.2）
    # volume_ratio is checked via the vr passed in scan_stock, but we also
    # check here from raw data for self-containment
    recent = df.iloc[:-1].tail(20)
    if len(recent) >= 5:
        avg_vol = recent['volume'].mean()
        if avg_vol > 0:
            # current bar volume (already in same unit after append_realtime_bar)
            current_vol = last['volume']
            vr = current_vol / avg_vol if avg_vol > 0 else 0
            if vr < 0.2:
                warnings.append(f"量能严重萎缩(量比{vr:.2f})")

    return warnings


# ── 综合评分 ──

def get_composite_signal(df, volume_ratio):
    """综合评分系统，替代独立信号
    总分范围 -100 ~ +100
    ≥20 → LONG, ≤-20 → SHORT, 其余 NEUTRAL
    """
    last = df.iloc[-1]
    score = 0
    details = []

    # KDJ 评分 (±30)
    j = last['j']
    if j < 25:
        kdj_score = 30
        details.append(f"KDJ J={j:.1f}<25 → +30")
    elif j > 80:
        kdj_score = -30
        details.append(f"KDJ J={j:.1f}>80 → -30")
    elif j < 50:
        # 线性梯度: 25~50 → 30~0
        kdj_score = int(30 * (50 - j) / 25)
        details.append(f"KDJ J={j:.1f} → +{kdj_score}")
    else:
        # 线性梯度: 50~80 → 0~-30
        kdj_score = -int(30 * (j - 50) / 30)
        details.append(f"KDJ J={j:.1f} → {kdj_score}")
    score += kdj_score

    # RSI 评分 (±25)
    rsi = last['rsi']
    if pd.isna(rsi):
        rsi_score = 0
    elif rsi < 30:
        rsi_score = 25
        details.append(f"RSI={rsi:.1f}<30 → +25")
    elif rsi > 70:
        rsi_score = -25
        details.append(f"RSI={rsi:.1f}>70 → -25")
    elif rsi < 50:
        rsi_score = int(25 * (50 - rsi) / 20)
        details.append(f"RSI={rsi:.1f} → +{rsi_score}")
    else:
        rsi_score = -int(25 * (rsi - 50) / 20)
        details.append(f"RSI={rsi:.1f} → {rsi_score}")
    score += rsi_score

    # BOLL 评分 (±25)
    close = last['close']
    upper = last.get('upper', None)
    lower = last.get('lower', None)
    ma20 = last.get('ma20', None)
    boll_score = 0
    if pd.notna(lower) and pd.notna(upper) and pd.notna(ma20):
        boll_width = upper - lower
        if boll_width > 0:
            if close <= lower:
                boll_score = 25
                details.append(f"触BOLL下轨 → +25")
            elif close >= upper:
                boll_score = -25
                details.append(f"触BOLL上轨 → -25")
            else:
                # 距中轨的比例
                mid_dist = (close - ma20) / (boll_width / 2)
                boll_score = -int(25 * max(-1, min(1, mid_dist)))
                if boll_score != 0:
                    details.append(f"BOLL位置 → {boll_score:+d}")
    score += boll_score

    # 量比确认 (±20)
    vr = volume_ratio
    vol_score = 0
    if vr > 0:
        direction = 1 if score > 0 else (-1 if score < 0 else 0)
        if direction != 0:
            if (direction > 0 and vr < 1.0) or (direction < 0 and vr > 1.5):
                # 方向一致量能配合
                vol_score = 20 * direction
                details.append(f"量比{vr:.2f}配合 → {vol_score:+d}")
            elif (direction > 0 and vr > 2.0) or (direction < 0 and vr < 0.5):
                # 量能不配合
                vol_score = -10 * direction
                details.append(f"量比{vr:.2f}不配合 → {vol_score:+d}")
    score += vol_score

    # 方向判定
    if score >= 20:
        direction = "LONG"
    elif score <= -20:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    # 兼容旧版文本信号
    legacy_signals = _get_legacy_signals(last)

    return {
        "score": int(score),
        "direction": direction,
        "details": details,
        "legacy_signals": legacy_signals,
    }


def _get_legacy_signals(last):
    """兼容旧版独立信号列表"""
    signals = []
    if last['j'] < 25:
        signals.append(("LONG", f"KDJ J({last['j']:.1f}) < 25"))
    elif last['j'] > 80:
        signals.append(("SHORT", f"KDJ J({last['j']:.1f}) > 80"))

    rsi = last['rsi']
    if pd.notna(rsi):
        if rsi < 30:
            signals.append(("LONG", f"RSI({rsi:.1f}) < 30"))
        elif rsi > 70:
            signals.append(("SHORT", f"RSI({rsi:.1f}) > 70"))

    if pd.notna(last.get('lower')) and last['close'] <= last['lower']:
        signals.append(("LONG", f"Price({last['close']:.2f}) <= BOLL下轨({last['lower']:.2f})"))
    elif pd.notna(last.get('upper')) and last['close'] >= last['upper']:
        signals.append(("SHORT", f"Price({last['close']:.2f}) >= BOLL上轨({last['upper']:.2f})"))

    return signals


# ── 过期检测 ──

def check_stale(rt_time_str):
    """检查行情时间是否过期（距当前 >30 分钟）"""
    try:
        now = datetime.now()
        parts = rt_time_str.strip().split(":")
        rt_dt = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]))
        delta = abs((now - rt_dt).total_seconds())
        return delta > 1800
    except Exception:
        return True


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
    df = calculate_ma60(df)

    # 量比
    vr_info = calculate_volume_ratio(hist, rt)

    # 综合评分
    signal = get_composite_signal(df, vr_info['volume_ratio'])

    # 禁止条件
    warnings = check_forbidden_conditions(df, rt, code)

    last = df.iloc[-1]

    return {
        "code": code,
        "name": name,
        "price": float(last['close']),
        "change_pct": float(last['change_pct']),
        "j": float(last['j']),
        "rsi": float(last['rsi']) if pd.notna(last['rsi']) else 0.0,
        "macd_hist": float(last['macd_hist']) if pd.notna(last['macd_hist']) else 0.0,
        "volume_ratio": vr_info['volume_ratio'],
        "signal": signal,
        "warnings": warnings,
    }


def _json_default(obj):
    """JSON serializer for numpy types"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def main():
    parser = argparse.ArgumentParser(description="T-Trading Scanner (realtime)")
    parser.add_argument("--symbol", type=str, help="扫描指定股票代码")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="JSON 结构化输出")
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
    tw = classify_time_window(rt_time)
    is_stale = check_stale(rt_time) if rt_time != "N/A" else True

    # 扫描所有股票
    results = []
    for item in watchlist:
        code = item['code']
        rt = realtime.get(code)
        if not rt or rt['price'] <= 0:
            results.append({"code": code, "name": item['name'], "error": "无实时数据"})
            continue
        res = scan_stock(pro, code, item['name'], rt)
        if not res:
            results.append({"code": code, "name": item['name'], "error": "历史数据不足"})
            continue
        results.append(res)

    # ── JSON 模式输出 ──
    if args.json_mode:
        output = {
            "scan_time": now,
            "quote_time": rt_time,
            "stale": is_stale,
            "time_window": tw,
            "stocks": results,
            "summary": {
                "total": len(results),
                "long": sum(1 for r in results if r.get("signal", {}).get("direction") == "LONG"),
                "short": sum(1 for r in results if r.get("signal", {}).get("direction") == "SHORT"),
                "neutral": sum(1 for r in results if r.get("signal", {}).get("direction") == "NEUTRAL"),
                "warnings": sum(1 for r in results if r.get("warnings")),
                "errors": sum(1 for r in results if r.get("error")),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, default=_json_default))
        return

    # ── 文本模式输出 ──
    stale_tag = " [行情可能过期]" if is_stale else ""
    print(f"--- T-Trading Scan ({now}) 行情时间: {rt_time}{stale_tag} ---")
    print(f"    时间窗口: [{tw['window']}] {tw['label']} | 可交易: {'是' if tw['tradeable'] else '否'}")
    print(f"{'Code':<8} {'Name':<10} {'Price':>8} {'Chg%':>7} {'J':>7} {'RSI':>7} {'VR':>6} {'Score':>6} {'Dir':<8} Signals")
    print("-" * 100)

    all_warnings = []
    for res in results:
        code = res['code']
        name = res['name']
        if res.get('error'):
            print(f"{code:<8} {name:<10} {'N/A':>8}  {res['error']}")
            continue

        sig = res['signal']
        legacy = " | ".join(f"[{s[0]}] {s[1]}" for s in sig['legacy_signals']) or "-"
        dir_str = sig['direction']
        print(f"{code:<8} {name:<10} {res['price']:>8.2f} {res['change_pct']:>+7.2f} "
              f"{res['j']:>7.1f} {res['rsi']:>7.1f} {res['volume_ratio']:>6.2f} "
              f"{sig['score']:>+6d} {dir_str:<8} {legacy}")

        if res.get('warnings'):
            for w in res['warnings']:
                all_warnings.append(f"  ⚠ {code} {name}: {w}")

    if all_warnings:
        print()
        print("=== 禁止/警告条件 ===")
        for w in all_warnings:
            print(w)


if __name__ == "__main__":
    main()
