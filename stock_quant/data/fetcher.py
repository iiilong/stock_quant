import akshare as ak
import pandas as pd
from datetime import datetime
import time
import os


class DataFetcher:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_stock_data(self, code: str, start_date: str, end_date: str,
                       adjust: str = "qfq") -> pd.DataFrame:
        cache_file = os.path.join(self.cache_dir, f"{code}_{start_date}_{end_date}.pkl")
        if os.path.exists(cache_file):
            return pd.read_pickle(cache_file)

        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "振幅": "amplitude",
                "涨跌幅": "pct_change", "涨跌额": "change",
                "换手率": "turnover"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df.to_pickle(cache_file)
            return df
        except Exception as e:
            print(f"获取{code}数据失败: {e}")
            return pd.DataFrame()

    def get_index_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        cache_file = os.path.join(self.cache_dir, f"idx_{code}_{start_date}_{end_date}.pkl")
        if os.path.exists(cache_file):
            return pd.read_pickle(cache_file)

        try:
            df = ak.stock_zh_index_daily(symbol=code)
            if df.empty:
                return pd.DataFrame()
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df = df.loc[start_date:end_date]
            df.to_pickle(cache_file)
            return df
        except Exception as e:
            print(f"获取指数{code}数据失败: {e}")
            return pd.DataFrame()

    def batch_get_stock_data(self, codes: list, start_date: str,
                             end_date: str, sleep: float = 0.5) -> dict:
        result = {}
        for i, code in enumerate(codes):
            df = self.get_stock_data(code, start_date, end_date)
            if not df.empty:
                result[code] = df
            if i < len(codes) - 1:
                time.sleep(sleep)
        return result
