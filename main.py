import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

class InstitutionalIPDAEngine:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.assets = {
            "Gold": "GC=F",
            "Silver": "SI=F",
            "Crude_Oil": "CL=F",
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "JPY=X",
            "AUDUSD": "AUDUSD=X",
            "USDCAD": "CAD=X",
            "DXY": "DX-Y.NYB"
        }

    def fetch_market_candles(self, symbol: str, interval: str = "5m", range_data: str = "1d") -> Optional[pd.DataFrame]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_data}"
        try:
            res = requests.get(url, headers=self.headers, timeout=10).json()
            result = res['chart']['result'][0]
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]
            
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps, unit='s'),
                'open': quote['open'],
                'high': quote['high'],
                'low': quote['low'],
                'close': quote['close'],
                'volume': quote['volume']
            }).dropna().reset_index(drop=True)
            return df
        except Exception:
            return None

    def detect_fvg(self, df: pd.DataFrame, min_gap_pct: float = 0.015) -> List[Dict]:
        fvgs = []
        for i in range(2, len(df)):
            c1_high, c1_low = df.loc[i-2, 'high'], df.loc[i-2, 'low']
            c2_open, c2_close = df.loc[i-1, 'open'], df.loc[i-1, 'close']
            c3_high, c3_low = df.loc[i, 'high'], df.loc[i, 'low']
            
            body = abs(c2_close - c2_open)
            avg_body = df['close'].diff().abs().rolling(10).mean().iloc[i-1]
            if np.isnan(avg_body):
                continue
            is_displacement = body > (avg_body * 1.3)
            
            if c3_low > c1_high and is_displacement:
                gap = c3_low - c1_high
                if (gap / c1_high) * 100 >= min_gap_pct:
                    fvgs.append({'type': 'BULLISH_FVG', 'top': c3_low, 'bottom': c1_high, 'ce': c1_high + (gap/2)})
            elif c3_high < c1_low and is_displacement:
                gap = c1_low - c3_high
                if (gap / c1_low) * 100 >= min_gap_pct:
                    fvgs.append({'type': 'BEARISH_FVG', 'top': c1_low, 'bottom': c3_high, 'ce': c3_high + (gap/2)})
        return fvgs

    def execute_all(self):
        print("==================================================")
        print("[ INSTITUTIONAL IPDA MASTERMIND ENGINE v2.0 ]")
        print(f"UTC Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("==================================================\n")

        data_store = {}
        print("[1] FETCHING MARKET DATA & FVG SCANNER:")
        for name, symbol in self.assets.items():
            df = self.fetch_market_candles(symbol)
            if df is not None and not df.empty:
                data_store[name] = df['close'].tolist()
                latest = df['close'].iloc[-1]
                fvgs = self.detect_fvg(df)
                
                print(f"    * {name:<10} : ${latest:.4f} | Valid FVGs: {len(fvgs)}")
                if fvgs:
                    lf = fvgs[-1]
                    print(f"      └─ Latest: {lf['type']} | Range: [{lf['bottom']:.4f} - {lf['top']:.4f}] | CE 50%: {lf['ce']:.4f}")
            else:
                print(f"    * {name:<10} : FETCH_ERROR")

        if data_store:
            min_l = min([len(v) for v in data_store.values()])
            df_corr = pd.DataFrame({k: v[-min_l:] for k, v in data_store.items()}).corr()
            
            print("\n[2] LIVE CORRELATION MATRIX & SMT DIVERGENCE:")
            if 'Gold' in df_corr and 'Silver' in df_corr:
                print(f"    * Gold vs Silver Correlation : {df_corr.loc['Gold', 'Silver']:.2f}")
            if 'EURUSD' in df_corr and 'GBPUSD' in df_corr:
                print(f"    * EURUSD vs GBPUSD Correlation : {df_corr.loc['EURUSD', 'GBPUSD']:.2f}")

if __name__ == '__main__':
    engine = InstitutionalIPDAEngine()
    engine.execute_all()
