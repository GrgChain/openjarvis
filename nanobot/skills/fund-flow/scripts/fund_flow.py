"""
Fund Flow Analysis Module (Tushare Only)
Fetches and analyzes individual stock fund flow data using Tushare Pro.
"""

import pandas as pd
import sys
import io
import warnings
import os
import argparse
import tushare as ts
from datetime import datetime, timedelta


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


class FundFlowDataFetcher:
    """资金流向数据获取类 (Tushare Only)"""
    
    def __init__(self, days=30):
        self.days = days
        
        # Initialize Tushare
        self.ts_pro = None
        self.ts_token = os.environ.get("TUSHARE_TOKEN")
        if not self.ts_token:
            print("❌ Error: TUSHARE_TOKEN not found. Please set it in environment variables or .env file.")
            sys.exit(1)
            
        try:
            ts.set_token(self.ts_token)
            self.ts_pro = ts.pro_api()
        except Exception as e:
            print(f"❌ Error: Tushare initialization failed: {e}")
            sys.exit(1)

    def get_fund_flow_data(self, symbol):
        """
        获取个股资金流向数据
        """
        data = {
            "symbol": symbol,
            "fund_flow_data": None,
            "data_success": False,
            "source": "tushare"
        }
        
        if not symbol.isdigit() or len(symbol) != 6:
            data["error"] = "Symbol must be 6 digits."
            return data
        
        try:
            # Determine market for akshare/tushare
            # market = self._get_market(symbol) 
            # actually we just need ts_code for tushare
            
            # Fetch data
            fund_flow_data = self._get_individual_fund_flow(symbol)
            
            if fund_flow_data:
                data["fund_flow_data"] = fund_flow_data
                data["data_success"] = True
            else:
                data["error"] = "No fund flow data found."
                
        except Exception as e:
            data["error"] = str(e)
        
        return data

    def _get_market(self, symbol):
        """Determine market prefix."""
        if symbol.startswith(('60', '688')):
            return 'sh'
        elif symbol.startswith(('00', '30')):
            return 'sz'
        elif symbol.startswith(('8', '4')):
            return 'bj'
        return 'sz'

    def _convert_to_ts_code(self, symbol):
        """Convert 6-digit symbol to ts_code (e.g. 000001 -> 000001.SZ)."""
        market = self._get_market(symbol)
        if market == 'sh': return f"{symbol}.SH"
        if market == 'bj': return f"{symbol}.BJ"
        return f"{symbol}.SZ"

    def _get_individual_fund_flow(self, symbol):
        """Fetch fund flow via Tushare."""
        try:
            ts_code = self._convert_to_ts_code(symbol)
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=self.days * 2 + 20)).strftime('%Y%m%d') # fetch more to cover non-trading days
            
            # Use moneyflow interface
            df = self.ts_pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is not None and not df.empty:
                # Map columns to match standard Chinese keys
                df = df.rename(columns={
                    'trade_date': '日期',
                    'buy_sm_amount': '小单买入',
                    'sell_sm_amount': '小单卖出',
                    'buy_md_amount': '中单买入',
                    'sell_md_amount': '中单卖出',
                    'buy_lg_amount': '大单买入',
                    'sell_lg_amount': '大单卖出',
                    'buy_elg_amount': '超大单买入',
                    'sell_elg_amount': '超大单卖出',
                    'net_mf_amount': '净额'
                })
                
                # Fetch Close Price and Change Pct for context (using daily)
                # We need to merge this because moneyflow doesn't have close/pct_chg usually
                try:
                    df_daily = self.ts_pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, fields='trade_date,close,pct_chg')
                    if df_daily is not None and not df_daily.empty:
                        df_daily = df_daily.rename(columns={'trade_date': '日期', 'close': '收盘价', 'pct_chg': '涨跌幅'})
                        # Merge on Date
                        df = pd.merge(df, df_daily, on='日期', how='left')
                except:
                    pass

                unit_multiplier = 10000.0
                
                for size in ['超大单', '大单', '中单', '小单']:
                    df[f'{size}净流入-净额'] = (df[f'{size}买入'] - df[f'{size}卖出']) * unit_multiplier
                
                df['主力净流入-净额'] = df['超大单净流入-净额'] + df['大单净流入-净额']
                
                total_buy = sum(df[f'{size}买入'] for size in ['超大单', '大单', '中单', '小单']) * unit_multiplier
                total_buy = total_buy.clip(lower=1)
                
                for size in ['主力', '超大单', '大单', '中单', '小单']:
                    df[f'{size}净流入-净占比'] = (df[f'{size}净流入-净额'] / total_buy) * 100

                df = df.sort_values('日期', ascending=False).head(self.days)
                
                data_list = [{k: v for k, v in row.items() if pd.notna(v)} for row in df.to_dict('records')]
                    
                return {
                    "data": data_list,
                    "days": len(data_list),
                    "market": self._get_market(symbol),
                    "source": "tushare",
                    "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            print(f"   [Tushare] Failed: {e}")
                
        return None

    def format_fund_flow_for_ai(self, data):
        """Format output to rich text."""
        if not data or not data.get("data_success"):
            return f"未能获取资金流向数据: {data.get('error', '未知错误')}"
        
        fund_flow = data.get("fund_flow_data")
        if not fund_flow: return "无数据"
        
        source = fund_flow.get('source', 'unknown')
        symbol = data.get('symbol', 'N/A')
        
        lines = []
        lines.append(f"【个股资金流向数据 - {source}数据源】")
        lines.append(f"股票代码：{symbol}")
        lines.append(f"市场：{fund_flow.get('market', 'N/A').upper()}")
        lines.append(f"交易日数：最近{fund_flow.get('days', 0)}个交易日")
        lines.append(f"查询时间：{fund_flow.get('query_time', 'N/A')}")
        lines.append("")
        lines.append("═══════════════════════════════════════")
        lines.append("[资金流向详细数据]")
        lines.append("═══════════════════════════════════════")
        lines.append("")
        
        # Helper to safely format floats
        def fmt(val, suffix=''):
            if isinstance(val, (int, float)):
                return f"{val:.2f}{suffix}"
            return str(val)

        for idx, item in enumerate(fund_flow.get('data', []), 1):
            date = item.get('日期', 'N/A')
            # Handle Tushare date format (YYYYMMDD to YYYY-MM-DD or keep as is)
            if isinstance(date, str) and len(date) == 8 and date.isdigit():
                date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                
            close = item.get('收盘价', 'N/A')
            pct = item.get('涨跌幅', 'N/A')
            
            lines.append(f"第 {idx} 个交易日 ({date}):")
            if close != 'N/A':
                lines.append(f"  基本信息: 收盘价 {close}, 涨跌幅 {pct}%")
            
            # Main Force
            main_net = item.get('主力净流入-净额', 'N/A')
            main_pct = item.get('主力净流入-净占比', 'N/A')
            lines.append(f"  主力资金: 净流入 {fmt(main_net)}, 占比 {fmt(main_pct, '%')}")
            
            # Extra Large
            elg_net = item.get('超大单净流入-净额', 'N/A')
            elg_pct = item.get('超大单净流入-净占比', 'N/A')
            lines.append(f"  超大单:   净流入 {fmt(elg_net)}, 占比 {fmt(elg_pct, '%')}")

            # Large
            lg_net = item.get('大单净流入-净额', 'N/A')
            lg_pct = item.get('大单净流入-净占比', 'N/A')
            lines.append(f"  大单:     净流入 {fmt(lg_net)}, 占比 {fmt(lg_pct, '%')}")
            
            # Medium
            md_net = item.get('中单净流入-净额', 'N/A')
            md_pct = item.get('中单净流入-净占比', 'N/A')
            lines.append(f"  中单:     净流入 {fmt(md_net)}, 占比 {fmt(md_pct, '%')}")

            # Small
            sm_net = item.get('小单净流入-净额', 'N/A')
            sm_pct = item.get('小单净流入-净占比', 'N/A')
            lines.append(f"  小单:     净流入 {fmt(sm_net)}, 占比 {fmt(sm_pct, '%')}")


            lines.append("")

        # Statistics
        lines.append("═══════════════════════════════════════")
        lines.append(f"[统计汇总 - 最近{fund_flow.get('days', 0)}个交易日]")
        lines.append("═══════════════════════════════════════")
        
        data_list = fund_flow.get('data', [])
        if data_list:
            # Main Inflow Stats
            main_inflows = [x.get('主力净流入-净额', 0) for x in data_list if isinstance(x.get('主力净流入-净额'), (int, float))]
            if main_inflows:
                total = sum(main_inflows)
                avg = total / len(main_inflows)
                pos = len([x for x in main_inflows if x > 0])
                neg = len([x for x in main_inflows if x < 0])
                
                lines.append(f"主力资金统计:")
                lines.append(f"  - 累计净流入: {total:,.2f}")
                lines.append(f"  - 平均日净流入: {avg:,.2f}")
                lines.append(f"  - 净流入天数: {pos}天 ({pos/len(main_inflows)*100:.1f}%)")
                lines.append(f"  - 净流出天数: {neg}天")

            # Price Stats
            pcts = [x.get('涨跌幅', 0) for x in data_list if isinstance(x.get('涨跌幅'), (int, float))]
            if pcts:
                avg_pct = sum(pcts) / len(pcts)
                up = len([x for x in pcts if x > 0])
                down = len([x for x in pcts if x < 0])
             
                lines.append("")
                lines.append(f"股价统计:")
                lines.append(f"  - 平均涨跌幅: {avg_pct:.2f}%")
                lines.append(f"  - 上涨天数: {up}天 ({up/len(pcts)*100:.1f}%)")
                lines.append(f"  - 下跌天数: {down}天")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fund Flow Analysis")
    parser.add_argument("--symbol", type=str, required=True, help="Stock Symbol (6 digits)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    
    args = parser.parse_args()
    
    fetcher = FundFlowDataFetcher(days=args.days)
    data = fetcher.get_fund_flow_data(args.symbol)
    
    print(fetcher.format_fund_flow_for_ai(data))

if __name__ == "__main__":
    main()
