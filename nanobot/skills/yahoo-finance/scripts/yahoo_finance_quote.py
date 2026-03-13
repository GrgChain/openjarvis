"""
Yahoo Finance Stock Quote Fetcher
Fetches real-time stock quotes from Yahoo Finance using cookie/crumb auth.
Supports single ticker or multiple tickers with retry logic.
"""

import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    import http.cookiejar
    import urllib.request
    _HAS_HTTPX = False


# ─── Constants ───────────────────────────────────────────────────────────────

YAHOO_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
YAHOO_QUOTE_URL = "https://query2.finance.yahoo.com/v7/finance/quote"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

QUOTE_FIELDS = ",".join([
    "symbol", "shortName", "longName",
    "regularMarketPrice", "regularMarketChange", "regularMarketChangePercent",
    "regularMarketPreviousClose", "regularMarketOpen",
    "regularMarketDayHigh", "regularMarketDayLow",
    "regularMarketVolume", "averageDailyVolume3Month",
    "marketCap", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "trailingPE", "forwardPE", "epsTrailingTwelveMonths",
    "dividendYield", "currency", "exchange", "market",
    "regularMarketTime", "marketState",
    "preMarketPrice", "preMarketChange", "preMarketChangePercent",
    "postMarketPrice", "postMarketChange", "postMarketChangePercent",
])

MAX_RETRIES = 2
RETRY_DELAY = 1.0

# Cache for crumb to avoid repeated auth requests
_CRUMB_CACHE = {"crumb": None, "cookies": None, "opener": None, "timestamp": 0}
CRUMB_CACHE_TTL = 300  # 5 minutes


# ─── Auth ────────────────────────────────────────────────────────────────────

def _get_crumb_httpx():
    """Get Yahoo Finance crumb using httpx with caching."""
    now = time.time()
    if _CRUMB_CACHE["crumb"] and (now - _CRUMB_CACHE["timestamp"]) < CRUMB_CACHE_TTL:
        return _CRUMB_CACHE["cookies"], _CRUMB_CACHE["crumb"]

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        client.get("https://fc.yahoo.com")
        resp = client.get(YAHOO_CRUMB_URL)
        resp.raise_for_status()
        crumb = resp.text.strip()

        _CRUMB_CACHE["crumb"] = crumb
        _CRUMB_CACHE["cookies"] = client.cookies
        _CRUMB_CACHE["timestamp"] = now

        return client.cookies, crumb


def _get_crumb_urllib():
    """Get Yahoo Finance crumb using urllib with caching."""
    now = time.time()
    if _CRUMB_CACHE["crumb"] and (now - _CRUMB_CACHE["timestamp"]) < CRUMB_CACHE_TTL:
        return _CRUMB_CACHE["cookies"], _CRUMB_CACHE["opener"], _CRUMB_CACHE["crumb"]

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = list(HEADERS.items())
    opener.open("https://fc.yahoo.com")
    resp = opener.open(YAHOO_CRUMB_URL)
    crumb = resp.read().decode("utf-8").strip()

    _CRUMB_CACHE["crumb"] = crumb
    _CRUMB_CACHE["cookies"] = cj
    _CRUMB_CACHE["opener"] = opener
    _CRUMB_CACHE["timestamp"] = now

    return cj, opener, crumb


# ─── Fetcher ─────────────────────────────────────────────────────────────────

def fetch_quotes(symbols: list[str]) -> dict:
    """Fetch real-time quotes for one or more tickers from Yahoo Finance."""
    result = {
        "symbols": symbols,
        "quotes": [],
        "count": 0,
        "success": False,
        "error": None,
    }

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            params = {
                "symbols": ",".join(symbols),
                "fields": QUOTE_FIELDS,
            }

            if _HAS_HTTPX:
                cookies, crumb = _get_crumb_httpx()
                params["crumb"] = crumb
                url = f"{YAHOO_QUOTE_URL}?{urllib.parse.urlencode(params)}"
                with httpx.Client(
                    headers={**HEADERS, "Accept": "application/json"},
                    cookies=cookies,
                    follow_redirects=True,
                    timeout=15,
                ) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
            else:
                cj, opener, crumb = _get_crumb_urllib()
                params["crumb"] = crumb
                url = f"{YAHOO_QUOTE_URL}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/json"})
                with opener.open(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            quote_response = data.get("quoteResponse", {})
            error = quote_response.get("error")
            if error:
                result["error"] = str(error)
                return result

            raw_quotes = quote_response.get("result", [])
            quotes = []
            for q in raw_quotes:
                quote = {
                    "symbol": q.get("symbol", ""),
                    "name": q.get("shortName") or q.get("longName", ""),
                    "price": q.get("regularMarketPrice"),
                    "change": q.get("regularMarketChange"),
                    "change_pct": q.get("regularMarketChangePercent"),
                    "prev_close": q.get("regularMarketPreviousClose"),
                    "open": q.get("regularMarketOpen"),
                    "high": q.get("regularMarketDayHigh"),
                    "low": q.get("regularMarketDayLow"),
                    "volume": q.get("regularMarketVolume"),
                    "avg_volume": q.get("averageDailyVolume3Month"),
                    "market_cap": q.get("marketCap"),
                    "52w_high": q.get("fiftyTwoWeekHigh"),
                    "52w_low": q.get("fiftyTwoWeekLow"),
                    "pe": q.get("trailingPE"),
                    "forward_pe": q.get("forwardPE"),
                    "eps": q.get("epsTrailingTwelveMonths"),
                    "dividend_yield": q.get("dividendYield"),
                    "currency": q.get("currency", ""),
                    "exchange": q.get("exchange", ""),
                    "market_state": q.get("marketState", ""),
                }

                # Extended hours data
                if q.get("preMarketPrice"):
                    quote["pre_market"] = {
                        "price": q["preMarketPrice"],
                        "change": q.get("preMarketChange"),
                        "change_pct": q.get("preMarketChangePercent"),
                    }
                if q.get("postMarketPrice"):
                    quote["post_market"] = {
                        "price": q["postMarketPrice"],
                        "change": q.get("postMarketChange"),
                        "change_pct": q.get("postMarketChangePercent"),
                    }

                # Market time
                mkt_time = q.get("regularMarketTime")
                if mkt_time:
                    try:
                        dt = datetime.fromtimestamp(mkt_time)
                        quote["market_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except (OSError, ValueError):
                        quote["market_time"] = str(mkt_time)

                quotes.append(quote)

            result["quotes"] = quotes
            result["count"] = len(quotes)
            result["success"] = len(quotes) > 0

            if not quotes:
                result["error"] = f"No quote data for symbols: {', '.join(symbols)}"

            return result

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                # Clear cache on error
                _CRUMB_CACHE["crumb"] = None
                time.sleep(RETRY_DELAY)
                continue

    result["error"] = f"{type(last_error).__name__}: {str(last_error)}"
    return result


# ─── Formatter ───────────────────────────────────────────────────────────────

def _fmt_num(val, decimals=2):
    """Format a number with commas and decimals."""
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:,.{decimals}f}"
    return f"{val:,}"


def _fmt_change(change, pct):
    """Format change with arrow indicator."""
    if change is None:
        return "—"
    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""
    pct_str = f" ({sign}{pct:.2f}%)" if pct is not None else ""
    return f"{arrow} {sign}{change:.2f}{pct_str}"


def _fmt_market_cap(val):
    """Format market cap in human-readable form."""
    if val is None:
        return "—"
    if val >= 1e12:
        return f"{val / 1e12:.2f}T"
    if val >= 1e9:
        return f"{val / 1e9:.2f}B"
    if val >= 1e6:
        return f"{val / 1e6:.2f}M"
    return f"{val:,.0f}"


def format_quote(q: dict) -> str:
    """Format a single quote for display."""
    parts = []

    # Header: symbol, name, price, change
    change_str = _fmt_change(q.get("change"), q.get("change_pct"))
    price_str = _fmt_num(q.get("price"))
    name = q.get("name", "")
    symbol = q.get("symbol", "")
    currency = q.get("currency", "")

    parts.append(f"  {symbol} ({name})  {price_str} {currency}  {change_str}")

    # OHLC
    parts.append(
        f"    开:{_fmt_num(q.get('open'))}  "
        f"高:{_fmt_num(q.get('high'))}  "
        f"低:{_fmt_num(q.get('low'))}  "
        f"昨收:{_fmt_num(q.get('prev_close'))}"
    )

    # Volume & Market Cap
    parts.append(
        f"    成交量:{_fmt_num(q.get('volume'), 0)}  "
        f"均量:{_fmt_num(q.get('avg_volume'), 0)}  "
        f"市值:{_fmt_market_cap(q.get('market_cap'))}"
    )

    # Valuation
    pe_str = _fmt_num(q.get("pe"))
    fpe_str = _fmt_num(q.get("forward_pe"))
    eps_str = _fmt_num(q.get("eps"))
    div_yield = q.get("dividend_yield")
    div_str = f"{div_yield * 100:.2f}%" if div_yield else "—"
    parts.append(f"    PE:{pe_str}  远期PE:{fpe_str}  EPS:{eps_str}  股息率:{div_str}")

    # 52-week range
    parts.append(f"    52周高:{_fmt_num(q.get('52w_high'))}  52周低:{_fmt_num(q.get('52w_low'))}")

    # Extended hours
    if q.get("pre_market"):
        pm = q["pre_market"]
        pm_change = _fmt_change(pm.get("change"), pm.get("change_pct"))
        parts.append(f"    盘前:{_fmt_num(pm.get('price'))} {pm_change}")
    if q.get("post_market"):
        am = q["post_market"]
        am_change = _fmt_change(am.get("change"), am.get("change_pct"))
        parts.append(f"    盘后:{_fmt_num(am.get('price'))} {am_change}")

    # Market state & time
    state = q.get("market_state", "")
    mkt_time = q.get("market_time", "")
    if state or mkt_time:
        parts.append(f"    状态:{state}  行情时间:{mkt_time}")

    return "\n".join(parts)


def format_all(result: dict) -> str:
    """Format the full quote result."""
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"Failed to fetch quotes: {error}"

    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        f"【Yahoo Finance 行情】",
        f"查询时间: {fetch_time}",
        f"共 {result['count']} 只",
        "─" * 60,
    ]

    for q in result["quotes"]:
        parts.append(format_quote(q))
        parts.append("")

    return "\n".join(parts)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Yahoo Finance Stock Quote Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s AAPL
  %(prog)s AAPL MSFT GOOGL
  %(prog)s ^DJI ^GSPC ^IXIC --json
        """
    )
    parser.add_argument(
        "symbols", nargs="+",
        help="One or more stock ticker symbols (e.g. AAPL MSFT TSLA)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of formatted text",
    )

    args = parser.parse_args()
    result = fetch_quotes(args.symbols)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_all(result))

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
