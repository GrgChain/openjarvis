#!/usr/bin/env python3
"""Score strong sectors with deterministic rules.

Data source priority: tushare (via TUSHARE_TOKEN) → akshare fallback.
Tunable constants are defined at the top of this file for easy adjustment.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Scoring constants — adjust these to tune the model
# ---------------------------------------------------------------------------

WEIGHTS = {
    "change": 0.30,
    "breadth": 0.25,
    "turnover": 0.15,
    "leader": 0.15,
    "fund": 0.15,
}

# (low, high) ranges for linear normalization to [0, 100]
NORM_RANGES = {
    "change_pct": (-4.0, 4.0),
    "turnover": (1.0, 12.0),
    "leader": (-3.0, 10.0),
    "fund_pct": (-3.0, 3.0),
}

# Tier classification (checked in order; first match wins)
TIERS = [
    (75.0, "强势"),
    (60.0, "偏强"),
    (45.0, "中性"),
    (0.0, "弱势"),
]

# Signal / risk tag rules: (condition_fn, label)
SIGNAL_RULES: list[tuple[str, Any]] = [
    ("价量齐升",  lambda c, b, t, ts, mi: c >= 2 and b >= 0.6),
    ("主力净流入", lambda c, b, t, ts, mi: mi >= 1),
    ("龙头强势",  lambda c, b, t, ts, mi: ts >= 6),
]
RISK_RULES: list[tuple[str, Any]] = [
    ("短线过热", lambda c, b, t, ts, mi: t >= 12 and ts >= 9),
    ("分化上涨", lambda c, b, t, ts, mi: c > 0 and b < 0.5),
    ("资金背离", lambda c, b, t, ts, mi: c > 0 and mi < 0),
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _scale_linear(v: float, lo: float, hi: float) -> float:
    """Normalize *v* from [lo, hi] to [0, 100], clamped."""
    if hi <= lo:
        return 50.0
    return _clamp((v - lo) / (hi - lo) * 100.0, 0.0, 100.0)


def _rank_percentiles(values: list[float]) -> dict[float, float]:
    if not values:
        return {}
    sorted_unique = sorted(set(values))
    if len(sorted_unique) == 1:
        return {sorted_unique[0]: 0.5}
    result: dict[float, float] = {}
    n = len(sorted_unique) - 1
    for idx, value in enumerate(sorted_unique):
        result[value] = idx / n
    return result


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

def _fetch_tushare() -> list[dict[str, Any]]:
    """Fetch sector data via tushare sw_daily (申万行业日行情). Returns [] on failure."""
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        return []
    try:
        import tushare as ts  # type: ignore
    except ImportError:
        return []

    try:
        ts.set_token(token)
        pro = ts.pro_api()

        today = datetime.now().strftime("%Y%m%d")

        # sw_daily: 申万行业日行情（包含 name, pct_change, vol, amount 等）
        df = pro.sw_daily(trade_date=today)
        if df is None or df.empty:
            # 非交易日 fallback 到最近交易日
            from datetime import timedelta
            for offset in range(1, 5):
                d = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                df = pro.sw_daily(trade_date=d)
                if df is not None and not df.empty:
                    break
        if df is None or df.empty:
            return []

        # 只保留 L2 行业指数
        l2 = pro.index_classify(level="L2", src="SW2021")
        if l2 is not None and not l2.empty:
            l2_codes = set(l2["index_code"].tolist())
            df = df[df["ts_code"].isin(l2_codes)]

        rows: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            name = str(r.get("name", "")).strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "change_pct": _to_float(r.get("pct_change")),
                "turnover": 0.0,  # sw_daily 无换手率
                "up_count": 0,
                "down_count": 0,
                "top_stock_change": 0.0,
                "main_net_inflow": 0.0,
                "main_net_inflow_pct": 0.0,
            })

        if rows:
            print(f"[tushare] Loaded {len(rows)} sectors", file=sys.stderr)
        return rows

    except Exception as exc:
        print(f"[tushare] Failed: {exc}", file=sys.stderr)
        return []


def _fetch_akshare() -> list[dict[str, Any]]:
    try:
        import akshare as ak  # type: ignore
    except ImportError as exc:
        raise RuntimeError("akshare is required as fallback data source") from exc

    industry_df = ak.stock_board_industry_name_em()
    if industry_df is None or industry_df.empty:
        return []

    rows: dict[str, dict[str, Any]] = {}
    for _, row in industry_df.iterrows():
        name = str(row.get("板块名称", "")).strip()
        if not name:
            continue
        rows[name] = {
            "name": name,
            "change_pct": _to_float(row.get("涨跌幅")),
            "turnover": _to_float(row.get("换手率")),
            "up_count": _to_int(row.get("上涨家数")),
            "down_count": _to_int(row.get("下跌家数")),
            "top_stock_change": _to_float(row.get("领涨股票涨跌幅")),
        }

    try:
        flow_df = ak.stock_sector_fund_flow_rank(indicator="今日")
        if flow_df is not None and not flow_df.empty:
            for _, row in flow_df.iterrows():
                name = str(row.get("名称", "")).strip()
                if not name:
                    continue
                base = rows.get(name)
                if not base:
                    continue
                base["main_net_inflow"] = _to_float(row.get("今日主力净流入-净额"))
                base["main_net_inflow_pct"] = _to_float(row.get("今日主力净流入-净占比"))
    except Exception:
        pass

    if rows:
        print(f"[akshare] Loaded {len(rows)} sectors", file=sys.stderr)
    return list(rows.values())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _classify_tier(score: float) -> str:
    """Map score to tier label."""
    for threshold, label in TIERS:
        if score >= threshold:
            return label
    return TIERS[-1][1]


def _score_row(row: dict[str, Any], inflow_pct_rank: dict[float, float]) -> dict[str, Any]:
    change_pct = _to_float(row.get("change_pct"))
    turnover = _to_float(row.get("turnover"))
    up_count = _to_int(row.get("up_count"))
    down_count = _to_int(row.get("down_count"))
    top_stock_change = _to_float(row.get("top_stock_change"))
    main_net_inflow = _to_float(row.get("main_net_inflow"))
    main_net_inflow_pct = _to_float(row.get("main_net_inflow_pct"))

    # --- Weighted component scores ---
    components: dict[str, float] = {}
    available: dict[str, float] = {}

    lo, hi = NORM_RANGES["change_pct"]
    components["change"] = _scale_linear(change_pct, lo, hi)
    available["change"] = WEIGHTS["change"]

    if up_count + down_count > 0:
        breadth = up_count / float(up_count + down_count)
        components["breadth"] = _clamp(breadth * 100.0, 0.0, 100.0)
        available["breadth"] = WEIGHTS["breadth"]
    else:
        breadth = 0.5

    if turnover > 0:
        lo, hi = NORM_RANGES["turnover"]
        components["turnover"] = _scale_linear(turnover, lo, hi)
        available["turnover"] = WEIGHTS["turnover"]

    if top_stock_change != 0:
        lo, hi = NORM_RANGES["leader"]
        components["leader"] = _scale_linear(top_stock_change, lo, hi)
        available["leader"] = WEIGHTS["leader"]

    fund_parts: list[float] = []
    if main_net_inflow_pct != 0:
        lo, hi = NORM_RANGES["fund_pct"]
        fund_parts.append(_scale_linear(main_net_inflow_pct, lo, hi))
    if not math.isclose(main_net_inflow, 0.0):
        rank = inflow_pct_rank.get(main_net_inflow)
        if rank is not None:
            fund_parts.append(rank * 100.0)
    if fund_parts:
        components["fund"] = sum(fund_parts) / len(fund_parts)
        available["fund"] = WEIGHTS["fund"]

    weight_sum = sum(available.values())
    score = 50.0 if weight_sum <= 0 else sum(components[k] * available[k] for k in available) / weight_sum

    # --- Adjustment bonuses / penalties ---
    if change_pct >= 2.0 and breadth >= 0.65:
        score += 3.0
    if main_net_inflow_pct >= 1.0 and change_pct > 0:
        score += 2.0
    if change_pct < 0:
        score -= min(5.0, abs(change_pct))

    score = _clamp(score, 0.0, 100.0)

    # --- Signals & risks via rule tables ---
    rule_args = (change_pct, breadth, turnover, top_stock_change, main_net_inflow_pct)
    tags = [label for label, fn in SIGNAL_RULES if fn(*rule_args)]
    risks = [label for label, fn in RISK_RULES if fn(*rule_args)]

    return {
        "sector": row.get("name", ""),
        "score": round(score, 2),
        "tier": _classify_tier(score),
        "change_pct": round(change_pct, 2),
        "turnover": round(turnover, 2),
        "breadth": round(breadth, 4),
        "up_count": up_count,
        "down_count": down_count,
        "top_stock_change": round(top_stock_change, 2),
        "main_net_inflow": round(main_net_inflow, 2),
        "main_net_inflow_pct": round(main_net_inflow_pct, 2),
        "tags": tags,
        "risks": risks,
    }


# ---------------------------------------------------------------------------
# Output / CLI
# ---------------------------------------------------------------------------

def _write_output(text: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    print(f"Output written to {output}", file=sys.stderr)


def _resolve_output_path(output_arg: str | None) -> Path:
    """Resolve output path. Default: sector_strength_<YYYY-MM-DD>.json in cwd."""
    stamp = datetime.now().strftime("%Y-%m-%d")
    default_name = f"sector_strength_{stamp}.json"
    if output_arg is None:
        return Path(default_name)
    p = Path(output_arg).expanduser()
    if p.is_dir() or output_arg.endswith("/"):
        return p / default_name
    return p


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score strong sectors (tushare优先, akshare fallback).")
    parser.add_argument("--top", type=int, default=20, help="Top N sectors to keep after sorting (0 = no limit).")
    parser.add_argument("--min-score", type=float, default=60.0, help="Minimum score filter.")
    parser.add_argument("--all", action="store_true", help="Show all sectors (alias for --min-score 0).")
    parser.add_argument("--output", default=None, help="Output file path.")
    parser.add_argument("--source", choices=["auto", "tushare", "akshare"], default="auto",
                        help="Data source: auto (tushare→akshare), tushare, akshare.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    min_score = 0.0 if getattr(args, "all", False) else args.min_score

    # --- Load data (tushare优先, akshare fallback) ---
    source_rows: list[dict[str, Any]] = []
    source_used = ""

    if args.source in ("auto", "tushare"):
        source_rows = _fetch_tushare()
        if source_rows:
            source_used = "tushare"

    if not source_rows and args.source in ("auto", "akshare"):
        source_rows = _fetch_akshare()
        if source_rows:
            source_used = "akshare"

    if not source_rows:
        print("No sector rows loaded.", file=sys.stderr)
        return 1

    # --- Score ---
    inflow_values = [_to_float(r.get("main_net_inflow")) for r in source_rows if _to_float(r.get("main_net_inflow")) != 0]
    inflow_pct_rank = _rank_percentiles(inflow_values)

    scored = [_score_row(row, inflow_pct_rank) for row in source_rows]
    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = [x for x in scored if x["score"] >= min_score]
    if args.top > 0:
        scored = scored[: args.top]

    # --- Output ---
    output_path = _resolve_output_path(args.output)

    payload = {
        "source": source_used,
        "count": len(scored),
        "strong_sectors": scored,
        "threshold": min_score,
    }
    _write_output(json.dumps(payload, ensure_ascii=False, indent=2), output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
