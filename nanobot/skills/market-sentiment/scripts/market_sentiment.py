"""
Market Sentiment Analysis Module (Tushare Only)
Fetches market sentiment indicators including ARBR, turnover rate, index sentiment, etc.
"""

import pandas as pd
import numpy as np
import tushare as ts
import argparse
from datetime import datetime, timedelta
import warnings
import sys
import io
import json
import os
from pathlib import Path

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
            except:
                pass

_setup_stdout_encoding()


class MarketSentimentDataFetcher:
    """Fetches market sentiment data using Tushare."""
    
    def __init__(self):
        self.arbr_period = 26
        
        # Initialize Tushare
        self.ts_token = os.environ.get("TUSHARE_TOKEN")
        if not self.ts_token:
            print("❌ Error: TUSHARE_TOKEN not found. Please set it in environment variables or .env file.")
            sys.exit(1)
            
        try:
            ts.set_token(self.ts_token)
            self.pro = ts.pro_api()
        except Exception as e:
            print(f"❌ Error: Tushare initialization failed: {e}")
            sys.exit(1)

    def get_market_sentiment_data(self, symbol, stock_data=None):
        """Main method to aggregate all sentiment data."""
        sentiment_data = {
            "symbol": symbol,
            "arbr_data": None,
            "market_index": None,
            "turnover_rate": None,
            "limit_up_down": None,
            "margin_trading": None,
            "fear_greed_index": None,
            "data_success": False
        }
        
        try:
            if not symbol.isdigit() or len(symbol) != 6:
                 sentiment_data["error"] = "Symbol must be 6 digits."
                 return sentiment_data

            # 1. ARBR
            # print(f"📊 Analyzing {symbol} ARBR (Period: {self.arbr_period})...")
            arbr = self._calculate_arbr(symbol, stock_data)
            if arbr:
                sentiment_data["arbr_data"] = arbr

            # 2. Turnover
            # print("📊 Fetching turnover rate...")
            turnover = self._get_turnover_rate(symbol)
            if turnover:
                sentiment_data["turnover_rate"] = turnover

            # 3. Market Index
            # print("📊 Analyzing market index...")
            market = self._get_market_index_sentiment()
            if market:
                sentiment_data["market_index"] = market

            # 4. Limit Up/Down (Generic Market)
            # print("📊 Fetching market limit up/down stats...")
            limit = self._get_limit_up_down_stats()
            if limit:
                sentiment_data["limit_up_down"] = limit

            # 5. Margin Trading
            # print("📊 Fetching margin trading data...")
            margin = self._get_margin_trading_data(symbol)
            if margin:
                sentiment_data["margin_trading"] = margin

            # 6. Fear & Greed (Derived)
            # print("📊 Calculating Fear & Greed Index...")
            fg = self._calculate_fear_greed(market, limit)
            if fg:
                sentiment_data["fear_greed_index"] = fg

            sentiment_data["data_success"] = True
            # print("✅ Market sentiment analysis completed.")

        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            sentiment_data["error"] = str(e)
        
        return sentiment_data

    def _convert_to_ts_code(self, symbol):
        """Convert 6-digit symbol to ts_code (e.g. 000001 -> 000001.SZ)."""
        if symbol.startswith(('6', '9')):
            return f"{symbol}.SH"
        elif symbol.startswith(('4', '8')):
            return f"{symbol}.BJ"
        else:
            return f"{symbol}.SZ"

    def _get_history_data(self, symbol, start_date, end_date):
        """Fetch daily bars via Tushare."""
        ts_code = self._convert_to_ts_code(symbol)
        try:
            df = ts.pro_bar(ts_code=ts_code, adj='qfq', start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "trade_date": "date", 
                    "vol": "volume"
                })
                df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
                return df.sort_values('date')
        except Exception as e:
            print(f"   [Tushare] History fetch failed: {e}")
        return None

    def _calculate_arbr(self, symbol, stock_data=None):
        """Calculate ARBR using historical data."""
        try:
            if stock_data is not None and not stock_data.empty:
                 df = stock_data
            else:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=150)).strftime('%Y%m%d')
                
                df = self._get_history_data(symbol, start_date, end_date)
            
            if df is None or df.empty:
                return None

            # Ensure columns
            cols = {'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low'}
            df = df.rename(columns={k:v for k,v in cols.items() if k in df.columns})

            # Calculate AR/BR
            df['HO'] = df['high'] - df['open']
            df['OL'] = df['open'] - df['low']
            df['HCY'] = df['high'] - df['close'].shift(1)
            df['CYL'] = df['close'].shift(1) - df['low']
            
            # Avoid division by zero
            ol_sum = df['OL'].rolling(window=self.arbr_period).sum()
            cyl_sum = df['CYL'].rolling(window=self.arbr_period).sum()
            
            df['AR'] = (df['HO'].rolling(window=self.arbr_period).sum() / ol_sum.replace(0, np.nan)) * 100
            df['BR'] = (df['HCY'].rolling(window=self.arbr_period).sum() / cyl_sum.replace(0, np.nan)) * 100
            
            df = df.dropna(subset=['AR', 'BR'])
            if df.empty: return None
            
            latest = df.iloc[-1]
            ar_val, br_val = latest['AR'], latest['BR']
            
            stats = {
                "ar_mean": df['AR'].mean(),
                "ar_std": df['AR'].std(),
                "ar_min": df['AR'].min(),
                "ar_max": df['AR'].max(),
                "br_mean": df['BR'].mean(),
                "br_std": df['BR'].std(),
                "br_min": df['BR'].min(),
                "br_max": df['BR'].max(),
            }
            
            # Simple compatibility mapping for format function
            stats['ar_ma'] = stats['ar_mean']
            stats['br_ma'] = stats['br_mean']
            
            interpretation = self._interpret_arbr(ar_val, br_val)
            signals = self._generate_arbr_signals(ar_val, br_val)
            
            return {
                "latest_ar": float(ar_val),
                "latest_br": float(br_val),
                "interpretation": interpretation,
                "signals": signals,
                "stats": stats,
                "date": latest['date'].strftime('%Y-%m-%d')
            }
        except Exception as e:
            print(f"   ARBR Logic Failed: {e}")
            return None

    def _interpret_arbr(self, ar_value, br_value):
        """Interprets ARBR values (Ported from market_sentiment_data.py)."""
        interpretation = []
        
        # AR
        if ar_value > 180:
            interpretation.append("AR极度超买（>180），市场过热，风险极高，建议谨慎")
        elif ar_value > 150:
            interpretation.append("AR超买（>150），市场情绪过热，注意回调风险")
        elif ar_value < 40:
            interpretation.append("AR极度超卖（<40），市场过冷，可能存在机会")
        elif ar_value < 70:
            interpretation.append("AR超卖（<70），市场情绪低迷，可关注反弹机会")
        else:
            interpretation.append(f"AR处于正常区间（{ar_value:.2f}），市场情绪相对平稳")
        
        # BR
        if br_value > 400:
            interpretation.append("BR极度超买（>400），投机情绪过热，警惕泡沫")
        elif br_value > 300:
            interpretation.append("BR超买（>300），投机情绪旺盛，注意风险")
        elif br_value < 30:
            interpretation.append("BR极度超卖（<30），投机情绪冰点，可能触底")
        elif br_value < 50:
            interpretation.append("BR超卖（<50），投机情绪低迷，关注企稳信号")
        else:
            interpretation.append(f"BR处于正常区间（{br_value:.2f}），投机情绪适中")
        
        # Relation
        if ar_value > 100 and br_value > 100:
            interpretation.append("多头力量强劲（AR>100且BR>100），但需警惕过热风险")
        elif ar_value < 100 and br_value < 100:
            interpretation.append("空头力量占优（AR<100且BR<100），市场情绪偏空")
        
        if ar_value > br_value:
            interpretation.append("人气指标强于意愿指标（AR>BR），市场基础较好，投资者信心相对稳定")
        else:
            interpretation.append("意愿指标强于人气指标（BR>AR），投机性较强，需注意资金稳定性")
        
        return interpretation

    def _generate_arbr_signals(self, ar_value, br_value):
        """Generates ARBR signals (Ported from market_sentiment_data.py)."""
        signals = []
        signal_strength = 0
        
        # AR
        if ar_value > 150:
            signals.append("AR卖出信号")
            signal_strength -= 1
        elif ar_value < 70:
            signals.append("AR买入信号")
            signal_strength += 1
        
        # BR
        if br_value > 300:
            signals.append("BR卖出信号")
            signal_strength -= 1
        elif br_value < 50:
            signals.append("BR买入信号")
            signal_strength += 1
        
        if signal_strength >= 2: overall = "强烈买入信号"
        elif signal_strength == 1: overall = "买入信号"
        elif signal_strength == -1: overall = "卖出信号"
        elif signal_strength <= -2: overall = "强烈卖出信号"
        else: overall = "中性信号"
        
        return {
            "individual_signals": signals if signals else ["中性"],
            "overall_signal": overall,
            "signal_strength": signal_strength
        }

    def _get_turnover_rate(self, symbol):
        """Fetch latest turnover rate."""
        ts_code = self._convert_to_ts_code(symbol)
        try:
             # Get latest trading date first? Or just try today and yesterday
            # Simplify: get last 5 days and take latest
            end_dt = datetime.now().strftime('%Y%m%d')
            start_dt = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            
            df = self.pro.daily_basic(ts_code=ts_code, start_date=start_dt, end_date=end_dt, fields='trade_date,turnover_rate,turnover_rate_f')
            if df is not None and not df.empty:
                latest = df.iloc[0] # date is usually descending in tushare normal apis, ensure sorting?
                # pro apis mostly return unsorted or date descending?
                # actually daily_basic might be date desc
                 # Sort just in case
                df = df.sort_values('trade_date', ascending=False)
                latest = df.iloc[0]
                
                tr = float(latest['turnover_rate'])
                interp = ""
                # Logic from market_sentiment_data.py
                if tr > 20: interp = "换手率极高（>20%），资金活跃度极高，可能存在炒作"
                elif tr > 10: interp = "换手率较高（>10%），交易活跃"
                elif tr > 5: interp = "换手率正常（5%-10%），交易适中"
                elif tr > 2: interp = "换手率偏低（2%-5%），交易相对清淡"
                else: interp = "换手率很低（<2%），交易清淡"
                
                return {
                    "current": float(tr),
                    "interpretation": interp,
                    "date": latest['trade_date']
                }
        except Exception as e:
            print(f"   Turnover Fetch Failed: {e}")
        return None

    def _get_market_index_sentiment(self):
        """Get index sentiment (SSE Composite)."""
        try:
            # 000001.SH = SSE Composite
            end_dt = datetime.now().strftime('%Y%m%d')
            start_dt = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            
            df = self.pro.index_daily(ts_code='000001.SH', start_date=start_dt, end_date=end_dt)
            if df is not None and not df.empty:
                df = df.sort_values('trade_date', ascending=False)
                latest = df.iloc[0]
                pct_chg = latest['pct_chg']
                
                return {
                    "index": "SSE Composite",
                    "change_pct": float(pct_chg),
                    "date": latest['trade_date']
                }
        except Exception as e:
            print(f"   Index Fetch Failed: {e}")
        return None

    def _get_limit_up_down_stats(self):
        """
        Get Limit Up/Down counts.
        Since Tushare's limit_list might check permissions, we might fallback to daily stats aggregation
        if limit_list is empty.
        """
        date_str = datetime.now().strftime('%Y%m%d')
        # Check if today is trading day, else find last
        # Actually pro.limit_list without date gives latest? No, date required usually.
        # Let's try to get latest trading calendar
        try:
             cal = self.pro.trade_cal(exchange='', is_open='1', start_date=(datetime.now()-timedelta(days=10)).strftime('%Y%m%d'), end_date=date_str)
             if cal is not None and not cal.empty:
                 last_trade_date = cal.iloc[-1]['cal_date']
             else:
                 last_trade_date = date_str
        except:
             last_trade_date = date_str

        try:
            # Try limit_list
            df_up = self.pro.limit_list(trade_date=last_trade_date, limit_type='U')
            df_down = self.pro.limit_list(trade_date=last_trade_date, limit_type='D')
            
            up_count = len(df_up) if df_up is not None else 0
            down_count = len(df_down) if df_down is not None else 0
            
            # If both 0, maybe API issue or permission? Just return 0s
            
            return {
                "limit_up": up_count,
                "limit_down": down_count,
                "date": last_trade_date
            }
        except Exception as e:
            print(f"   Limit Stats Failed: {e}")
        return None

    def _get_margin_trading_data(self, symbol):
        """Get margin trading data for specific stock (margin_detail)."""
        ts_code = self._convert_to_ts_code(symbol)
        try:
            end_dt = datetime.now().strftime('%Y%m%d')
            start_dt = (datetime.now() - timedelta(days=20)).strftime('%Y%m%d')
            
            # margin_detail for individual stock
            df = self.pro.margin_detail(ts_code=ts_code, start_date=start_dt, end_date=end_dt)
            if df is not None and not df.empty:
                df = df.sort_values('trade_date', ascending=False)
                latest = df.iloc[0]
                
                rzye = latest['rzye'] # Margin Balance
                rqye = latest['rqye'] # Short Balance
                
                return {
                    "margin_balance": float(rzye),
                    "short_balance": float(rqye),
                    "date": latest['trade_date']
                }
        except Exception as e:
            print(f"   Margin Fetch Failed: {e}")
            # Try fetching aggregate market margin if individual fails?
            # self.pro.margin(exchange_id='SSE', ...)
        return None

    def _calculate_fear_greed(self, market, limit):
        """Calculates Fear & Greed Index (Based on logic from market_sentiment_data.py)."""
        if not market: # limit is less critical, but good to have
            return None
        
        try:
            score = 50
            factors = []
            
            # Original logic used AKShare's up/down counts. Here we use Tushare daily data if available.
            # But we don't have up/down counts in 'market' from _get_market_index_sentiment (only index change)
            # We can approximate with Limit Up/Down counts which we have.
            
            # Let's try to get broader market up/down stats if possible.
            # Since _get_limit_up_down_stats only returns limit counts, distinct from total market up/down.
            # We will use what we have:
            
            # 1. Market Index Change
            pct = market.get('change_pct', 0)
            score += pct * 5
            factors.append(f"Index Change: {pct}%")
            
            # 2. Limit Ratio (proxy for market breadth/sentiment)
            if limit:
                up = limit.get('limit_up', 0)
                down = limit.get('limit_down', 0)
                total = up + down
                if total > 0:
                    limit_ratio = up / total
                    # Map to AKShare logic roughly: (up_ratio - 0.5) * 60
                    # Here we use limit_ratio as a proxy.
                    score += (limit_ratio - 0.5) * 40
                    factors.append(f"Limit Up Ratio: {limit_ratio:.1%}")

            score = max(0, min(100, score))
            
            if score >= 75:
                level = "极度贪婪"
                interpretation = "市场情绪极度乐观，投资者贪婪，需警惕回调风险"
            elif score >= 60:
                level = "贪婪"
                interpretation = "市场情绪乐观，投资者偏向贪婪"
            elif score >= 40:
                level = "中性"
                interpretation = "市场情绪中性，投资者相对理性"
            elif score >= 25:
                level = "恐慌"
                interpretation = "市场情绪悲观，投资者偏向恐慌"
            else:
                level = "极度恐慌"
                interpretation = "市场情绪极度悲观，投资者恐慌，可能存在超卖机会"
            
            return {
                "score": score,
                "level": level,
                "interpretation": interpretation,
                "factors": factors
            }
        except Exception as e:
             print(f"Fear/Greed Calc Failed: {e}")
             return None

    def format_sentiment_data_for_ai(self, sentiment_data):
        """Format sentiment data into a rich text report."""
        if not sentiment_data or not sentiment_data.get("data_success"):
            return "未能获取市场情绪数据" if not sentiment_data.get("error") else f"获取失败: {sentiment_data['error']}"
        
        text_parts = []
        
        # ARBR
        if sentiment_data.get("arbr_data"):
            arbr = sentiment_data["arbr_data"]
            # New script uses 'stats' key
            stats = arbr.get('stats', {})
            text_parts.append(f"""
【ARBR市场情绪指标】
- 计算周期：{self.arbr_period}日
- AR值：{arbr.get('latest_ar', 'N/A'):.2f}（人气指标）
- BR值：{arbr.get('latest_br', 'N/A'):.2f}（意愿指标）
- 解读：
{chr(10).join(['  * ' + item for item in arbr.get('interpretation', [])])}

ARBR统计数据：
- AR均值：{stats.get('ar_ma', 0):.2f}
- BR均值：{stats.get('br_ma', 0):.2f}
""")
        
        # Turnover
        if sentiment_data.get("turnover_rate"):
            turnover = sentiment_data["turnover_rate"]
            text_parts.append(f"""
【换手率数据】
- 当前换手率：{turnover.get('current', 'N/A')}%
- 解读：{turnover.get('interpretation', 'N/A')}
""")
        
        # Market Index
        if sentiment_data.get("market_index"):
            market = sentiment_data["market_index"]
            text_parts.append(f"""
【大盘市场情绪】
- 指数：{market.get('index', 'N/A')}
- 涨跌幅：{market.get('change_pct', 'N/A')}%
""")
        
        # Limit Stats
        if sentiment_data.get("limit_up_down"):
            limit = sentiment_data["limit_up_down"]
            up = limit.get('limit_up', 0)
            down = limit.get('limit_down', 0)
            total = up + down
            ratio = f"{up/total*100:.1f}%" if total > 0 else "N/A"
            text_parts.append(f"""
【涨跌停统计】
- 涨停股数量：{up}只
- 跌停股数量：{down}只
- 涨停占比：{ratio}
""")
        
        # Margin
        if sentiment_data.get("margin_trading"):
            margin = sentiment_data["margin_trading"]
            text_parts.append(f"""
【融资融券数据】
- 融资余额：{margin.get('margin_balance', 'N/A')}元
- 融券余额：{margin.get('short_balance', 'N/A')}元
""")
        
        # Fear Greed
        if sentiment_data.get("fear_greed_index"):
            fg = sentiment_data["fear_greed_index"]
            text_parts.append(f"""
【市场恐慌贪婪指数】
- 指数得分：{fg.get('score', 'N/A'):.1f}/100
- 情绪等级：{fg.get('level', 'N/A')}
""")
        
        return "\n".join(text_parts)


def load_local_data(data_dir, symbol):
    """Load stock data from CSV."""
    if not data_dir: return None
    path = Path(data_dir) / f"{symbol}.csv"
    if not path.exists():
        # print(f"⚠️ Local file not found: {path}")
        return None
    try:
        df = pd.read_csv(path)
        # Ensure columns match what we need (lowercase)
        # Standardize columns
        df = df.rename(columns=lambda x: x.lower())
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        return df
    except Exception as e:
        # print(f"⚠️ Failed to load local data: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Market Sentiment Analysis (Tushare)")
    parser.add_argument("--symbol", type=str, required=True, help="Stock Symbol (6 digits)")
    parser.add_argument("--data-dir", type=str, default="kline_data", help="Directory containing stock CSVs")
    
    args = parser.parse_args()
    
    fetcher = MarketSentimentDataFetcher()
    
    stock_data = None
    if args.data_dir:
        # print(f"📂 Loading local data from {args.data_dir}...")
        stock_data = load_local_data(args.data_dir, args.symbol)

    data = fetcher.get_market_sentiment_data(args.symbol, stock_data)
    
    report_text = fetcher.format_sentiment_data_for_ai(data)
    print(report_text)

if __name__ == "__main__":
    main()
