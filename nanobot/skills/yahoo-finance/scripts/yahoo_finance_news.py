"""
Yahoo Finance News Fetcher
Fetches the latest financial news from Yahoo Finance search API and RSS feed.
Supports single query or batch mode for multiple topics/tickers.
Uses RSS feed to enrich news with summaries when available.
Enriches related tickers with real-time quote data (price, change, change%).
"""

import argparse
import json
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

from yahoo_finance_quote import fetch_quotes

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    import urllib.request
    _HAS_HTTPX = False


# ─── Constants ───────────────────────────────────────────────────────────────

YAHOO_SEARCH_API = "https://query1.finance.yahoo.com/v1/finance/search"
YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}
MAX_RETRIES = 2
RETRY_DELAY = 1.0


# ─── Fetcher ─────────────────────────────────────────────────────────────────

def _fetch_with_retry(url: str, retries: int = MAX_RETRIES) -> dict:
    """Fetch URL with retry logic, returns parsed JSON."""
    last_error = None

    for attempt in range(retries + 1):
        try:
            if _HAS_HTTPX:
                with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.json()
            else:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(RETRY_DELAY)
            continue

    raise last_error


def _fetch_text_with_retry(url: str, retries: int = MAX_RETRIES) -> str:
    """Fetch URL with retry logic, returns raw text."""
    last_error = None

    for attempt in range(retries + 1):
        try:
            if _HAS_HTTPX:
                with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.text
            else:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(RETRY_DELAY)
            continue

    raise last_error


def _fetch_rss_summaries(query: str, limit: int = 20) -> dict[str, str]:
    """Fetch RSS feed for a ticker/query and return {uuid: description} mapping."""
    params = {
        "s": query,
        "region": "US",
        "lang": "en-US",
        "count": limit,
    }
    try:
        url = f"{YAHOO_RSS_URL}?{urllib.parse.urlencode(params)}"
        xml_text = _fetch_text_with_retry(url)
        root = ET.fromstring(xml_text)
        summaries = {}
        for item in root.iter("item"):
            guid_el = item.find("guid")
            desc_el = item.find("description")
            if guid_el is not None and desc_el is not None:
                uuid = (guid_el.text or "").strip()
                desc = (desc_el.text or "").strip()
                if uuid and desc:
                    summaries[uuid] = desc
        return summaries
    except Exception:
        return {}


def _enrich_tickers(all_tickers: set[str]) -> dict[str, dict]:
    """Fetch quotes for all tickers and return {symbol: {price, change, change_pct}} mapping."""
    if not all_tickers:
        return {}
    try:
        result = fetch_quotes(list(all_tickers))
        if not result.get("success"):
            return {}
        return {
            q["symbol"]: {
                "price": q.get("price"),
                "change": q.get("change"),
                "change_pct": q.get("change_pct"),
                "currency": q.get("currency", ""),
            }
            for q in result.get("quotes", [])
            if q.get("symbol")
        }
    except Exception:
        return {}


def _fmt_ticker_with_quote(symbol: str, quote_map: dict[str, dict]) -> str:
    """Format a single ticker with quote info, e.g. 'AAPL ▲+1.23(+0.85%)'."""
    q = quote_map.get(symbol)
    if not q or q.get("price") is None:
        return symbol
    change = q.get("change")
    pct = q.get("change_pct")
    if change is None:
        return f"{symbol} {q['price']:.2f}"
    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""
    pct_str = f"({sign}{pct:.2f}%)" if pct is not None else ""
    return f"{symbol} {arrow}{sign}{change:.2f}{pct_str}"


def fetch_yahoo_news(query: str, limit: int = 20) -> dict:
    """Fetch latest news from Yahoo Finance search API for a single query,
    enriched with summaries from RSS feed and ticker quotes."""
    params = {
        "q": query,
        "quotesCount": 0,
        "newsCount": limit,
        "enableFuzzyQuery": "false",
        "quotesQueryId": "tss_match_phrase_query",
        "newsQueryId": "news_cie_vespa",
    }

    result = {
        "query": query,
        "items": [],
        "count": 0,
        "success": False,
        "error": None,
    }

    try:
        url = f"{YAHOO_SEARCH_API}?{urllib.parse.urlencode(params)}"
        data = _fetch_with_retry(url)
        news_list = data.get("news", [])

        # Fetch RSS summaries keyed by uuid
        rss_summaries = _fetch_rss_summaries(query, limit)

        # First pass: build items and collect all tickers
        items = []
        all_tickers = set()
        for n in news_list[:limit]:
            title = n.get("title", "").strip()
            if not title:
                continue

            uuid = n.get("uuid", "")
            summary = rss_summaries.get(uuid, "")

            item = {
                "title": title,
                "publisher": n.get("publisher", ""),
                "link": n.get("link", ""),
                "type": n.get("type", ""),
                "summary": summary,
            }

            pub_time = n.get("providerPublishTime")
            if pub_time:
                try:
                    dt = datetime.fromtimestamp(pub_time)
                    item["publish_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (OSError, ValueError):
                    item["publish_time"] = str(pub_time)

            tickers = n.get("relatedTickers", [])
            if tickers:
                item["_raw_tickers"] = tickers
                all_tickers.update(tickers)

            items.append(item)

        # Enrich tickers with real-time quotes
        quote_map = _enrich_tickers(all_tickers)
        for item in items:
            raw = item.pop("_raw_tickers", [])
            if raw:
                item["related_tickers"] = ", ".join(
                    _fmt_ticker_with_quote(t, quote_map) for t in raw
                )

        result["items"] = items
        result["count"] = len(items)
        result["success"] = len(items) > 0

        if not items:
            result["error"] = f"No news found for '{query}'"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"

    return result


def fetch_batch_news(queries: list[str], limit_per_query: int = 10, verbose: bool = False) -> list[dict]:
    """Fetch news for multiple queries in batch."""
    results = []
    total = len(queries)

    for i, query in enumerate(queries, 1):
        if verbose:
            print(f"[{i}/{total}] Fetching: {query}...", file=sys.stderr, flush=True)

        result = fetch_yahoo_news(query, limit=limit_per_query)
        results.append(result)

        if i < total:
            time.sleep(0.3)

    return results


# ─── Formatter ───────────────────────────────────────────────────────────────

def format_single_result(data: dict) -> str:
    """Format a single query result."""
    if not data.get("success"):
        return f"  ⚠ Failed: {data.get('error', 'Unknown error')}\n"

    parts = []
    for idx, item in enumerate(data["items"], 1):
        parts.append(f"  {idx}. {item['title']}")
        meta = []
        if item.get("publisher"):
            meta.append(item["publisher"])
        if item.get("publish_time"):
            meta.append(item["publish_time"])
        if item.get("related_tickers"):
            meta.append(f"Tickers: {item['related_tickers']}")
        if meta:
            parts.append(f"     {' | '.join(meta)}")
        if item.get("summary"):
            parts.append(f"     {item['summary']}")
        if item.get("link"):
            parts.append(f"     {item['link']}")
        parts.append("")

    return "\n".join(parts)


def format_batch_results(results: list[dict], fetch_time: str) -> str:
    """Format batch results into a comprehensive report."""
    parts = [
        "=" * 60,
        f"【Yahoo Finance News — Batch Report】",
        f"Fetch time: {fetch_time}",
        f"Queries: {len(results)}",
        "=" * 60,
        "",
    ]

    total_items = 0
    for data in results:
        total_items += data.get("count", 0)
        query = data.get("query", "?")
        count = data.get("count", 0)
        status = "✅" if data.get("success") else "❌"

        parts.append(f"{'─' * 50}")
        parts.append(f"{status} [{query}] — {count} items")
        parts.append(f"{'─' * 50}")
        parts.append(format_single_result(data))

    parts.append("=" * 60)
    parts.append(f"Total: {total_items} news items across {len(results)} queries")
    parts.append("=" * 60)

    return "\n".join(parts)


def format_single_news(data: dict) -> str:
    """Format a single query result (non-batch mode)."""
    if not data.get("success"):
        error = data.get("error", "Unknown error")
        return f"Failed to fetch Yahoo Finance news: {error}"

    parts = [
        f"【Yahoo Finance News — \"{data['query']}\"】",
        f"Fetch time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Results: {data['count']} items",
        "",
    ]

    for idx, item in enumerate(data["items"], 1):
        parts.append(f"--- News {idx} ---")
        parts.append(f"  Title:     {item['title']}")
        if item.get("publisher"):
            parts.append(f"  Publisher: {item['publisher']}")
        if item.get("publish_time"):
            parts.append(f"  Time:      {item['publish_time']}")
        if item.get("related_tickers"):
            parts.append(f"  Tickers:   {item['related_tickers']}")
        if item.get("summary"):
            parts.append(f"  Summary:   {item['summary']}")
        if item.get("link"):
            parts.append(f"  URL:       {item['link']}")
        parts.append("")

    return "\n".join(parts)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Yahoo Finance News Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query AAPL
  %(prog)s --queries AAPL TSLA NVDA --limit 5
  %(prog)s --query "AI stocks" --json
        """
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help="Single search keyword or stock ticker",
    )
    parser.add_argument(
        "--queries", type=str, nargs="+", default=None,
        help="Multiple search keywords for batch mode",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max news items per query (default: 20)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of formatted text",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show progress messages (batch mode only)",
    )

    args = parser.parse_args()

    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if args.queries:
        # Batch mode
        results = fetch_batch_news(args.queries, limit_per_query=args.limit, verbose=args.verbose)
        if args.json:
            print(json.dumps({"fetch_time": fetch_time, "results": results}, indent=2, ensure_ascii=False))
        else:
            print(format_batch_results(results, fetch_time))
        if not any(r["success"] for r in results):
            sys.exit(1)
    else:
        # Single query mode
        query = args.query or "stock market"
        data = fetch_yahoo_news(query=query, limit=args.limit)
        if args.json:
            print(json.dumps({"fetch_time": fetch_time, **data}, indent=2, ensure_ascii=False))
        else:
            print(format_single_news(data))
        if not data["success"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
