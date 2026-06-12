import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')


class MultiFactorStrategy:
    """
    多因子选股策略 - 纯价格数据版本
    
    因子组合：
    1. 动量因子：20日、60日、120日动量
    2. 反转因子：5日反转
    3. 波动率因子：低波动
    4. 成交量因子：量价配合
    5. 趋势因子：均线多头排列
    
    选股逻辑：每月调仓，选综合得分最高的股票
    """
    
    def __init__(self, top_n=10, rebalance_days=20):
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.name = "MultiFactor"

    def get_price_data(self, codes: list, days: int = 180) -> dict:
        """获取价格数据"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
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
                if not df.empty and len(df) >= 60:
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                    df = df.set_index(df.columns[0]).sort_index()
                    result[code] = df
                if (i + 1) % 20 == 0:
                    print(f"  Fetched {i+1}/{len(codes)} stocks...")
                time.sleep(0.2)
            except Exception:
                continue
        
        return result

    def calculate_factors(self, price_data: dict) -> pd.DataFrame:
        """计算因子"""
        records = []
        
        for code, df in price_data.items():
            try:
                close = df.iloc[:, 2].astype(float)
                high = df.iloc[:, 3].astype(float)
                low = df.iloc[:, 4].astype(float)
                volume = df.iloc[:, 5].astype(float)
                
                n = len(close)
                if n < 30:
                    continue
                
                min_need = min(n, 120)
                close = close.iloc[-min_need:]
                high = high.iloc[-min_need:]
                low = low.iloc[-min_need:]
                volume = volume.iloc[-min_need:]
                
                mom_5 = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if n >= 5 else 0
                mom_20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if n >= 20 else 0
                mom_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100 if n >= 60 else 0
                mom_120 = (close.iloc[-1] / close.iloc[-120] - 1) * 100 if n >= 120 else mom_60
                
                reversal_5 = -mom_5
                
                returns = close.pct_change().dropna()
                vol_20 = returns.iloc[-min(20, len(returns)):].std() * np.sqrt(252)
                vol_60 = returns.iloc[-min(60, len(returns)):].std() * np.sqrt(252)
                
                vol_20_val = float(vol_20) if not np.isnan(vol_20) else 0.5
                vol_60_val = float(vol_60) if not np.isnan(vol_60) else 0.5
                
                vol_ma20 = volume.iloc[-20:].mean()
                vol_ma5 = volume.iloc[-5:].mean()
                vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0
                
                ma5 = close.rolling(5).mean()
                ma10 = close.rolling(10).mean()
                ma20 = close.rolling(20).mean()
                ma60 = close.rolling(min(60, n)).mean()
                
                trend_score = 0
                if not np.isnan(ma5.iloc[-1]) and not np.isnan(ma10.iloc[-1]) and ma5.iloc[-1] > ma10.iloc[-1]:
                    trend_score += 1
                if not np.isnan(ma10.iloc[-1]) and not np.isnan(ma20.iloc[-1]) and ma10.iloc[-1] > ma20.iloc[-1]:
                    trend_score += 1
                if not np.isnan(ma20.iloc[-1]) and not np.isnan(ma60.iloc[-1]) and ma20.iloc[-1] > ma60.iloc[-1]:
                    trend_score += 1
                if close.iloc[-1] > ma5.iloc[-1] if not np.isnan(ma5.iloc[-1]) else False:
                    trend_score += 1
                
                records.append({
                    "code": code,
                    "mom_5": float(mom_5),
                    "mom_20": float(mom_20),
                    "mom_60": float(mom_60),
                    "mom_120": float(mom_120),
                    "reversal_5": float(reversal_5),
                    "vol_20": vol_20_val,
                    "vol_60": vol_60_val,
                    "vol_ratio": float(vol_ratio),
                    "trend_score": trend_score,
                    "price": float(close.iloc[-1]),
                })
            except Exception as e:
                continue
                
                mom_5 = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                mom_20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100
                mom_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100
                mom_120 = (close.iloc[-1] / close.iloc[-120] - 1) * 100
                
                reversal_5 = -mom_5
                
                returns = close.pct_change().dropna()
                vol_20 = returns.iloc[-20:].std() * np.sqrt(252)
                vol_60 = returns.iloc[-60:].std() * np.sqrt(252)
                
                vol_ratio = volume.iloc[-5:].mean() / volume.iloc[-20:].mean()
                
                ma5 = close.rolling(5).mean()
                ma10 = close.rolling(10).mean()
                ma20 = close.rolling(20).mean()
                ma60 = close.rolling(60).mean()
                
                trend_score = 0
                if ma5.iloc[-1] > ma10.iloc[-1]:
                    trend_score += 1
                if ma10.iloc[-1] > ma20.iloc[-1]:
                    trend_score += 1
                if ma20.iloc[-1] > ma60.iloc[-1]:
                    trend_score += 1
                if close.iloc[-1] > ma5.iloc[-1]:
                    trend_score += 1
                
                atr = (high - low).rolling(14).mean()
                atr_pct = atr.iloc[-1] / close.iloc[-1] * 100
                
                records.append({
                    "code": code,
                    "mom_5": mom_5,
                    "mom_20": mom_20,
                    "mom_60": mom_60,
                    "mom_120": mom_120,
                    "reversal_5": reversal_5,
                    "vol_20": vol_20,
                    "vol_60": vol_60,
                    "vol_ratio": vol_ratio,
                    "trend_score": trend_score,
                    "atr_pct": atr_pct,
                    "price": close.iloc[-1],
                })
            except Exception as e:
                continue
        
        if not records:
            return pd.DataFrame()
        
        factors = pd.DataFrame(records)
        factors = self._normalize_factors(factors)
        factors["total_score"] = (
            factors["momentum_score"] * 0.30 +
            factors["reversal_score"] * 0.15 +
            factors["low_vol_score"] * 0.20 +
            factors["volume_score"] * 0.15 +
            factors["trend_score_norm"] * 0.20
        )
        
        return factors

    def _normalize_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """归一化因子"""
        df = df.copy()
        
        df["momentum_score"] = (
            self._rank_normalize(df["mom_20"]) * 0.4 +
            self._rank_normalize(df["mom_60"]) * 0.4 +
            self._rank_normalize(df["mom_120"]) * 0.2
        )
        
        df["reversal_score"] = self._rank_normalize(df["reversal_5"])
        
        df["low_vol_score"] = 1 - self._rank_normalize(df["vol_20"])
        
        df["volume_score"] = self._rank_normalize(df["vol_ratio"])
        
        df["trend_score_norm"] = df["trend_score"] / 4.0
        
        return df

    def _rank_normalize(self, series: pd.Series) -> pd.Series:
        """排名归一化"""
        return series.rank(pct=True)

    def select_stocks(self, factors: pd.DataFrame) -> list:
        """选股"""
        valid = factors.dropna(subset=["total_score"])
        
        if valid.empty:
            return []
        
        selected = valid.nlargest(self.top_n, "total_score")
        
        print(f"\nSelected {len(selected)} stocks:")
        for _, row in selected.iterrows():
            print(f"  {row['code']}: score={row['total_score']:.4f}, "
                  f"mom20={row['mom_20']:.1f}%, "
                  f"vol={row['vol_20']:.1%}")
        
        return selected["code"].tolist()


class MultiFactorBacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000, commission_rate=0.0003,
                 stamp_tax_rate=0.001, slippage=0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage = slippage

    def run(self, stock_pool: list, strategy) -> dict:
        """回测"""
        print("\nFetching price data...")
        price_data = strategy.get_price_data(stock_pool, days=180)
        print(f"Got data for {len(price_data)} stocks")
        
        if not price_data:
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        print("\nCalculating factors...")
        factors = strategy.calculate_factors(price_data)
        
        if factors.empty:
            print("ERROR: No valid factors")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        selected_stocks = strategy.select_stocks(factors)
        
        if not selected_stocks:
            print("ERROR: No stocks selected")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        print(f"\nBacktesting {len(selected_stocks)} stocks...")
        
        capital = self.initial_capital
        equal_weight = capital / len(selected_stocks)
        
        trades = []
        equity_curve = []
        holdings = {}
        
        for code in selected_stocks:
            if code not in price_data:
                continue
            df = price_data[code]
            price = df.iloc[:, 2].iloc[-1]
            shares = int(equal_weight / price / 100) * 100
            if shares >= 100:
                cost = shares * price * (1 + self.slippage)
                commission = cost * self.commission_rate
                capital -= (cost + commission)
                holdings[code] = (shares, price)
                trades.append({
                    "code": code,
                    "buy_price": price,
                    "shares": shares,
                })
        
        portfolio_value = capital
        for code, (shares, buy_price) in holdings.items():
            if code in price_data:
                current_price = price_data[code].iloc[:, 2].iloc[-1]
                portfolio_value += shares * current_price
        
        equity_curve.append({
            "date": datetime.now(),
            "equity": portfolio_value
        })
        
        total_return = (portfolio_value / self.initial_capital - 1) * 100
        
        print(f"\n--- Portfolio Summary ---")
        print(f"  Initial Capital: {self.initial_capital:,.0f}")
        print(f"  Current Value: {portfolio_value:,.0f}")
        print(f"  Total Return: {total_return:.2f}%")
        print(f"  Cash: {capital:,.0f}")
        print(f"\n  Holdings:")
        for code, (shares, buy_price) in holdings.items():
            if code in price_data:
                current_price = price_data[code].iloc[:, 2].iloc[-1]
                pnl = (current_price - buy_price) / buy_price * 100
                print(f"    {code}: {shares} shares @ {buy_price:.2f} -> {current_price:.2f} ({pnl:+.2f}%)")
        
        equity_df = pd.DataFrame(equity_curve).set_index("date")
        
        return {
            "equity_curve": equity_df["equity"],
            "trades": trades,
            "selected_stocks": selected_stocks,
            "factors": factors,
            "holdings": holdings,
            "portfolio_value": portfolio_value,
        }


def calculate_metrics(equity_curve: pd.Series, initial_capital: float = 100000) -> dict:
    """计算指标"""
    if equity_curve.empty:
        return None
    
    total_ret = (equity_curve.iloc[-1] / initial_capital - 1)
    
    return {
        "total_return": f"{total_ret:.2%}",
        "portfolio_value": f"{equity_curve.iloc[-1]:,.0f}",
        "initial_capital": f"{initial_capital:,.0f}",
    }
