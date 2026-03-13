"""
Risk Assessment Module (pywencai)
Fetches stock risk data: Lifting Bans, Shareholder Reductions, Important Events.
"""

import pywencai
import pandas as pd
import time
import warnings
import os
import sys
import io
import argparse
from datetime import datetime

# Terminate warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
os.environ['PYTHONWARNINGS'] = 'ignore::DeprecationWarning'
os.environ['NODE_NO_WARNINGS'] = '1'

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


class RiskDataFetcher:
    """Fetches risk data using pywencai."""
    
    def __init__(self):
        pass
    
    def get_risk_data(self, symbol):
        """Fetch all risk data."""
        # print(f"\nFetching risk data for {symbol}...") # Silenced
        
        risk_data = {
            'symbol': symbol,
            'data_success': False,
            'lifting_ban': None,
            'shareholder_reduction': None,
            'important_events': None,
            'error': None
        }
        
        try:
            # 1. Lifting Ban
            # print("   Querying lifting bans...")
            lifting_ban = self._get_lifting_ban_data(symbol)
            risk_data['lifting_ban'] = lifting_ban
            
            # 2. Shareholder Reduction
            # print("   Querying shareholder reductions...")
            reduction = self._get_shareholder_reduction_data(symbol)
            risk_data['shareholder_reduction'] = reduction
            
            # 3. Important Events
            # print("   Querying important events...")
            events = self._get_important_events_data(symbol)
            risk_data['important_events'] = events
            
            # Check success
            if (lifting_ban and lifting_ban.get('has_data')) or \
               (reduction and reduction.get('has_data')) or \
               (events and events.get('has_data')):
                risk_data['data_success'] = True
            
        except Exception as e:
            risk_data['error'] = str(e)
        
        return risk_data
    
    def _get_lifting_ban_data(self, symbol):
        """Fetch lifting ban data."""
        return self._query_wencai(f"{symbol}限售解禁", "Lifting Ban")
    
    def _get_shareholder_reduction_data(self, symbol):
        """Fetch shareholder reduction data."""
        return self._query_wencai(f"{symbol}大股东减持公告", "Shareholder Reduction")
    
    def _get_important_events_data(self, symbol):
        """Fetch important events."""
        return self._query_wencai(f"{symbol}近期重要事件", "Important Events")

    def _query_wencai(self, query, label):
        """Generic wencai query handler."""
        result = {
            'has_data': False,
            'query': query,
            'data': None,
            'error': None
        }
        try:
            # pywencai.get returns DataFrame or None/Dict
            response = pywencai.get(query=query, loop=True)
            
            if response is None:
                return result
                
            df = self._convert_to_dataframe(response)
            
            if df is not None and not df.empty:
                result['has_data'] = True
                result['data'] = df
                
        except Exception as e:
            # print(f"   [{label}] Query Failed: {e}")
            result['error'] = str(e)
            
        return result
    
    def _convert_to_dataframe(self, result):
        """Convert pywencai result to DataFrame."""
        try:
            if result is None: return None
            
            df_result = None
            if isinstance(result, dict):
                try:
                    df_result = pd.DataFrame([result])
                except Exception: return None
            elif isinstance(result, pd.DataFrame):
                df_result = result
            else:
                return None
            
            if df_result is None or df_result.empty: return None
            
            # Handle standard pywencai return structure variations
            # Sometimes it returns a single row with a nested DataFrame or List
            
            # Case 1: 'tableV1' column
            if 'tableV1' in df_result.columns and len(df_result.columns) == 1:
                table_v1 = df_result.iloc[0]['tableV1']
                if isinstance(table_v1, (pd.DataFrame, list)):
                    df_result = pd.DataFrame(table_v1)

            # Case 2: Single column containing DataFrame (generalization)
            elif len(df_result.columns) == 1:
                val = df_result.iloc[0][df_result.columns[0]]
                if isinstance(val, (pd.DataFrame, list)):
                    df_result = pd.DataFrame(val)
            
            return df_result if not df_result.empty else None
            
        except Exception as e:
            return None

    def format_risk_data_for_ai(self, risk_data):
        """格式化风险数据供AI分析使用 - 直接转换DataFrame为字符串"""
        if not risk_data or not risk_data.get('data_success'):
            return "未获取到风险数据"
        
        formatted_text = []
        symbol = risk_data.get('symbol', 'N/A')
        formatted_text.append(f"【{symbol} 风险评估报告】")
        formatted_text.append(f"查询时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        formatted_text.append("")
        
        try:
            sections = [
                ("限售解禁数据", risk_data.get('lifting_ban')),
                ("大股东减持数据", risk_data.get('shareholder_reduction')),
                ("重要事件数据", risk_data.get('important_events'))
            ]
            
            for title, section_data in sections:
                formatted_text.append("=" * 80)
                formatted_text.append(f"【{title}】")
                formatted_text.append("=" * 80)
                
                if section_data and section_data.get('has_data') and section_data.get('data') is not None:
                    formatted_text.append(f"查询语句: {section_data.get('query', '')}")
                    formatted_text.append("")
                    
                    df = section_data.get('data')
                    try:
                        df_str = df.head(50).to_string(index=False, max_rows=50, max_cols=20)
                        formatted_text.append(f"共 {len(df)} 条记录，显示前50条：")
                        formatted_text.append(df_str)
                    except Exception as e:
                        formatted_text.append(f"数据转换失败: {str(e)}")
                else:
                    formatted_text.append(f"暂无{title}")
                formatted_text.append("")
            
            return "\n".join(formatted_text) if formatted_text else "暂无风险数据"
            
        except Exception as e:
            return f"格式化风险数据时出错: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="Risk Assessment (pywencai)")
    parser.add_argument("--symbol", type=str, required=True, help="Stock Symbol (e.g., 000001)")
    
    args = parser.parse_args()
    
    fetcher = RiskDataFetcher()
    data = fetcher.get_risk_data(args.symbol)
    
    print(fetcher.format_risk_data_for_ai(data))

if __name__ == "__main__":
    main()
