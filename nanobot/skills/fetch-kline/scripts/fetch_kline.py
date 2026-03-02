from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Set
import os

import pandas as pd
import tushare as ts
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# --------------------------- Global Requests Retry Config --------------------------- #
# AKShare uses requests under the hood, this helps prevent RemoteDisconnected errors
session = requests.Session()
# Configure robust retries: 10 connect retries, 10 read retries, with exponential backoff
retry = Retry(
    total=10,
    connect=10, 
    read=10,
    backoff_factor=1,
    status_forcelist=[413, 429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Monkeypatch requests.get to use our session with retries for AKShare
_original_get = requests.get
def _session_get(url, **kwargs):
    return session.get(url, **kwargs)
requests.get = _session_get
requests.post = session.post

# --------------------------- Warning Suppression --------------------------- #
warnings.filterwarnings("ignore", category=FutureWarning)

# --------------------------- Constants --------------------------- #
COOLDOWN_SECS = 600
BAN_PATTERNS = (
    "访问频繁", "请稍后", "超过频率", "频繁访问",
    "too many requests", "429",
    "forbidden", "403",
    "max retries exceeded"
)

class RateLimitError(RuntimeError):
    pass

# --------------------------- DataFetcher Class --------------------------- #
class DataFetcher:
    def __init__(self, api_token: Optional[str] = None):
        if not api_token:
            api_token = os.environ.get("TUSHARE_TOKEN")
        
        # Configure Proxy if needed (from original code)
        os.environ["NO_PROXY"] = "api.waditu.com,.waditu.com,waditu.com"
        os.environ["no_proxy"] = os.environ["NO_PROXY"]
        
        self.pro = None
        if api_token:
            try:
                ts.set_token(api_token)
                self.pro = ts.pro_api()
            except Exception as e:
                print(f"Failed to initialize Tushare, will use AKShare fallback: {e}")
        else:
            print("TUSHARE_TOKEN not provided, using AKShare for data fetching.")

    @staticmethod
    def _to_ts_code(code: str) -> str:
        code = str(code).zfill(6)
        if code.startswith(("60", "68", "9")):
            return f"{code}.SH"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SZ"

    @staticmethod
    def _looks_like_ip_ban(exc: Exception) -> bool:
        msg = (str(exc) or "").lower()
        return any(pat in msg for pat in BAN_PATTERNS)

    def _cool_sleep(self, base_seconds: int) -> None:
        jitter = random.uniform(0.9, 1.2)
        sleep_s = max(1, int(base_seconds * jitter))
        print(f"Suspected rate limit, sleeping {sleep_s}s...")
        time.sleep(sleep_s)

    def get_kline(self, code: str, start: str, end: str) -> pd.DataFrame:
        ts_code = self._to_ts_code(code)
        df = None
        error = None
        
        # Try Tushare first if we have a token
        if getattr(self, "pro", None):
            try:
                df = ts.pro_bar(
                    ts_code=ts_code,
                    adj="qfq",
                    start_date=start,
                    end_date=end,
                    freq="D",
                    api=self.pro
                )
            except Exception as e:
                if self._looks_like_ip_ban(e):
                    raise RateLimitError(str(e)) from e
                error = e
                # Fallback to AKShare

        # Fallback to AKShare
        if df is None:
            try:
                import akshare as ak
                # AKShare requires symbol without suffix, e.g. "000001" instead of "000001.SZ"
                # but with board prefixes like sh600000 for some interfaces? 
                # stock_zh_a_hist just takes 6 digit symbol
                df = ak.stock_zh_a_hist(
                    symbol=code.zfill(6),
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust="qfq"
                )
                if df is not None and not df.empty:
                    # Rename AKShare columns to match Tushare output format
                    # AKShare: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
                    df = df.rename(columns={
                        "日期": "trade_date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "vol"
                    })
                    # Format date to match Tushare's YYYYMMDD string format before processing further
                    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
            except Exception as e:
                print(f"AKShare fallback failed for {code}: {e}")
                if error: 
                    raise error
                raise e

        if df is None or df.empty:
            return pd.DataFrame()

        df = df[["trade_date", "open", "close", "high", "low", "vol"]].rename(
            columns={"trade_date": "date", "vol": "volume"}
        )
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        for c in ["open", "close", "high", "low", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.sort_values("date").reset_index(drop=True)

    @staticmethod
    def validate(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
        if df["date"].isna().any():
            raise ValueError("Missing date values detected")
        if (df["date"] > pd.Timestamp.today()).any():
            raise ValueError("Future dates detected in data")
        return df

    def fetch_one(self, code: str, start: str, end: str, out_dir: Path):
        csv_path = out_dir / f"{code}.csv"
        existing_df = pd.DataFrame()
        last_date = None

        # Check existing data
        if csv_path.exists():
            try:
                existing_df = pd.read_csv(csv_path, parse_dates=["date"])
                if not existing_df.empty:
                    last_date = existing_df["date"].max()
            except Exception as e:
                print(f"Error reading {csv_path}, will re-download full history: {e}")
                existing_df = pd.DataFrame()

        # Determine fetch range
        fetch_start = start
        if last_date is not None:
            fetch_start = (last_date + pd.Timedelta(days=1)).strftime("%Y%m%d")
            
            # Check if sync needed
            today_str = dt.date.today().strftime("%Y%m%d")
            effective_end = today_str if str(end).lower() == "today" else end
            
            if fetch_start > effective_end:
                print(f"{code} is up to date ({last_date.date()}).")
                return

        # Retry Loop: Up to 5 attempts for robustness
        for attempt in range(1, 6):
            try:
                new_df = self.get_kline(code, fetch_start, end)
                
                if new_df.empty and existing_df.empty:
                    new_df = pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume"])
                
                if not new_df.empty:
                    if not existing_df.empty:
                        new_df = new_df[new_df["date"] > last_date]
                        if not new_df.empty:
                            final_df = pd.concat([existing_df, new_df], ignore_index=True)
                        else:
                            final_df = existing_df
                    else:
                        final_df = new_df
                    
                    final_df = self.validate(final_df)
                    final_df.to_csv(csv_path, index=False)
                break
            except Exception as e:
                msg = str(e).lower()
                is_ban = self._looks_like_ip_ban(e)
                
                # Check for critical errors that shouldn't be retried
                if "no_such_code" in msg or "invalid" in msg:
                    print(f"{code}: Invalid code or no data available. Skipping.")
                    break
                    
                if is_ban or "ssl" in msg or "max retries exceeded" in msg or "connection" in msg:
                    # Exponential backoff for connection/ban issues
                    wait_s = COOLDOWN_SECS if is_ban else (5 * (2 ** (attempt - 1)))
                    print(f"[{attempt}/5] {code} Connect/Ban issue. Sleep {wait_s}s. {e}")
                    if is_ban:
                        self._cool_sleep(wait_s)
                    else:
                        time.sleep(wait_s)
                else:
                    wait_s = 10 * attempt
                    print(f"[{attempt}/5] {code} failed: {e}. Retry in {wait_s}s")
                    time.sleep(wait_s)
        else:
            print(f"[{code}] Failed permanently after 5 attempts.")


# --------------------------- StockList Logic --------------------------- #
def get_stocklist_path() -> Path:
    """Return the absolute path to the default stocklist.csv."""
    return Path(__file__).resolve().parent / "stocklist.csv"

def load_codes(stocklist_csv: Path, exclude_boards: Set[str]) -> List[str]:
    if not stocklist_csv.exists():
        raise FileNotFoundError(f"{stocklist_csv} not found")
        
    df = pd.read_csv(stocklist_csv)
    
    # Filter
    code_str = df["symbol"].astype(str)
    ts_code = df["ts_code"].astype(str).str.upper()
    mask = pd.Series(True, index=df.index)

    if "gem" in exclude_boards:
        mask &= ~code_str.str.startswith(("300", "301"))
    if "star" in exclude_boards:
        mask &= ~code_str.str.startswith("688")
    if "bj" in exclude_boards:
        mask &= ~(ts_code.str.endswith(".BJ") | code_str.str.startswith(("4", "8")))

    codes = code_str[mask].str.zfill(6).unique().tolist()
    print(f"Loaded {len(codes)} stocks from {stocklist_csv} (excluded: {exclude_boards})")
    return codes





def run_job(args, fetcher):
    """
    Execute a single sync job.
    """
    print(f"JOB STARTED: {dt.datetime.now()}")
    
    # Date parsing (re-evaluated each run for 'today')
    start = dt.date.today().strftime("%Y%m%d") if str(args.start).lower() == "today" else args.start
    end = dt.date.today().strftime("%Y%m%d") if str(args.end).lower() == "today" else args.end
    
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load Codes
    exclude_boards = set(args.exclude_boards)

    try:
        # Default to stocklist.csv in current directory of this file
        stock_list_path = get_stocklist_path()
        codes = load_codes(stock_list_path, exclude_boards)
    except Exception as e:
        print(f"Failed to load stock list: {e}")
        return

    print(f"Starting incremental sync for {len(codes)} stocks | {start} -> {end}")

    # Concurrent Fetch
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(fetcher.fetch_one, code, start, end, out_dir)
            for code in codes
        ]
        # Avoid tqdm in scheduled mode if running in background to prevent log spam,
        # but keep it for manual runs or if preferred.
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Progress"):
            pass

    print(f"JOB DONE. Data saved to {out_dir.resolve()}")



# --------------------------- Main --------------------------- #
def main():

    parser = argparse.ArgumentParser(description="Tushare Daily K-Line Scraper (Incremental)")
    parser.add_argument("--start", default="20250101", help="YYYYMMDD or 'today'")
    parser.add_argument("--end", default="today", help="YYYYMMDD or 'today'")
    parser.add_argument("--exclude-boards", nargs="*", default=[], choices=["gem", "star", "bj"])
    parser.add_argument("--out", default="kline_data")
    parser.add_argument("--workers", type=int, default=6)

    args = parser.parse_args()

    # Init Fetcher
    try:
        fetcher = DataFetcher()

    except ValueError as e:
        print(str(e))
        sys.exit(1)

    # Run once immediately
    run_job(args, fetcher)

if __name__ == "__main__":
    main()
