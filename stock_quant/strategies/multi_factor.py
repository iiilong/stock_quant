import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class MultiFactorStrategy:
    """
    多因子选股策略
    
    因子组合：
    1. 估值因子：PE、PB
    2. 质量因子：ROE、毛利率
    3. 成长因子：营收增长率、净利润增长率
    4. 动量因子：20日动量、60日动量
    5. 资金流因子：主力净流入
    6. 波动因子：低波动
    
    选股逻辑：每月调仓，选综合得分最高的股票
    """
    
    def __init__(self, top_n=10, rebalance_days=20):
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.name = "MultiFactor"

    def get_fundamental_data(self, codes: list) -> pd.DataFrame:
        """获取基本面数据"""
        all_data = []
        
        for code in codes:
            try:
                df = ak.stock_individual_info_em(symbol=code)
                info = {}
                for _, row in df.iterrows():
                    info[row.iloc[0]] = row.iloc[1]
                
                info["code"] = code
                all_data.append(info)
            except Exception:
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.DataFrame(all_data)
        
        numeric_cols = ["总市值", "流通市值", "市盈率(动态)", "市净率", "60日涨跌幅"]
        for col in numeric_cols:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce")
        
        return result

    def get_price_data(self, codes: list, days: int = 120) -> dict:
        """获取价格数据"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        result = {}
        for code in codes:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                if not df.empty:
                    df["日期"] = pd.to_datetime(df["日期"])
                    df = df.set_index("日期").sort_index()
                    result[code] = df
            except Exception:
                continue
        
        return result

    def calculate_factors(self, fundamental: pd.DataFrame, 
                          price_data: dict) -> pd.DataFrame:
        """计算因子得分"""
        factors = fundamental.copy()
        
        if "市盈率(动态)" in factors.columns:
            pe = factors["市盈率(动态)"]
            factors["pe_score"] = self._normalize_score(pe, reverse=True)
        else:
            factors["pe_score"] = 0
        
        if "市净率" in factors.columns:
            pb = factors["市净率"]
            factors["pb_score"] = self._normalize_score(pb, reverse=True)
        else:
            factors["pb_score"] = 0
        
        if "60日涨跌幅" in factors.columns:
            momentum = factors["60日涨跌幅"]
            factors["momentum_score"] = self._normalize_score(momentum)
        else:
            factors["momentum_score"] = 0
        
        vol_scores = []
        for code in factors["code"]:
            if code in price_data:
                df = price_data[code]
                if len(df) >= 20:
                    returns = df["收盘"].pct_change().dropna()
                    vol = returns.std() * np.sqrt(252)
                    vol_scores.append(vol)
                else:
                    vol_scores.append(np.nan)
            else:
                vol_scores.append(np.nan)
        
        factors["volatility"] = vol_scores
        factors["low_vol_score"] = self._normalize_score(
            factors["volatility"], reverse=True
        )
        
        mom20_scores = []
        mom60_scores = []
        for code in factors["code"]:
            if code in price_data:
                df = price_data[code]
                close = df["收盘"]
                if len(close) >= 20:
                    mom20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100
                    mom20_scores.append(mom20)
                else:
                    mom20_scores.append(np.nan)
                
                if len(close) >= 60:
                    mom60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100
                    mom60_scores.append(mom60)
                else:
                    mom60_scores.append(np.nan)
            else:
                mom20_scores.append(np.nan)
                mom60_scores.append(np.nan)
        
        factors["mom20"] = mom20_scores
        factors["mom60"] = mom60_scores
        factors["momentum_20_score"] = self._normalize_score(factors["mom20"])
        factors["momentum_60_score"] = self._normalize_score(factors["mom60"])
        
        factors["value_score"] = factors["pe_score"] * 0.5 + factors["pb_score"] * 0.5
        factors["momentum_total"] = (
            factors["momentum_score"] * 0.3 +
            factors["momentum_20_score"] * 0.35 +
            factors["momentum_60_score"] * 0.35
        )
        
        factors["total_score"] = (
            factors["value_score"] * 0.25 +
            factors["momentum_total"] * 0.35 +
            factors["low_vol_score"] * 0.20 +
            factors["momentum_20_score"] * 0.20
        )
        
        return factors

    def _normalize_score(self, series: pd.Series, reverse: bool = False) -> pd.Series:
        """归一化因子得分到0-1"""
        if series.isna().all():
            return pd.Series(0.5, index=series.index)
        
        rank = series.rank(pct=True)
        if reverse:
            rank = 1 - rank
        return rank

    def select_stocks(self, factors: pd.DataFrame) -> list:
        """选股"""
        valid = factors.dropna(subset=["total_score"])
        
        if valid.empty:
            return []
        
        selected = valid.nlargest(self.top_n, "total_score")
        
        print(f"\nSelected {len(selected)} stocks:")
        for _, row in selected.iterrows():
            print(f"  {row['code']}: score={row['total_score']:.4f}, "
                  f"PE={row.get('市盈率(动态)', 'N/A')}, "
                  f"mom60={row.get('mom60', 0):.1f}%")
        
        return selected["code"].tolist()


class MultiFactorBacktestEngine:
    """多因子回测引擎"""
    
    def __init__(self, initial_capital=100000, commission_rate=0.0003,
                 stamp_tax_rate=0.001, slippage=0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage = slippage

    def run(self, stock_pool: list, strategy) -> dict:
        """回测"""
        print("\nFetching fundamental data...")
        fundamental = strategy.get_fundamental_data(stock_pool)
        
        if fundamental.empty:
            print("ERROR: No fundamental data")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        print(f"Got data for {len(fundamental)} stocks")
        
        print("\nFetching price data...")
        price_data = strategy.get_price_data(stock_pool, days=120)
        print(f"Got price data for {len(price_data)} stocks")
        
        print("\nCalculating factors...")
        factors = strategy.calculate_factors(fundamental, price_data)
        
        selected_stocks = strategy.select_stocks(factors)
        
        if not selected_stocks:
            print("ERROR: No stocks selected")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        print(f"\nBacktesting {len(selected_stocks)} stocks...")
        
        capital = self.initial_capital
        holdings = {}
        trades = []
        equity_curve = []
        
        for code in selected_stocks:
            if code not in price_data:
                continue
            
            df = price_data[code]
            if len(df) < 2:
                continue
            
            current_price = df["收盘"].iloc[-1]
            prev_price = df["收盘"].iloc[-2]
            
            position_value = 0
            if code in holdings:
                shares, buy_price = holdings[code]
                position_value = shares * current_price
            
            daily_return = (current_price - prev_price) / prev_price
            
            total_value = capital + sum(
                shares * df["收盘"].iloc[-1] 
                for code_inner, (shares, _) in holdings.items()
                if code_inner in price_data and code_inner != code
            )
            total_value += position_value
            
            equity_curve.append({
                "date": df.index[-1],
                "equity": total_value
            })
        
        if not equity_curve:
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        equity_df = pd.DataFrame(equity_curve).set_index("date")
        
        avg_equity = equity_df["equity"].mean()
        total_return = (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0] - 1) * 100
        
        print(f"\n--- Backtest Summary ---")
        print(f"  Total Return: {total_return:.2f}%")
        print(f"  Average Equity: {avg_equity:,.0f}")
        
        for code in selected_stocks:
            if code in price_data:
                df = price_data[code]
                stock_return = (df["收盘"].iloc[-1] / df["收盘"].iloc[0] - 1) * 100
                print(f"  {code}: {stock_return:.2f}%")
        
        return {
            "equity_curve": equity_df["equity"],
            "trades": trades,
            "selected_stocks": selected_stocks,
            "factors": factors,
        }


def calculate_simple_metrics(equity_curve: pd.Series) -> dict:
    """计算简单指标"""
    if equity_curve.empty or len(equity_curve) < 2:
        return None
    
    total_ret = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / len(equity_curve)) - 1
    
    returns = equity_curve.pct_change().dropna()
    ann_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    peak = equity_curve.cummax()
    max_dd = ((equity_curve - peak) / peak).min()
    
    return {
        "total_return": f"{total_ret:.2%}",
        "ann_return": f"{ann_ret:.2%}",
        "ann_volatility": f"{ann_vol:.2%}",
        "sharpe": f"{sharpe:.3f}",
        "max_dd": f"{max_dd:.2%}",
    }
