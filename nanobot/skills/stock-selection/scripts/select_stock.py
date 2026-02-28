import argparse
import os
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

# ---------- 工具 ----------

def load_data(data_dir: Path, codes: Iterable[str]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    for code in codes:
        fp = data_dir / f"{code}.csv"
        if not fp.exists():
            continue
        try:
            df = pd.read_csv(fp, parse_dates=["date"]).sort_values("date")
            frames[code] = df
        except Exception as e:
            print(f"Error reading {fp}: {e}")
            continue
    return frames


def load_config(cfg_path: Path) -> List[Dict[str, Any]]:
    if not cfg_path.exists():
        print(f"配置文件 {cfg_path} 不存在")
        sys.exit(1)
    with cfg_path.open(encoding="utf-8") as f:
        cfg_raw = json.load(f)

    # 兼容三种结构：单对象、对象数组、或带 strategies 键
    if isinstance(cfg_raw, list):
        cfgs = cfg_raw
    elif isinstance(cfg_raw, dict) and "strategies" in cfg_raw:
        cfgs = cfg_raw["strategies"]
    else:
        cfgs = [cfg_raw]

    if not cfgs:
        print("configs.json 未定义任何 Strategy")
        sys.exit(1)

    return cfgs


def instantiate_strategy(cfg: Dict[str, Any]):
    """动态加载 Strategy 类并实例化"""
    cls_name: str = cfg.get("class")
    if not cls_name:
        raise ValueError("缺少 class 字段")

    try:
        # Import from local strategies.py
        import strategies
        cls = getattr(strategies, cls_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"无法加载 strategies.{cls_name}: {e}") from e

    params = cfg.get("params", {})
    return cfg.get("alias", cls_name), cls(**params)


def get_data_directory(arg_data_dir: str) -> Path:
    data_dir = Path(arg_data_dir)
    if data_dir.exists():
        return data_dir
        
    # Fallback to project root data
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    fallback_data = project_root / "data"
    
    if fallback_data.exists() and any(fallback_data.glob("*.csv")):
        print(f"Data not found in {data_dir}, using fallback: {fallback_data}")
        return fallback_data
    
    print(f"数据目录 {data_dir} 不存在")
    sys.exit(1)


def get_stock_codes(data_dir: Path, tickers_arg: str) -> List[str]:
    codes = (
        [f.stem for f in data_dir.glob("*.csv")]
        if tickers_arg.lower() == "all"
        else [c.strip() for c in tickers_arg.split(",") if c.strip()]
    )
    if not codes:
        print("股票池为空！")
        sys.exit(1)
    
    print(f"Found {len(codes)} stocks in {data_dir}")
    return codes


def determine_trade_date(date_arg: str | None, data: Dict[str, pd.DataFrame]) -> pd.Timestamp:
    trade_date = (
        pd.to_datetime(date_arg)
        if date_arg
        else max(df["date"].max() for df in data.values())
    )
    if not date_arg:
        print(f"未指定 --date，使用最近日期 {trade_date.date()}")
    return trade_date


def run_strategies(strategy_cfgs: List[Dict], trade_date: pd.Timestamp, data: Dict[str, pd.DataFrame], out: Path | None = None):
    results = {}
    for cfg in strategy_cfgs:
        if cfg.get("activate", True) is False:
            continue
        try:
            alias, strategy = instantiate_strategy(cfg)
        except Exception as e:
            print(f"跳过配置 {cfg}：{e}")
            continue
        
        print(f"Running strategy: {alias}")
        picks = strategy.select(trade_date, data)
        results[alias] = picks

        # 将结果写入日志，同时输出到控制台
        print("")
        print(f"============== 策略结果 [{alias}] ==============")
        print(f"交易日: {trade_date.date()}")
        print(f"符合条件股票数: {len(picks)}")
        print(", ".join(picks) if picks else "无符合条件股票")

    # 如果指定了输出目录，将所有结果保存到一个 JSON 文件
    if out and results:
        file_date = trade_date.strftime("%Y%m%d")
        output_file = out / f"picks_{file_date}.json"
        try:
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"所有结果已合并保存至: {output_file}")
        except Exception as e:
            print(f"无法保存结果到 {output_file}: {e}")


def get_strategy_configs() -> List[Dict[str, Any]]:
    config_path = Path(__file__).resolve().parent / "configs.json"
    return load_config(config_path)


def main():
    p = argparse.ArgumentParser(description="Run strategies defined in configs.json")
    p.add_argument("--data-dir", default="kline_data", help="CSV 行情目录")
    p.add_argument("--date", help="交易日 YYYY-MM-DD；缺省=数据最新日期")
    p.add_argument("--tickers", default="all", help="'all' 或逗号分隔股票代码列表")
    p.add_argument("--out", default="stock_picks", help="策略结果保存目录 (默认: ./stock_picks)")
    args = p.parse_args()
    
    # 1. Prepare Data
    data_dir = get_data_directory(args.data_dir)
    codes = get_stock_codes(data_dir, args.tickers)
    data = load_data(data_dir, codes)
    if not data:
        print("未能加载任何行情数据")
        sys.exit(1)

    # 2. Prepare Context
    trade_date = determine_trade_date(args.date, data)

    # 3. Load & Run Strategies
    strategy_cfgs = get_strategy_configs()
    
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_strategies(strategy_cfgs, trade_date, data, out=out_dir)


if __name__ == "__main__":
    main()
