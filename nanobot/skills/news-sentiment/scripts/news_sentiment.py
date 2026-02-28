"""
News Sentiment Module (akshare)
Fetches and aggregates latest stock news from East Money, Sina, and Cailian Press.
Replicated from qstock_news_data.py
"""

import pandas as pd
import sys
import io
import warnings
import argparse
from datetime import datetime
import akshare as ak

warnings.filterwarnings('ignore')

# --------------------------- Stdout Encoding Hack --------------------------- #
def _setup_stdout_encoding():
    """Ensure utf-8 output in terminals."""
    if sys.platform == 'win32' and not hasattr(sys.stdout, '_original_stream'):
        try:
            import streamlit
            return
        except ImportError:
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
            except Exception:
                pass

_setup_stdout_encoding()


class NewsDataFetcher:
    """News data fetcher using akshare (Replicated from QStockNewsDataFetcher)."""
    
    def __init__(self, max_items=30):
        self.max_items = max_items
        self.available = True

    def get_stock_news(self, symbol):
        """
        Fetch stock news data.
        """
        data = {
            "symbol": symbol,
            "news_data": None,
            "data_success": False,
            "source": "akshare" # Renamed from qstock to reflect actual source
        }
        
        if not self.available:
            data["error"] = "akshare library not available"
            return data
        
        # Validation
        if not self._is_chinese_stock(symbol):
            data["error"] = "News data only supports Chinese A-shares (6 digits)"
            return data
        
        try:
            news_data = self._get_news_data(symbol)
            
            if news_data:
                data["news_data"] = news_data
                data["data_success"] = True
            else:
                data["error"] = "No news found"
                
        except Exception as e:
            data["error"] = str(e)
        
        return data
    
    def _is_chinese_stock(self, symbol):
        """Check if symbol is Chinese stock."""
        return symbol.isdigit() and len(symbol) == 6
    
    def _get_news_data(self, symbol):
        """Fetch news data using akshare logic from qstock_news_data.py."""
        try:
            
            news_items = []
            
            # Method 1: East Money (Individual Stock News)
            try:
                # stock_news_em(symbol="600519")
                df = ak.stock_news_em(symbol=symbol)
                
                if df is not None and not df.empty:
                    
                    records = df.head(self.max_items).to_dict('records')
                    for row in records:
                        item = {'source': '东方财富'}
                        for col, value in row.items():
                            if pd.isna(value) or value is None:
                                continue
                            try:
                                item[col] = str(value)
                            except Exception:
                                item[col] = "无法解析"
                        if len(item) > 1:
                            news_items.append(item)
            
            except Exception as e:
                pass
            
            # Method 2: Sina Finance (Fallback)
            if not news_items:
                try:
                    # Get stock name
                    df_info = ak.stock_zh_a_spot_em()
                    
                    stock_name = None
                    if df_info is not None and not df_info.empty:
                        match = df_info[df_info['代码'] == symbol]
                        if not match.empty:
                            stock_name = match.iloc[0]['名称']
                    
                    if stock_name:
                        try:
                            df = ak.stock_news_sina(symbol=stock_name)
                            if df is not None and not df.empty:
                                
                                records = df.head(self.max_items).to_dict('records')
                                for row in records:
                                    item = {'source': '新浪财经'}
                                    for col, value in row.items():
                                        if pd.isna(value) or value is None:
                                            continue
                                        try:
                                            item[col] = str(value)
                                        except Exception:
                                            item[col] = "无法解析"
                                    if len(item) > 1:
                                        news_items.append(item)
                        except Exception:
                            pass
                
                except Exception as e:
                    pass
            
            # Method 3: Cailian Press (Telegraphs)
            if not news_items or len(news_items) < 5:
                try:
                    df = ak.stock_news_cls()
                    
                    if df is not None and not df.empty:
                        # Filter by symbol or title
                        df_filtered = df[
                            df['内容'].str.contains(symbol, na=False) |
                            df['标题'].str.contains(symbol, na=False)
                        ]
                        
                        if not df_filtered.empty:
                            
                            records = df_filtered.head(self.max_items - len(news_items)).to_dict('records')
                            for row in records:
                                item = {'source': '财联社'}
                                for col, value in row.items():
                                    if pd.isna(value) or value is None:
                                        continue
                                    try:
                                        item[col] = str(value)
                                    except Exception:
                                        item[col] = "无法解析"
                                if len(item) > 1:
                                    news_items.append(item)
                
                except Exception as e:
                    pass
            
            if not news_items:
                return None
            
            # Limit count
            news_items = news_items[:self.max_items]
            
            return {
                "items": news_items,
                "count": len(news_items),
                "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "date_range": "最近新闻"
            }
            
        except Exception as e:
            return None

    def format_news_for_ai(self, data):
        """
        Format news data for AI (Replicated from qstock_news_data.py).
        """
        if not data or not data.get("data_success"):
            return "未能获取新闻数据"
        
        text_parts = []
        
        if data.get("news_data"):
            news_data = data["news_data"]
            text_parts.append(f"""
【最新新闻 - akshare数据源】
查询时间：{news_data.get('query_time', 'N/A')}
时间范围：{news_data.get('date_range', 'N/A')}
新闻数量：{news_data.get('count', 0)}条

""")
            
            for idx, item in enumerate(news_data.get('items', []), 1):
                text_parts.append(f"新闻 {idx}:")
                
                # Priority fields
                priority_fields = ['title', 'date', 'time', 'source', 'content', 'url']
                
                # Display priority fields first
                for field in priority_fields:
                    if field in item:
                        value = item[field]
                        # Limit content length
                        if field == 'content' and len(str(value)) > 500:
                            value = str(value)[:500] + "..."
                        text_parts.append(f"  {field}: {value}")
                
                # Display other fields
                for key, value in item.items():
                    if key not in priority_fields and key != 'source':
                        # Skip very long fields
                        if len(str(value)) > 300:
                            value = str(value)[:300] + "..."
                        text_parts.append(f"  {key}: {value}")
                
                text_parts.append("")  # Empty line separator
        
        return "\n".join(text_parts)


def main():
    parser = argparse.ArgumentParser(description="News Sentiment (akshare)")
    parser.add_argument("--symbol", type=str, required=True, help="Stock Symbol")
    parser.add_argument("--limit", type=int, default=30, help="Max news items")
    
    args = parser.parse_args()
    
    fetcher = NewsDataFetcher(max_items=args.limit)
    data = fetcher.get_stock_news(args.symbol)
    
    print(fetcher.format_news_for_ai(data))

if __name__ == "__main__":
    main()
