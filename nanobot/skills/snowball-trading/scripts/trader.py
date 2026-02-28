#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""雪球组合交易 — 通过 easytrader 管理雪球 A 股模拟组合。"""

import argparse
import os
import sys
from pathlib import Path

import easytrader

# Fix for Docker environments where stdout might have strict encoding
# This prevents UnicodeEncodeError: 'utf-8' codec can't encode characters in position ...: surrogates not allowed
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SnowballTrader
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SnowballTrader:
    """雪球模拟组合交易封装。

    用法示例::

        trader = SnowballTrader()
        trader.show_balance()
        trader.show_position()
        trader.buy("000001", price=12.5, amount=100)
        trader.sell("000001", price=13.0, amount=100)
        trader.adjust("000001", weight=10)
    """

    def __init__(self, initial_assets: float = 1_000_000):
        token = os.getenv("XQ_A_TOKEN", "")
        portfolio_code = os.getenv("XQ_PORTFOLIO_CODE", "")

        if not token or not portfolio_code:
            sys.exit(
                "[ERROR] 缺少环境变量 XQ_A_TOKEN 或 XQ_PORTFOLIO_CODE\n"
                "请在 .env 文件中配置：\n"
                "  XQ_A_TOKEN=<your_xueqiu_token>\n"
                "  XQ_PORTFOLIO_CODE=<your_portfolio_code>"
            )

        self._client = easytrader.use("xq", initial_assets=initial_assets)
        self.initial_assets = initial_assets
        self._client.prepare(
            cookies=f"xq_a_token={token}",
            portfolio_code=portfolio_code,
            portfolio_market="cn",
        )

    # ── 交易操作 ──────────────────────────────────────────────────────────

    def buy(self, code: str, price: float, amount: int):
        """买入股票。"""
        result = self._client.buy(code, price=price, amount=amount)
        self._print_trade("买入", code, price, amount, result)
        return result

    def sell(self, code: str, price: float, amount: int):
        """卖出股票。"""
        result = self._client.sell(code, price=price, amount=amount)
        self._print_trade("卖出", code, price, amount, result)
        return result

    def adjust(self, code: str, weight: float):
        """比例调仓，将 code 调整到 weight%。"""
        self._client.adjust_weight(code, weight)
        print(f"【调仓成功】 {code} → {weight}%")

    # ── 查询 ──────────────────────────────────────────────────────────────

    def show_position(self):
        """打印持仓信息。"""
        positions = self._client.position
        if not positions:
            print("【持仓信息】 当前无持仓。")
            return positions

        print("【持仓信息】")
        print(f"  {'代码':<10} {'名称':<10} {'市值':>12} {'成本价':>10} {'最新价':>10}")
        for p in positions:
            print(
                f"  {p.get('stock_code', ''):<10} "
                f"{p.get('stock_name', ''):<10} "
                f"{p.get('market_value', 0):>12.2f} "
                f"{p.get('cost_price', 0):>10.3f} "
                f"{p.get('last_price', 0):>10.3f}"
            )
        return positions

    def show_balance(self):
        """打印资金状况。"""
        balances = self._client.balance
        if not balances:
            print("【资金状况】 无法获取资金信息。")
            return balances

        b = balances[0]
        print("【资金状况】")
        print(f"  总资产:   {b.get('asset_balance', 0):>14.2f}")
        print(f"  参考市值: {b.get('market_value', 0):>14.2f}")
        print(f"  可用资金: {b.get('current_balance', 0):>14.2f}")

        # 计算总收益
        total_asset = b.get('asset_balance', 0)
        profit = total_asset - self.initial_assets
        if self.initial_assets > 0:
            profit_rate = (profit / self.initial_assets) * 100
        else:
            profit_rate = 0.0

        print(f"  总收益:   {profit:>14.2f}")
        print(f"  收益率:   {profit_rate:>13.2f}%")
        return balances

    # ── 内部 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _print_trade(action: str, code: str, price: float, amount: int, result):
        print(f"【{action}结果】 {code}  价格: {price}  数量: {amount}")
        if result:
            print(f"  返回: {result}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="雪球组合交易 — buy / sell / adjust / position / balance")
    p.add_argument("--initial-assets", type=float, default=1_000_000)
    sub = p.add_subparsers(dest="command", required=True, help="子命令")

    # buy / sell 共享参数
    for name, desc in [("buy", "买入"), ("sell", "卖出")]:
        s = sub.add_parser(name, help=f"{desc}股票")
        s.add_argument("--code",   required=True, help="股票代码")
        s.add_argument("--price",  required=True, type=float, help="委托价格")
        s.add_argument("--amount", required=True, type=int, help="委托数量")

    s = sub.add_parser("adjust", help="比例调仓")
    s.add_argument("--code",   required=True, help="股票代码")
    s.add_argument("--weight", required=True, type=float, help="目标持仓比例 (%%)")

    sub.add_parser("position", help="查询持仓")
    sub.add_parser("balance",  help="查询资金")
    return p


def main():
    args = _build_parser().parse_args()
    trader = SnowballTrader(initial_assets=args.initial_assets)

    match args.command:
        case "buy":      trader.buy(args.code, args.price, args.amount)
        case "sell":     trader.sell(args.code, args.price, args.amount)
        case "adjust":   trader.adjust(args.code, args.weight)
        case "position": trader.show_position()
        case "balance":  trader.show_balance()


if __name__ == "__main__":
    main()
