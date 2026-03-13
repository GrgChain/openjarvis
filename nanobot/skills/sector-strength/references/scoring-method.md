# Sector Strength Scoring

## Input Fields

Required minimal fields:
- `name`
- `change_pct`

Optional but recommended:
- `turnover`
- `up_count`, `down_count`
- `top_stock_change`
- `main_net_inflow_pct`
- `main_net_inflow`

## Weighted Components

- `change_pct`: 30%
- `breadth`: 25%
- `turnover`: 15%
- `leader_strength`: 15%
- `fund_flow`: 15%

When some fields are missing, weights are renormalized across available components.

## Normalization

- `change_pct`: linear map from `[-4, +4]` to `[0, 100]`
- `turnover`: linear map from `[1, 12]` to `[0, 100]`
- `leader_strength`: linear map from `[-3, +10]` to `[0, 100]`
- `breadth`: direct map from `[0, 1]` to `[0, 100]`
- `main_net_inflow_pct`: linear map from `[-3, +3]` to `[0, 100]`
- `main_net_inflow`: percentile rank among sectors

Fund flow score uses average of available fund sub-metrics.

## Adjustment Rules

- Add +3 if `change_pct >= 2` and `breadth >= 0.65`
- Add +2 if `main_net_inflow_pct >= 1` and `change_pct > 0`
- Subtract up to 5 when `change_pct < 0`

Final score is clamped to `[0, 100]`.

## Tier Rules

- `>= 75`: `强势`
- `60-74.99`: `偏强`
- `45-59.99`: `中性`
- `< 45`: `弱势`

## Risk Tags

- `短线过热`: `turnover >= 12` and `top_stock_change >= 9`
- `分化上涨`: `change_pct > 0` and `breadth < 0.5`
- `资金背离`: `change_pct > 0` and `main_net_inflow_pct < 0`
