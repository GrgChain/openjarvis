---
name: sector-strength
description: Rule-based judgment of strong sectors (强势板块) for A-shares. Use when the user asks to identify strongest sectors, rank sector momentum, validate AI sector conclusions with deterministic scoring, or generate watchlists from sector涨跌幅/换手率/涨跌家数/资金流.
metadata: {"nanobot":{"emoji":"🏆","requires":{"bins":["python"]}}}
---

# Sector Strength

Use this skill to judge strong sectors with deterministic scoring rules instead of pure LLM text inference.

## Run

```bash
python3 scripts/score_sectors.py
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--top N` | Top N sectors (0 = no limit) | `20` |
| `--min-score N` | Minimum score filter | `60` |
| `--all` | Show all sectors (alias `--min-score 0`) | off |
| `--output` | Output file path | `sector_strength_<YYYY-MM-DD>.json` |
| `--source` | Data source: `auto`, `tushare`, `akshare` | `auto` |

## Data Source

Priority: **tushare** → akshare fallback (when `--source auto`).

- `tushare`: requires `TUSHARE_TOKEN` env var. Uses SW L2 industry index + moneyflow.
- `akshare`: uses 东方财富行业板块 + 资金流向, no token needed.
- `auto` (default): try tushare first, fall back to akshare if unavailable or fails.

## Scoring Logic

Script combines these weighted dimensions (tunable constants at top of `score_sectors.py`):

| Dimension | Weight | Normalization Range |
|-----------|--------|-------------------|
| sector change % | 30% | [-4, +4] |
| breadth (up/total) | 25% | [0, 1] |
| turnover | 15% | [1, 12] |
| leader strength | 15% | [-3, +10] |
| fund flow | 15% | [-3, +3] |

Score `0-100`, classified as:
- `>= 75`: **强势** / `60-74`: **偏强** / `45-59`: **中性** / `< 45`: **弱势**

Signal tags: `价量齐升` · `主力净流入` · `龙头强势`
Risk tags: `短线过热` · `分化上涨` · `资金背离`

## Example Output

```json
{
  "count": 2,
  "strong_sectors": [
    {
      "sector": "半导体",
      "score": 82.35,
      "tier": "强势",
      "change_pct": 3.12,
      "turnover": 6.45,
      "breadth": 0.7826,
      "top_stock_change": 9.98,
      "main_net_inflow_pct": 2.31,
      "tags": ["价量齐升", "主力净流入", "龙头强势"],
      "risks": []
    },
    {
      "sector": "光伏设备",
      "score": 68.10,
      "tier": "偏强",
      "change_pct": 1.85,
      "turnover": 4.20,
      "breadth": 0.6500,
      "top_stock_change": 7.52,
      "main_net_inflow_pct": -0.45,
      "tags": ["龙头强势"],
      "risks": ["资金背离"]
    }
  ],
  "threshold": 60.0
}
```

Output file: `sector/sector_strength_20260305.json`

## Use In Analysis

When user asks "哪些板块是强势板块":
1. Run `score_sectors.py`
2. Report top sectors with `score`, `tier`, and signal/risk tags.
3. Compare AI conclusions with rule-based ranking for consistency.

For metric definitions and fallback behavior, read:
- [references/scoring-method.md](references/scoring-method.md)
