import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')


class MonthlyRebalanceBacktest:
    """
    月度调仓回测引擎
    
    特点：
    1. 每月固定日期调仓
    2. 等权重配置
    3. 计算完整的净值曲线
    4. 无未来函数
    """
    
    def __init__(self, initial_capital=100000, top_n=10,
                 commission_rate=0.0003, stamp_tax_rate=0.001,
                 slippage=0.001):
        self.initial_capital = initial_capital
        self.top_n = top_n
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage = slippage

    def get_stock_data(self, codes: list, start_date: str, end_date: str) -> dict:
        """获取股票数据"""
        result = {}
        for i, code in enumerate(codes):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                if not df.empty and len(df) >= 20:
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                    df = df.set_index(df.columns[0]).sort_index()
                    result[code] = df
                if (i + 1) % 20 == 0:
                    print(f"  Fetched {i+1}/{len(codes)} stocks...")
                time.sleep(0.15)
            except Exception:
                continue
        return result

    def get_realtime_data(self, codes: list) -> dict:
        """获取实时数据（PE、资金流等）"""
        result = {"pe": {}, "money_flow": {}}
        
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                for code in codes:
                    try:
                        stock_data = df[df.iloc[:, 1] == code]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            for col_idx in range(len(row)):
                                col_name = str(row.index[col_idx])
                                val = row.iloc[col_idx]
                                if 'PE' in col_name.upper() or '市盈率' in col_name:
                                    try:
                                        result["pe"][code] = float(val)
                                    except:
                                        pass
                    except Exception:
                        continue
        except Exception:
            pass
        
        try:
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                for code in codes:
                    try:
                        stock_data = df[df.iloc[:, 1] == code]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            for col_idx in range(len(row)):
                                col_name = str(row.index[col_idx])
                                val = row.iloc[col_idx]
                                if '主力净流入' in col_name and '占比' in col_name:
                                    try:
                                        result["money_flow"][code] = float(val)
                                    except:
                                        pass
                    except Exception:
                        continue
        except Exception:
            pass
        
        return result

    def calculate_factors_at_date(self, price_data: dict, 
                                   realtime: dict,
                                   as_of_date: pd.Timestamp) -> pd.DataFrame:
        """计算某日的因子（无未来函数）"""
        records = []
        
        for code, df in price_data.items():
            try:
                available = df.loc[:as_of_date]
                if len(available) < 30:
                    continue
                
                close = available.iloc[:, 2].astype(float)
                high = available.iloc[:, 3].astype(float)
                low = available.iloc[:, 4].astype(float)
                volume = available.iloc[:, 5].astype(float)
                
                n = len(close)
                
                mom_20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if n >= 20 else 0
                mom_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100 if n >= 60 else mom_20
                
                reversal_5 = -(close.iloc[-1] / close.iloc[-5] - 1) * 100 if n >= 5 else 0
                
                returns = close.pct_change().dropna()
                vol_20 = returns.iloc[-min(20, len(returns)):].std() * np.sqrt(252)
                vol_20_val = float(vol_20) if not np.isnan(vol_20) else 0.5
                
                vol_ma20 = volume.iloc[-20:].mean() if n >= 20 else volume.mean()
                vol_ma5 = volume.iloc[-5:].mean()
                vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0
                
                ma5 = close.rolling(5).mean()
                ma10 = close.rolling(10).mean()
                ma20 = close.rolling(20).mean()
                
                trend_score = 0
                if not np.isnan(ma5.iloc[-1]) and not np.isnan(ma10.iloc[-1]) and ma5.iloc[-1] > ma10.iloc[-1]:
                    trend_score += 1
                if not np.isnan(ma10.iloc[-1]) and not np.isnan(ma20.iloc[-1]) and ma10.iloc[-1] > ma20.iloc[-1]:
                    trend_score += 1
                if close.iloc[-1] > ma5.iloc[-1] if not np.isnan(ma5.iloc[-1]) else False:
                    trend_score += 1
                
                pe = realtime.get("pe", {}).get(code, None) if isinstance(realtime.get("pe"), dict) else None
                money_flow = realtime.get("money_flow", {}).get(code, 0) if isinstance(realtime.get("money_flow"), dict) else 0
                
                records.append({
                    "code": code,
                    "mom_20": mom_20,
                    "mom_60": mom_60,
                    "reversal_5": reversal_5,
                    "vol_20": vol_20_val,
                    "vol_ratio": vol_ratio,
                    "trend_score": trend_score,
                    "pe": pe,
                    "money_flow": money_flow,
                    "price": float(close.iloc[-1]),
                })
            except Exception:
                continue
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        df["mom_score"] = self._rank_normalize(df["mom_20"]) * 0.5 + self._rank_normalize(df["mom_60"]) * 0.5
        df["reversal_score"] = self._rank_normalize(df["reversal_5"])
        df["low_vol_score"] = 1 - self._rank_normalize(df["vol_20"])
        df["volume_score"] = self._rank_normalize(df["vol_ratio"])
        df["trend_norm"] = df["trend_score"] / 3.0
        
        pe_valid = df["pe"].apply(lambda x: x if x is not None and x > 0 else np.nan)
        df["value_score"] = 1 - self._rank_normalize(pe_valid)
        
        df["flow_score"] = self._rank_normalize(df["money_flow"])
        
        df["total_score"] = (
            df["value_score"].fillna(0.5) * 0.15 +
            df["mom_score"] * 0.25 +
            df["reversal_score"] * 0.10 +
            df["low_vol_score"] * 0.15 +
            df["volume_score"] * 0.10 +
            df["trend_norm"] * 0.15 +
            df["flow_score"] * 0.10
        )
        
        return df

    def _rank_normalize(self, series: pd.Series) -> pd.Series:
        return series.rank(pct=True)

    def select_stocks(self, factors: pd.DataFrame) -> list:
        valid = factors.dropna(subset=["total_score"])
        if valid.empty:
            return []
        selected = valid.nlargest(self.top_n, "total_score")
        return selected["code"].tolist()

    def run_backtest(self, codes: list, start_date: str, end_date: str) -> dict:
        """运行回测"""
        print("\nFetching historical data...")
        price_data = self.get_stock_data(codes, start_date, end_date)
        print(f"Got data for {len(price_data)} stocks")
        
        if not price_data:
            return {"equity_curve": pd.Series(dtype=float), "trades": [], "rebalances": []}
        
        print("\nFetching realtime data...")
        realtime = self.get_realtime_data(list(price_data.keys()))
        
        all_dates = sorted(set().union(*[set(df.index) for df in price_data.values()]))
        all_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]
        
        rebalance_dates = []
        current_month = None
        for date in all_dates:
            month = (date.year, date.month)
            if month != current_month:
                rebalance_dates.append(date)
                current_month = month
        
        print(f"\nRunning backtest with {len(rebalance_dates)} rebalance dates...")
        
        capital = self.initial_capital
        holdings = {}
        equity_curve = []
        trades = []
        rebalance_records = []
        
        for reb_idx, reb_date in enumerate(rebalance_dates):
            factors = self.calculate_factors_at_date(price_data, realtime, reb_date)
            
            if factors.empty:
                continue
            
            selected = self.select_stocks(factors)
            
            if not selected:
                continue
            
            for code, (shares, buy_price) in holdings.items():
                if code in price_data:
                    df = price_data[code]
                    if reb_date in df.index:
                        sell_price = float(df.loc[reb_date].iloc[2])
                        revenue = shares * sell_price * (1 - self.slippage)
                        commission = revenue * self.commission_rate
                        tax = revenue * self.stamp_tax_rate
                        capital += revenue - commission - tax
                        trades.append({
                            "date": reb_date,
                            "code": code,
                            "action": "SELL",
                            "price": sell_price,
                            "shares": shares,
                        })
            
            holdings = {}
            
            for code in selected:
                if code in price_data:
                    df = price_data[code]
                    if reb_date in df.index:
                        price = float(df.loc[reb_date].iloc[2])
                        equal_weight = capital / len(selected)
                        shares = int(equal_weight / price / 100) * 100
                        if shares >= 100:
                            cost = shares * price * (1 + self.slippage)
                            commission = cost * self.commission_rate
                            capital -= (cost + commission)
                            holdings[code] = (shares, price)
                            trades.append({
                                "date": reb_date,
                                "code": code,
                                "action": "BUY",
                                "price": price,
                                "shares": shares,
                            })
            
            rebalance_records.append({
                "date": reb_date,
                "stocks": selected,
                "holdings": len(holdings),
            })
            
            total_val = capital
            for code, (shares, _) in holdings.items():
                if code in price_data:
                    df = price_data[code]
                    if reb_date in df.index:
                        total_val += shares * float(df.loc[reb_date].iloc[2])
            equity_curve.append({"date": reb_date, "equity": total_val})
            
            if (reb_idx + 1) % 6 == 0:
                print(f"  Rebalance {reb_idx + 1}/{len(rebalance_dates)}: {reb_date.strftime('%Y-%m-%d')}, "
                      f"stocks={len(selected)}, equity={total_val:,.0f}")
        
        if holdings:
            last_date = all_dates[-1]
            total_val = capital
            for code, (shares, _) in holdings.items():
                if code in price_data:
                    df = price_data[code]
                    if last_date in df.index:
                        total_val += shares * float(df.loc[last_date].iloc[2])
            equity_curve.append({"date": last_date, "equity": total_val})
        
        equity_df = pd.DataFrame(equity_curve).set_index("date")
        equity_df = equity_df[~equity_df.index.duplicated(keep='last')]
        
        return {
            "equity_curve": equity_df["equity"],
            "trades": trades,
            "rebalances": rebalance_records,
            "final_holdings": holdings,
        }


def calculate_backtest_metrics(equity_curve: pd.Series, initial_capital: float) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return None
    
    total_ret = equity_curve.iloc[-1] / initial_capital - 1
    
    returns = equity_curve.pct_change().dropna()
    
    ann_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()
    
    total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    ann_ret = (1 + total_ret) ** (365 / total_days) - 1 if total_days > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    
    return {
        "total_return": f"{total_ret:.2%}",
        "ann_return": f"{ann_ret:.2%}",
        "ann_volatility": f"{ann_vol:.2%}",
        "sharpe": f"{sharpe:.3f}",
        "max_dd": f"{max_dd:.2%}",
        "calmar": f"{calmar:.3f}",
        "final_value": f"{equity_curve.iloc[-1]:,.0f}",
    }
