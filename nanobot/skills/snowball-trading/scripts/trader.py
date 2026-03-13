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

    def __init__(self, initial_assets: float = None):

        if initial_assets is None:
            raw_assets = os.getenv("XQ_INITIAL_ASSETS", "1000000")
            try:
                initial_assets = float(raw_assets)
            except ValueError:
                initial_assets = 1_000_000.0
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

    def cancel(self, order_id: str = None):
        """撤销未成交的委托。如果不指定 order_id，则撤销所有未成交委托。"""
        if order_id:
            result = self._client.cancel_entrust(order_id)
            print(f"【撤单结果】 订单 ID: {order_id}")
            if result:
                print(f"  返回: {result}")
        else:
            # easytrader 的 xq 驱动 cancel_entrust 若不传参数通常不生效或行为不一
            # 我们先尝试获取当前委托
            try:
                entrusts = self._client.entrust
                if not entrusts:
                    print("【撤单结果】 当前没有待成交的委托。")
                    return
                for e in entrusts:
                    oid = e.get('entrust_no') or e.get('entrust_id')
                    if oid:
                        self._client.cancel_entrust(oid)
                        print(f"【撤单结果】 已撤销订单: {oid}")
            except Exception as e:
                print(f"【撤单失败】 {e}")

    # ── 查询 ──────────────────────────────────────────────────────────────

    def show_position(self):
        """打印持仓信息。"""
        positions = self._client.position
        if not positions:
            print("【持仓信息】 当前无持仓。")
            return positions

        # 从调仓历史获取每只股票的真实成交价和 volume
        entry_price_dict = {}  # symbol -> 成交价
        volume_dict = {}       # symbol -> volume (比例值)
        try:
            for rb in self._client.history:
                if rb.get('status') != 'success':
                    continue
                for rh in rb.get('rebalancing_histories', []):
                    sym = rh.get('stock_symbol', '')
                    vol = rh.get('volume', 0) or 0
                    price = rh.get('price', 0) or 0
                    if sym and vol > 0 and price > 0:
                        entry_price_dict[sym] = price
                        volume_dict[sym] = vol
        except Exception:
            pass

        quote_dict = {}
        target_stocks = [p.get('stock_code', '') for p in positions if p.get('stock_code')]
        if target_stocks:
            url = "https://stock.xueqiu.com/v5/stock/batch/quote.json?symbol=" + ",".join(target_stocks)
            headers = self._client.s.headers.copy()
            headers["Host"] = "stock.xueqiu.com"
            try:
                res = self._client.s.get(url, headers=headers)
                quotes = res.json()
                if quotes and 'data' in quotes and 'items' in quotes['data']:
                    for item in quotes['data']['items']:
                        q = item.get('quote', {})
                        if q and 'symbol' in q:
                            quote_dict[q['symbol']] = q
            except Exception as e:
                print(f"获取行情数据失败: {e}")

        print("【持仓信息】")
        print(f"  {'代码':<10} {'名称':<10} {'成交价':>10} {'初始市值':>12} {'最新市值':>12} {'持仓盈亏':>12} {'盈亏比例':>8} {'最新价':>10} {'今日涨跌幅':>8}")
        for p in positions:
            code = p.get('stock_code', '')
            q = quote_dict.get(code, {})
            if q:
                p['last_price'] = q.get('current', p.get('last_price', 0))
                p['percent'] = q.get('percent', 0.0)

            volume = volume_dict.get(code, 0.0)
            entry_price = entry_price_dict.get(code, 0.0)
            last_price = p.get('last_price', 0)

            # volume 是比例值，shares = volume × initial_assets
            # entry_price 来自调仓历史的真实成交价
            if volume > 0 and entry_price > 0 and last_price > 0:
                shares = volume * self.initial_assets
                initial_market_value = shares * entry_price
                real_market_value = shares * last_price
            else:
                initial_market_value = p.get('market_value', 0)
                real_market_value = initial_market_value

            pnl = real_market_value - initial_market_value
            pnl_rate = (pnl / initial_market_value * 100) if initial_market_value else 0.0

            print(
                f"  {code:<10} "
                f"{p.get('stock_name', ''):<10} "
                f"{entry_price:>10.3f} "
                f"{initial_market_value:>12.2f} "
                f"{real_market_value:>12.2f} "
                f"{pnl:>+12.2f} "
                f"{pnl_rate:>+7.2f}% "
                f"{last_price:>10.3f} "
                f"{p.get('percent', 0.0):>7.2f}%"
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

        print(f"  总收益:   {profit:>+14.2f}")
        print(f"  总收益率:   {profit_rate:>+13.2f}%")

        # 当日盈亏：通过组合净值历史计算 (今日总资产 - 昨日净值 × 初始资金)
        try:
            url = f"https://xueqiu.com/cubes/nav_daily/all.json?cube_symbol={self._client.account_config['portfolio_code']}"
            res = self._client.s.get(url)
            nav_data = res.json()
            nav_list = nav_data[0].get('list', [])
            if nav_list:
                prev_nav = nav_list[-1]['value']
                prev_date = nav_list[-1]['date']
                prev_total = prev_nav * self.initial_assets
                daily_pnl = total_asset - prev_total
                daily_rate = (total_asset / prev_total - 1) * 100 if prev_total else 0.0
                print(f"  当日盈亏: {daily_pnl:>+14.2f} ({daily_rate:>+.2f}%，基于 {prev_date} 净值 {prev_nav:.4f})")
        except Exception:
            pass

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
    s.add_argument("--weight", required=True, type=float, help="目标持仓比例 (%)")

    s = sub.add_parser("cancel", help="撤销委托")
    s.add_argument("--id", help="订单 ID (如果不传则尝试撤销所有)")

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
        case "cancel":   trader.cancel(args.id)
        case "position": trader.show_position()
        case "balance":  trader.show_balance()


if __name__ == "__main__":
    main()
