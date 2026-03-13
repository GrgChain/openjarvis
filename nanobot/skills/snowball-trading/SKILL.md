---
name: snowball-trading
description: Use when the user requests to execute simulated trades, rebalance their portfolio, or query their current positions/running balance on Xueqiu (Snowball).
metadata: {"nanobot":{"emoji":"⛄","requires":{"bins":["python"]}}}
---

# Snowball Portfolio Trading Skill

Follow these instructions to manage stock portfolios via `easytrader` on the Snowball (Xueqiu) simulation platform.

> [!IMPORTANT]
> Snowball simulated portfolios enforce **T+1** constraints — stocks purchased today cannot be sold until the next trading day. Ensure this is considered when executing short-term strategies.

## Environment Variables

The trader relies strictly on system-passed environment variables to authenticate with Xueqiu (instead of a static `.env` file). You should prefix the command with `env` or pass them directly when executing. These MUST be set:

| Variable | Description |
|:---|:---|
| `XQ_A_TOKEN` | Xueqiu token (Extracted from Browser DevTools → Cookie → `xq_a_token`) |
| `XQ_PORTFOLIO_CODE` | Portfolio code, e.g., `ZH000000` |
| `XQ_INITIAL_ASSETS` | Initial assets for the simulated portfolio (Default: `1000000`) |

## Execution Core

Run the `scripts/trader.py` script to perform portfolio transactions.

### Usage structure

```bash
python scripts/trader.py <COMMAND> [--code <SYMBOL>] [--price <PRICE>] [--amount <AMOUNT>] [--weight <WEIGHT_PCT>]
```

### Commands

| Command | Description | Required Arguments |
|:---|:---|:---|
| `buy` | Buy a specific stock | `--code` `--price` `--amount` |
| `sell` | Sell a specific stock | `--code` `--price` `--amount` |
| `adjust` | Rebalance a stock to a target percentage | `--code` `--weight` |
| `cancel` | Cancel an unexecuted order | `--id` (optional) |
| `position` | List all current mock holdings | *None* |
| `balance` | Check available cash and total market value | *None* |

### Examples

**Buy 100 shares of Ping An Bank (000001) at 12.50:**
```bash
python scripts/trader.py buy --code 000001 --price 12.50 --amount 100
```

**Cancel an order with a specific ID:**
```bash
python scripts/trader.py cancel --id ZH123456
```

**Cancel all pending orders:**
```bash
python scripts/trader.py cancel
```

**Rebalance Ping An Bank (000001) to exactly 10% of total portfolio value:**
```bash
python scripts/trader.py adjust --code 000001 --weight 10
```

**Liquidate a position completely (set its weight to 0%):**
```bash
python scripts/trader.py adjust --code 000001 --weight 0
```

## Review Output

The script outputs a response detailing the transaction confirmation or tabular readouts for positions. If executing a trade, use the response to verify the transaction was successfully broadcast to Xueqiu's portfolio API before responding to the user.
