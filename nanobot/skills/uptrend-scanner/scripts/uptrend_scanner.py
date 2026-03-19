#!/usr/bin/env python3
"""
上升趋势股票扫描器 (Uptrend Stock Scanner)

从本地 K 线 CSV 数据中扫描处于上升趋势的股票，基于多维度技术指标综合评分。

维度:
  1. 均线多头排列  (MA alignment)      - 25%
  2. 价格站上均线  (Price above MA)     - 20%
  3. 均线斜率      (MA slope)           - 20%
  4. MACD 趋势    (MACD trend)         - 20%
  5. 量价配合      (Volume-price)       - 15%
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(cfg_path: Path) -> Dict[str, Any]:
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as f:
            return json.load(f)
    # defaults
    return {
        "ma_periods": {"short": 5, "mid": 10, "long": 20, "extra_long": 60},
        "weights": {
            "ma_alignment": 0.25,
            "price_above_ma": 0.20,
            "ma_slope": 0.20,
            "macd_trend": 0.20,
            "volume_price": 0.15,
        },
        "slope_lookback_days": 10,
        "macd_params": {"fast": 12, "slow": 26, "signal": 9},
        "volume_lookback_days": 10,
        "min_data_days": 120,
        "tiers": {"strong": 80, "uptrend": 60, "neutral": 40},
    }

# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def compute_mas(close: pd.Series, periods: Dict[str, int]) -> Dict[str, pd.Series]:
    """计算各周期均线"""
    return {k: close.rolling(window=v, min_periods=v).mean() for k, v in periods.items()}


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple:
    """返回 (DIF, DEA, MACD_hist)"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2 * (dif - dea)
    return dif, dea, macd_hist


def linear_slope(series: pd.Series, days: int) -> float:
    """计算最近 days 个点的线性回归斜率"""
    if len(series) < days:
        return 0.0
    y = series.tail(days).values
    if np.any(np.isnan(y)):
        return 0.0
    x = np.arange(days, dtype=float)
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)

# ---------------------------------------------------------------------------
# Scoring Dimensions
# ---------------------------------------------------------------------------

def score_ma_alignment(close_val: float, mas: Dict[str, float]) -> tuple:
    """
    均线多头排列评分。
    完美排列: MA5 > MA10 > MA20 > MA60 => 100
    每缺一层扣 25 分。
    """
    vals = [mas.get("short"), mas.get("mid"), mas.get("long"), mas.get("extra_long")]
    if any(v is None or np.isnan(v) for v in vals):
        return 0.0, []

    pairs = list(zip(vals, vals[1:]))  # (MA5,MA10), (MA10,MA20), (MA20,MA60)
    aligned_count = sum(1 for a, b in pairs if a > b)

    score = (aligned_count / len(pairs)) * 100.0

    tags = []
    if aligned_count == len(pairs):
        tags.append("均线多头")
    return score, tags


def score_price_above_ma(close_val: float, mas: Dict[str, float]) -> tuple:
    """价格站上均线评分: 收盘价 > MA20 (50 分) + 收盘价 > MA60 (50 分)"""
    score = 0.0
    tags = []
    ma20 = mas.get("long")
    ma60 = mas.get("extra_long")

    if ma20 is not None and not np.isnan(ma20) and close_val > ma20:
        score += 50.0
    if ma60 is not None and not np.isnan(ma60) and close_val > ma60:
        score += 50.0
        tags.append("价格站上MA60")
    return score, tags


def score_ma_slope(mas_series: Dict[str, pd.Series], lookback: int) -> tuple:
    """
    均线斜率评分。
    MA20 斜率 > 0 得 50 分；MA60 斜率 > 0 得 50 分。
    """
    score = 0.0
    tags = []
    ma20 = mas_series.get("long")
    ma60 = mas_series.get("extra_long")

    if ma20 is not None:
        s20 = linear_slope(ma20, lookback)
        if s20 > 0:
            score += 50.0
            tags.append("MA20上行")
    if ma60 is not None:
        s60 = linear_slope(ma60, lookback)
        if s60 > 0:
            score += 50.0
            tags.append("MA60上行")
    return score, tags


def score_macd_trend(dif_val: float, dea_val: float, hist_val: float, prev_hist: float) -> tuple:
    """
    MACD 趋势评分:
      - DIF > 0        => 30 分
      - DIF > DEA       => 30 分 (金叉状态)
      - MACD 柱 > 0     => 20 分
      - MACD 柱递增      => 20 分
    """
    score = 0.0
    tags = []

    if np.isnan(dif_val) or np.isnan(dea_val) or np.isnan(hist_val):
        return 0.0, tags

    if dif_val > 0:
        score += 30.0
    if dif_val > dea_val:
        score += 30.0
        tags.append("MACD金叉")
    if hist_val > 0:
        score += 20.0
    if not np.isnan(prev_hist) and hist_val > prev_hist:
        score += 20.0
    return score, tags


def score_volume_price(df: pd.DataFrame, lookback: int) -> tuple:
    """
    量价配合评分。
    在最近 lookback 天内:
      - 上涨日成交量均值 > 下跌日成交量均值 => 50 分
      - 总体量能趋势向上 (成交量斜率 > 0)   => 50 分
    """
    score = 0.0
    tags = []

    if len(df) < lookback:
        return 0.0, tags

    recent = df.tail(lookback).copy()
    recent["pct_chg"] = recent["close"].pct_change()

    up_days = recent[recent["pct_chg"] > 0]
    down_days = recent[recent["pct_chg"] < 0]

    if len(up_days) > 0 and len(down_days) > 0:
        avg_up_vol = up_days["volume"].mean()
        avg_down_vol = down_days["volume"].mean()
        if avg_up_vol > avg_down_vol:
            score += 50.0
            tags.append("量价齐升")

    vol_slope = linear_slope(recent["volume"], lookback)
    if vol_slope > 0:
        score += 50.0

    return score, tags

# ---------------------------------------------------------------------------
# Main Scanner
# ---------------------------------------------------------------------------

def scan_stock(code: str, df: pd.DataFrame, cfg: Dict[str, Any]) -> Optional[Dict]:
    """对单只股票计算上升趋势评分"""
    min_days = cfg.get("min_data_days", 120)
    if len(df) < min_days:
        return None

    periods = cfg["ma_periods"]
    weights = cfg["weights"]
    slope_lb = cfg.get("slope_lookback_days", 10)
    vol_lb = cfg.get("volume_lookback_days", 10)
    macd_p = cfg.get("macd_params", {})

    close = df["close"].astype(float)
    close_val = float(close.iloc[-1])

    # 计算指标
    mas_series = compute_mas(close, periods)
    mas_latest = {k: float(v.iloc[-1]) if pd.notna(v.iloc[-1]) else np.nan for k, v in mas_series.items()}
    dif, dea, hist = compute_macd(close, macd_p.get("fast", 12), macd_p.get("slow", 26), macd_p.get("signal", 9))

    # 各维度评分
    s1, t1 = score_ma_alignment(close_val, mas_latest)
    s2, t2 = score_price_above_ma(close_val, mas_latest)
    s3, t3 = score_ma_slope(mas_series, slope_lb)
    s4, t4 = score_macd_trend(
        float(dif.iloc[-1]), float(dea.iloc[-1]),
        float(hist.iloc[-1]), float(hist.iloc[-2]) if len(hist) >= 2 else np.nan,
    )
    s5, t5 = score_volume_price(df, vol_lb)

    # 加权总分
    total = (
        s1 * weights["ma_alignment"]
        + s2 * weights["price_above_ma"]
        + s3 * weights["ma_slope"]
        + s4 * weights["macd_trend"]
        + s5 * weights["volume_price"]
    )

    # 合并 tags
    all_tags = t1 + t2 + t3 + t4 + t5

    # 趋势分级
    tiers = cfg.get("tiers", {"strong": 80, "uptrend": 60, "neutral": 40})
    if total >= tiers["strong"]:
        tier = "强上升趋势"
    elif total >= tiers["uptrend"]:
        tier = "上升趋势"
    elif total >= tiers["neutral"]:
        tier = "震荡偏多"
    else:
        tier = "弱势"

    return {
        "code": code,
        "score": round(total, 2),
        "tier": tier,
        "ma_alignment": round(s1, 1),
        "price_above_ma": round(s2, 1),
        "ma_slope": round(s3, 1),
        "macd_trend": round(s4, 1),
        "volume_price": round(s5, 1),
        "tags": all_tags,
    }

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_stocklist() -> Dict[str, Dict[str, str]]:
    """加载 stocklist.csv，返回 {symbol: {name, industry}} 映射"""
    mapping: Dict[str, Dict[str, str]] = {}
    stocklist_path = Path(__file__).resolve().parent / "stocklist.csv"
    if not stocklist_path.exists():
        return mapping
    try:
        df = pd.read_csv(stocklist_path, dtype=str)
        for _, row in df.iterrows():
            symbol = str(row.get("symbol", "")).strip()
            if symbol:
                mapping[symbol] = {
                    "name": str(row.get("name", "")).strip(),
                    "industry": str(row.get("industry", "")).strip(),
                }
    except Exception as e:
        print(f"加载 stocklist.csv 出错: {e}", file=sys.stderr)
    return mapping


def get_data_directory(arg_data_dir: str) -> Path:
    data_dir = Path(arg_data_dir)
    if data_dir.exists():
        return data_dir
    # Fallback to project root data
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    fallback_data = project_root / "data"
    if fallback_data.exists() and any(fallback_data.glob("*.csv")):
        print(f"数据目录 {data_dir} 不存在，使用备用目录: {fallback_data}", file=sys.stderr)
        return fallback_data
    print(f"数据目录 {data_dir} 不存在", file=sys.stderr)
    sys.exit(1)


def load_stock_data(data_dir: Path, codes: List[str]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    for code in codes:
        fp = data_dir / f"{code}.csv"
        if not fp.exists():
            continue
        try:
            df = pd.read_csv(fp, parse_dates=["date"]).sort_values("date")
            frames[code] = df
        except Exception as e:
            print(f"读取 {fp} 出错: {e}", file=sys.stderr)
    return frames

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="上升趋势股票扫描器")
    p.add_argument("--data-dir", default="kline_data", help="K 线 CSV 数据目录 (默认: kline_data)")
    p.add_argument("--tickers", default="all", help="'all' 或逗号分隔的股票代码")
    p.add_argument("--min-score", type=float, default=60.0, help="最低趋势评分 (默认: 60)")
    p.add_argument("--top", type=int, default=20, help="返回前 N 只 (0 = 不限, 默认: 20)")
    p.add_argument("--output", default=None, help="输出文件路径 (默认: uptrend_<DATE>.json)")
    args = p.parse_args()

    # 加载配置
    cfg_path = Path(__file__).resolve().parent / "configs.json"
    cfg = load_config(cfg_path)

    # 加载数据
    data_dir = get_data_directory(args.data_dir)
    if args.tickers.lower() == "all":
        codes = [f.stem for f in data_dir.glob("*.csv")]
    else:
        codes = [c.strip() for c in args.tickers.split(",") if c.strip()]

    if not codes:
        print("股票池为空！", file=sys.stderr)
        sys.exit(1)

    print(f"扫描 {len(codes)} 只股票...", file=sys.stderr)
    data = load_stock_data(data_dir, codes)
    if not data:
        print("未能加载任何行情数据", file=sys.stderr)
        sys.exit(1)

    # 加载股票名称映射
    stock_info = load_stocklist()

    # 扫描
    results = []
    for code, df in data.items():
        result = scan_stock(code, df, cfg)
        if result and result["score"] >= args.min_score:
            info = stock_info.get(code, {})
            result["name"] = info.get("name", "")
            result["industry"] = info.get("industry", "")
            results.append(result)

    # 排序
    results.sort(key=lambda x: x["score"], reverse=True)

    # 限制数量
    if args.top > 0:
        results = results[:args.top]

    # 获取日期
    if data:
        any_df = next(iter(data.values()))
        trade_date = any_df["date"].max().strftime("%Y-%m-%d")
    else:
        trade_date = date.today().isoformat()

    output = {
        "date": trade_date,
        "count": len(results),
        "min_score": args.min_score,
        "stocks": results,
    }

    # 输出 JSON 到 stdout
    print(json.dumps(output, ensure_ascii=False, indent=2))

    # 保存文件
    out_path = args.output or f"uptrend_{trade_date}.json"
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"结果已保存至: {out_path}", file=sys.stderr)
    except Exception as e:
        print(f"保存失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
