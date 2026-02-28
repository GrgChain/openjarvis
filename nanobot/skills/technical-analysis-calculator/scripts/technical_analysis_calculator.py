"""
Technical Analysis Calculator
Calculates technical indicators for stock data from CSV files.
"""

import pandas as pd
import numpy as np
import ta
import argparse
import sys
import os
import json
from pathlib import Path

class TechnicalAnalysisCalculator:
    """
    Technical Analysis Calculator.
    Assumes input DataFrame has columns: 'Open', 'High', 'Low', 'Close', 'Volume'.
    """

    @staticmethod
    def calculate_technical_indicators(df):
        """
        Calculate comprehensive technical indicators.
        Returns the DataFrame with added indicator columns.
        """
        if df is None or df.empty:
            return df
            
        try:
            # Create a copy to avoid SettingWithCopy warnings
            df = df.copy()
            
            # --- 1. Moving Averages (MA) ---
            df['MA5'] = ta.trend.sma_indicator(df['Close'], window=5)
            df['MA10'] = ta.trend.sma_indicator(df['Close'], window=10)
            df['MA20'] = ta.trend.sma_indicator(df['Close'], window=20)
            df['MA30'] = ta.trend.sma_indicator(df['Close'], window=30)
            df['MA60'] = ta.trend.sma_indicator(df['Close'], window=60)
            df['MA120'] = ta.trend.sma_indicator(df['Close'], window=120)
            df['MA250'] = ta.trend.sma_indicator(df['Close'], window=250)

            # --- 2. MACD (Moving Average Convergence Divergence) ---
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_hist'] = macd.macd_diff()

            # --- 3. KDJ (Stochastic Oscillator) ---
            # TA-Lib's stoch function returns K and D. J = 3K - 2D
            stoch = ta.momentum.StochasticOscillator(
                high=df['High'], low=df['Low'], close=df['Close'], window=9, smooth_window=3
            )
            df['K'] = stoch.stoch()
            df['D'] = stoch.stoch_signal()
            df['J'] = 3 * df['K'] - 2 * df['D']

            # --- 4. RSI (Relative Strength Index) ---
            df['RSI6'] = ta.momentum.rsi(df['Close'], window=6)
            df['RSI12'] = ta.momentum.rsi(df['Close'], window=12)
            df['RSI24'] = ta.momentum.rsi(df['Close'], window=24)

            # --- 5. Bollinger Bands ---
            bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
            df['BB_upper'] = bollinger.bollinger_hband()
            df['BB_middle'] = bollinger.bollinger_mavg()
            df['BB_lower'] = bollinger.bollinger_lband()
            
            # Band Width & %B
            df['BB_width'] = convert_to_float(bollinger.bollinger_wband())
            df['BB_pct_b'] = convert_to_float(bollinger.bollinger_pband())

            # --- 6. Volume MA & Ratio ---
            df['Vol_MA5'] = ta.trend.sma_indicator(df['Volume'], window=5)
            df['Vol_MA10'] = ta.trend.sma_indicator(df['Volume'], window=10)
            # Volume Ratio (Vol / Vol_MA5)
            df['Vol_Ratio'] = df['Volume'] / df['Vol_MA5'].replace(0, np.nan)

            # --- 7. WR (Williams %R) ---
            df['WR10'] = ta.momentum.williams_r(df['High'], df['Low'], df['Close'], lbp=10)
            df['WR6'] = ta.momentum.williams_r(df['High'], df['Low'], df['Close'], lbp=6)

            # --- 8. CCI (Commodity Channel Index) ---
            df['CCI'] = ta.trend.cci(df['High'], df['Low'], df['Close'], window=14)

            # --- 9. BIAS (Bias Ratio) ---
            # Bias = (Close - MA) / MA * 100
            ma6 = ta.trend.sma_indicator(df['Close'], window=6)
            ma12 = ta.trend.sma_indicator(df['Close'], window=12)
            ma24 = ta.trend.sma_indicator(df['Close'], window=24)
            df['BIAS6'] = (df['Close'] - ma6) / ma6 * 100
            df['BIAS12'] = (df['Close'] - ma12) / ma12 * 100
            df['BIAS24'] = (df['Close'] - ma24) / ma24 * 100

            return df
            
        except Exception as e:
            # print(f"Indicator calc failed: {e}")
            return {"error": f"Calculation failed: {str(e)}"}

    @staticmethod
    def get_latest_indicators(df):
        """
        Get the latest indicator values as a dictionary.
        """
        if df is None or (isinstance(df, dict) and "error" in df) or df.empty:
            return {}
            
        try:
            latest = df.iloc[-1]
            return {
                "date": str(latest.name) if isinstance(latest.name, (str, pd.Timestamp)) else str(latest.get('Date', 'N/A')),
                "price": convert_to_float(latest['Close']),
                "change_pct": convert_to_float(df['Close'].pct_change().iloc[-1] * 100),
                
                # Trend
                "ma5": convert_to_float(latest['MA5']),
                "ma10": convert_to_float(latest['MA10']),
                "ma20": convert_to_float(latest['MA20']),
                "ma30": convert_to_float(latest['MA30']),
                "ma60": convert_to_float(latest['MA60']),
                
                # MACD
                "macd": convert_to_float(latest['MACD']),
                "macd_signal": convert_to_float(latest['MACD_signal']),
                "macd_hist": convert_to_float(latest['MACD_hist']),
                
                # KDJ
                "k": convert_to_float(latest['K']),
                "d": convert_to_float(latest['D']),
                "j": convert_to_float(latest['J']),
                
                # RSI
                "rsi6": convert_to_float(latest['RSI6']),
                "rsi12": convert_to_float(latest['RSI12']),
                "rsi24": convert_to_float(latest['RSI24']),
                
                # Bollinger
                "bb_upper": convert_to_float(latest['BB_upper']),
                "bb_middle": convert_to_float(latest['BB_middle']),
                "bb_lower": convert_to_float(latest['BB_lower']),
                "bb_width": convert_to_float(latest.get('BB_width')),
                
                # Volume
                "vol_ratio": convert_to_float(latest['Vol_Ratio']),
                
                # Others
                "wr10": convert_to_float(latest['WR10']),
                "cci": convert_to_float(latest['CCI']),
                "bias6": convert_to_float(latest['BIAS6'])
            }
        except Exception as e:
            return {"error": f"Extract latest failed: {str(e)}"}

def convert_to_float(val):
    """Safe float conversion."""
    try:
        if pd.isna(val) or val is None:
            return None
        return float(val)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Calculate technical indicators for stock data.")
    parser.add_argument("--data-dir", type=str, default="kline_data", help="Directory containing stock CSVs")
    parser.add_argument("--symbol", type=str, required=True, help="Stock symbol to analyze (e.g., 000001)")
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    # Create data directory if it doesn't exist
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(json.dumps({"error": f"Could not create data directory '{data_dir}': {e}"}, indent=2, ensure_ascii=False))
            sys.exit(1)
        
    symbol = args.symbol
    # Try multiple common filename patterns
    possible_files = [
        data_dir / f"{symbol}.csv",
        data_dir / f"SH{symbol}.csv",
        data_dir / f"SZ{symbol}.csv",
        data_dir / f"bj{symbol}.csv",
    ]
    
    csv_file = None
    for f in possible_files:
        if f.exists():
            csv_file = f
            break
            
    df = None
    
    # If file exists, load it
    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            df.columns = [c.capitalize() for c in df.columns]
            if 'Date' in df.columns:
                 df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d', errors='coerce')
                 df.set_index('Date', inplace=True)
        except Exception as e:
            print(json.dumps({"error": f"Error reading local file: {e}"}, indent=2, ensure_ascii=False))
            sys.exit(1)
    else:
        print(json.dumps({"error": f"Local data file for '{symbol}' not found in '{data_dir}'"}, indent=2, ensure_ascii=False))
        sys.exit(1)
            
    # If load failed
    if df is None or df.empty:
        print(json.dumps({"error": f"Data is empty or invalid for '{symbol}'"}, indent=2, ensure_ascii=False))
        sys.exit(1)

    try:
        # Calculate logic
        df_tech = TechnicalAnalysisCalculator.calculate_technical_indicators(df)
        latest = TechnicalAnalysisCalculator.get_latest_indicators(df_tech)
        
        if "error" not in latest:
            # Output result as JSON object (not array) for single stock
            print(json.dumps(latest, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": latest['error']}, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(json.dumps({"error": f"Failed to process: {e}"}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
