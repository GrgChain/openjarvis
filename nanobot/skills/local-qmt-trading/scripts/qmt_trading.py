"""
Local QMT Trading API Client
REST API client for XT量化下单服务 (miniQMT).
Base URL is configured via QMT_API_URL environment variable.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    _HAS_HTTPX = False


# ─── Config ──────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("QMT_API_URL", "http://192.168.20.158:8001")


# ─── HTTP Helpers ────────────────────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> dict:
    """Send a GET request."""
    url = f"{BASE_URL}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v)
        if query:
            url = f"{url}?{query}"

    if _HAS_HTTPX:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
    else:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))


def _post(path: str, data: dict, params: dict | None = None) -> dict:
    """Send a POST request with JSON body."""
    url = f"{BASE_URL}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v)
        if query:
            url = f"{url}?{query}"

    if _HAS_HTTPX:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()
    else:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))


# ─── API Functions ───────────────────────────────────────────────────────────

def health():
    """Health check — show all account connection status."""
    return _get("/api/v1/health")


def assets(account_id: str | None = None):
    """Query account assets (cash, market value, etc.)."""
    params = {"account_id": account_id} if account_id else None
    return _get("/api/v1/account/assets", params)


def positions(account_id: str | None = None):
    """Query current positions."""
    params = {"account_id": account_id} if account_id else None
    return _get("/api/v1/positions", params)


def orders(account_id: str | None = None):
    """Query today's orders."""
    params = {"account_id": account_id} if account_id else None
    return _get("/api/v1/orders", params)


def trades(account_id: str | None = None):
    """Query today's trades."""
    params = {"account_id": account_id} if account_id else None
    return _get("/api/v1/trades", params)


def history_trades(account_id: str | None = None,
                   start_date: str = "", end_date: str = ""):
    """Query historical trades."""
    params = {}
    if account_id:
        params["account_id"] = account_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    return _get("/api/v1/trades/history", params or None)


def buy(stock_code: str, quantity: int, price: float = 0,
        price_type: str = "limit", account_id: str | None = None,
        strategy_name: str = "", order_remark: str = ""):
    """Submit a buy order."""
    data = {
        "stock_code": stock_code,
        "quantity": quantity,
        "price": price,
        "price_type": price_type,
    }
    if strategy_name:
        data["strategy_name"] = strategy_name
    if order_remark:
        data["order_remark"] = order_remark
    params = {"account_id": account_id} if account_id else None
    return _post("/api/v1/order/buy", data, params)


def sell(stock_code: str, quantity: int, price: float = 0,
         price_type: str = "limit", account_id: str | None = None,
         strategy_name: str = "", order_remark: str = ""):
    """Submit a sell order."""
    data = {
        "stock_code": stock_code,
        "quantity": quantity,
        "price": price,
        "price_type": price_type,
    }
    if strategy_name:
        data["strategy_name"] = strategy_name
    if order_remark:
        data["order_remark"] = order_remark
    params = {"account_id": account_id} if account_id else None
    return _post("/api/v1/order/sell", data, params)


def cancel(order_id: int, account_id: str | None = None):
    """Cancel a pending order."""
    data = {"order_id": order_id}
    params = {"account_id": account_id} if account_id else None
    return _post("/api/v1/order/cancel", data, params)


# ─── Formatters ──────────────────────────────────────────────────────────────

STOCK_NAMES = {}

def get_stock_name(code: str) -> str:
    if not STOCK_NAMES:
        csv_path = os.path.join(os.path.dirname(__file__), "stocklist.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "ts_code" in row and "name" in row:
                        STOCK_NAMES[row["ts_code"]] = row["name"]
    return STOCK_NAMES.get(code, "")


ORDER_STATUS = {
    48: "未报", 49: "待报", 50: "已报", 51: "已报待撤",
    52: "部成待撤", 53: "部撤", 54: "已撤", 55: "部成",
    56: "已成", 57: "废单",
}


def fmt_assets(data: dict) -> str:
    return (
        f"【账户资金 — {data.get('account_id', '?')}】\n"
        f"  总资产:   {data.get('total_asset', 0):,.2f}\n"
        f"  可用资金: {data.get('cash', 0):,.2f}\n"
        f"  冻结资金: {data.get('frozen_cash', 0):,.2f}\n"
        f"  持仓市值: {data.get('market_value', 0):,.2f}\n"
        f"  总负债:   {data.get('total_debt', 0):,.2f}"
    )


def fmt_positions(data: dict) -> str:
    acct = data.get("account_id", "?")
    pos_list = data.get("positions", [])
    if not pos_list:
        return f"【持仓 — {acct}】\n  无持仓"
    lines = [f"【持仓 — {acct}】({len(pos_list)} 只)"]
    for p in pos_list:
        code = p.get("stock_code", "")
        name = p.get("stock_name") or get_stock_name(code) or code
        lines.append(
            f"  {name}({code})  "
            f"持仓:{p.get('volume', 0)}  "
            f"可卖:{p.get('can_use_volume', 0)}  "
            f"成本:{p.get('avg_price', 0):.2f}  "
            f"市值:{p.get('market_value', 0):,.2f}"
        )
    return "\n".join(lines)


def fmt_orders(data: dict) -> str:
    acct = data.get("account_id", "?")
    order_list = data.get("orders", [])
    if not order_list:
        return f"【当日委托 — {acct}】\n  无委托"
    lines = [f"【当日委托 — {acct}】({len(order_list)} 条)"]
    for o in order_list:
        direction = "买入" if o.get("order_type") == 23 else "卖出"
        status = ORDER_STATUS.get(o.get("order_status", 0), str(o.get("order_status")))
        t = o.get("order_time", 0)
        time_str = datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else "?"
        code = o.get('stock_code', '?')
        name = get_stock_name(code) or code
        lines.append(
            f"  [{time_str}] {direction} {name}({code})  "
            f"委托:{o.get('order_volume', 0)}@{o.get('price', 0):.2f}  "
            f"成交:{o.get('traded_volume', 0)}@{o.get('traded_price', 0):.2f}  "
            f"状态:{status}"
        )
    return "\n".join(lines)


def fmt_trades(data: dict) -> str:
    acct = data.get("account_id", "?")
    trade_list = data.get("trades", [])
    if not trade_list:
        return f"【成交记录 — {acct}】\n  无成交"
    lines = [f"【成交记录 — {acct}】({len(trade_list)} 条)"]
    for tr in trade_list:
        direction = "买入" if tr.get("order_type") == 48 else "卖出"
        t = tr.get("traded_time", 0)
        time_str = datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else "?"
        code = tr.get('stock_code', '?')
        name = get_stock_name(code) or code
        lines.append(
            f"  [{time_str}] {direction} {name}({code})  "
            f"{tr.get('traded_volume', 0)}股@{tr.get('traded_price', 0):.2f}  "
            f"金额:{tr.get('traded_amount', 0):,.2f}"
        )
    return "\n".join(lines)


def fmt_cancel_response(data: dict) -> str:
    return (
        f"【撤单结果】\n"
        f"  账户:   {data.get('account_id', '?')}\n"
        f"  订单ID: {data.get('order_id', '?')}\n"
        f"  状态:   {data.get('status', '?')}\n"
        f"  信息:   {data.get('message', '')}"
    )


def fmt_order_response(data: dict) -> str:
    return (
        f"【下单结果】\n"
        f"  账户:   {data.get('account_id', '?')}\n"
        f"  方向:   {data.get('direction', '?')}\n"
        f"  代码:   {data.get('stock_code', '?')}\n"
        f"  数量:   {data.get('quantity', 0)}\n"
        f"  价格:   {data.get('price', 0)}\n"
        f"  类型:   {data.get('price_type', '?')}\n"
        f"  订单ID: {data.get('order_id', '?')}\n"
        f"  状态:   {data.get('status', '?')}\n"
        f"  信息:   {data.get('message', '')}"
    )


def fmt_health(data: dict) -> str:
    lines = [
        f"【服务健康检查】",
        f"  状态:   {data.get('status', '?')}",
        f"  xtquant: {'可用' if data.get('xtquant_available') else '不可用'}",
    ]
    for acc in data.get("accounts", []):
        status = "已连接 ✅" if acc.get("connected") else "未连接 ❌"
        lines.append(f"  账户 {acc.get('account_id', '?')}: {status}")
    if not data.get("accounts"):
        lines.append("  无配置账户")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Local QMT Trading API Client",
        epilog="Environment: QMT_API_URL (default: http://192.168.20.158:8001)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # health
    sub.add_parser("health", help="健康检查")

    # assets
    p = sub.add_parser("assets", help="查询账户资金")
    p.add_argument("--account-id", default=None)

    # positions
    p = sub.add_parser("positions", help="查询当前持仓")
    p.add_argument("--account-id", default=None)

    # orders
    p = sub.add_parser("orders", help="查询当日委托")
    p.add_argument("--account-id", default=None)

    # trades
    p = sub.add_parser("trades", help="查询当日成交")
    p.add_argument("--account-id", default=None)

    # history
    p = sub.add_parser("history", help="查询历史成交")
    p.add_argument("--account-id", default=None)
    p.add_argument("--start-date", default="", help="起始日期 YYYYMMDD")
    p.add_argument("--end-date", default="", help="结束日期 YYYYMMDD")

    # buy
    p = sub.add_parser("buy", help="买入下单")
    p.add_argument("--stock-code", required=True, help="股票代码 (e.g. 600519.SH)")
    p.add_argument("--quantity", type=int, required=True, help="数量（股）")
    p.add_argument("--price", type=float, default=0, help="价格 (限价单必填)")
    p.add_argument("--price-type", default="limit", choices=["limit", "market"])
    p.add_argument("--account-id", default=None)
    p.add_argument("--strategy-name", default="")
    p.add_argument("--order-remark", default="")

    # cancel
    p = sub.add_parser("cancel", help="撤销委托")
    p.add_argument("--order-id", type=int, required=True, help="要撤销的订单ID")
    p.add_argument("--account-id", default=None)

    # sell
    p = sub.add_parser("sell", help="卖出下单")
    p.add_argument("--stock-code", required=True, help="股票代码 (e.g. 600519.SH)")
    p.add_argument("--quantity", type=int, required=True, help="数量（股）")
    p.add_argument("--price", type=float, default=0, help="价格 (限价单必填)")
    p.add_argument("--price-type", default="limit", choices=["limit", "market"])
    p.add_argument("--account-id", default=None)
    p.add_argument("--strategy-name", default="")
    p.add_argument("--order-remark", default="")

    args = parser.parse_args()

    try:
        if args.command == "health":
            result = health()
            print(fmt_health(result))

        elif args.command == "assets":
            result = assets(args.account_id)
            print(fmt_assets(result))

        elif args.command == "positions":
            result = positions(args.account_id)
            print(fmt_positions(result))

        elif args.command == "orders":
            result = orders(args.account_id)
            print(fmt_orders(result))

        elif args.command == "trades":
            result = trades(args.account_id)
            print(fmt_trades(result))

        elif args.command == "history":
            result = history_trades(args.account_id, args.start_date, args.end_date)
            print(fmt_trades(result))

        elif args.command == "cancel":
            result = cancel(
                order_id=args.order_id,
                account_id=args.account_id,
            )
            print(fmt_cancel_response(result))

        elif args.command == "buy":
            result = buy(
                stock_code=args.stock_code,
                quantity=args.quantity,
                price=args.price,
                price_type=args.price_type,
                account_id=args.account_id,
                strategy_name=args.strategy_name,
                order_remark=args.order_remark,
            )
            print(fmt_order_response(result))

        elif args.command == "sell":
            result = sell(
                stock_code=args.stock_code,
                quantity=args.quantity,
                price=args.price,
                price_type=args.price_type,
                account_id=args.account_id,
                strategy_name=args.strategy_name,
                order_remark=args.order_remark,
            )
            print(fmt_order_response(result))

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
