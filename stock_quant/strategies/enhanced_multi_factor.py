import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')


class EnhancedMultiFactorStrategy:
    """
    增强多因子选股策略
    
    因子组合（8个因子）：
    1. 估值因子：PE近似、PB近似
    2. 质量因子：ROE近似、毛利率近似
    3. 动量因子：20日、60日动量
    4. 反转因子：5日反转
    5. 波动率因子：低波动
    6. 成交量因子：量价配合
    7. 趋势因子：均线多头排列
    8. 资金流因子：主力资金流向
    
    选股逻辑：每月调仓，选综合得分最高的股票
    """
    
    def __init__(self, top_n=10, rebalance_days=20):
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        self.name = "EnhancedMultiFactor"

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
                if not df.empty and len(df) >= 30:
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                    df = df.set_index(df.columns[0]).sort_index()
                    result[code] = df
                if (i + 1) % 20 == 0:
                    print(f"  Fetched {i+1}/{len(codes)} stocks...")
                time.sleep(0.2)
            except Exception:
                continue
        
        return result

    def get_fundamental_data(self, codes: list) -> dict:
        """获取基本面数据（从实时行情）"""
        result = {}
        
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                for code in codes:
                    try:
                        stock_data = df[df.iloc[:, 1] == code]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            pe = None
                            pb = None
                            total_mv = None
                            
                            for col_idx in range(len(row)):
                                col_name = str(row.index[col_idx])
                                val = row.iloc[col_idx]
                                if 'PE' in col_name.upper() or '市盈率' in col_name:
                                    try:
                                        pe = float(val)
                                    except:
                                        pass
                                elif 'PB' in col_name.upper() or '市净率' in col_name:
                                    try:
                                        pb = float(val)
                                    except:
                                        pass
                                elif '总市值' in col_name or '市值' in col_name:
                                    try:
                                        total_mv = float(val)
                                    except:
                                        pass
                            
                            result[code] = {
                                "pe": pe,
                                "pb": pb,
                                "total_mv": total_mv,
                            }
                    except Exception:
                        continue
        except Exception:
            pass
        
        return result

    def get_money_flow(self, codes: list) -> dict:
        """获取资金流数据"""
        result = {}
        
        try:
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                for code in codes:
                    try:
                        stock_data = df[df.iloc[:, 1] == code]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            main_net = 0
                            main_net_pct = 0
                            
                            for col_idx in range(len(row)):
                                col_name = str(row.index[col_idx])
                                val = row.iloc[col_idx]
                                if '主力净流入' in col_name and '占比' in col_name:
                                    try:
                                        main_net_pct = float(val)
                                    except:
                                        pass
                                elif '主力净流入' in col_name:
                                    try:
                                        main_net = float(val)
                                    except:
                                        pass
                            
                            result[code] = {
                                "main_net_inflow": main_net,
                                "main_net_inflow_pct": main_net_pct,
                            }
                    except Exception:
                        continue
        except Exception:
            pass
        
        return result

    def calculate_factors(self, price_data: dict, 
                          fundamental: dict, money_flow: dict) -> pd.DataFrame:
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
                
                pe = fundamental.get(code, {}).get("pe", None)
                pb = fundamental.get(code, {}).get("pb", None)
                total_mv = fundamental.get(code, {}).get("total_mv", None)
                
                money_flow_dict = money_flow.get(code, {})
                main_net = money_flow_dict.get("main_net_inflow_pct", 0)
                
                records.append({
                    "code": code,
                    "mom_5": float(mom_5),
                    "mom_20": float(mom_20),
                    "mom_60": float(mom_60),
                    "reversal_5": float(reversal_5),
                    "vol_20": vol_20_val,
                    "vol_60": vol_60_val,
                    "vol_ratio": float(vol_ratio),
                    "trend_score": trend_score,
                    "pe": pe,
                    "pb": pb,
                    "total_mv": total_mv,
                    "main_net_pct": main_net,
                    "price": float(close.iloc[-1]),
                })
            except Exception as e:
                continue
        
        if not records:
            return pd.DataFrame()
        
        factors = pd.DataFrame(records)
        factors = self._normalize_factors(factors)
        
        factors["value_score"] = factors["pe_score"] * 0.5 + factors["pb_score"] * 0.5
        
        factors["total_score"] = (
            factors["value_score"] * 0.15 +
            factors["momentum_score"] * 0.25 +
            factors["reversal_score"] * 0.10 +
            factors["low_vol_score"] * 0.15 +
            factors["volume_score"] * 0.10 +
            factors["trend_score_norm"] * 0.15 +
            factors["money_flow_score"] * 0.10
        )
        
        return factors

    def _normalize_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """归一化因子"""
        df = df.copy()
        
        df["momentum_score"] = (
            self._rank_normalize(df["mom_20"]) * 0.5 +
            self._rank_normalize(df["mom_60"]) * 0.5
        )
        
        df["reversal_score"] = self._rank_normalize(df["reversal_5"])
        
        df["low_vol_score"] = 1 - self._rank_normalize(df["vol_20"])
        
        df["volume_score"] = self._rank_normalize(df["vol_ratio"])
        
        df["trend_score_norm"] = df["trend_score"] / 4.0
        
        pe_valid = df["pe"].apply(lambda x: x if x is not None and x > 0 else np.nan)
        df["pe_score"] = 1 - self._rank_normalize(pe_valid)
        
        pb_valid = df["pb"].apply(lambda x: x if x is not None and x > 0 else np.nan)
        df["pb_score"] = 1 - self._rank_normalize(pb_valid)
        
        df["money_flow_score"] = self._rank_normalize(df["main_net_pct"])
        
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
            pe_str = f"{row['pe']:.1f}" if row['pe'] is not None else "N/A"
            print(f"  {row['code']}: score={row['total_score']:.4f}, "
                  f"PE={pe_str}, mom20={row['mom_20']:.1f}%, "
                  f"main_flow={row['main_net_pct']:.1f}%")
        
        return selected["code"].tolist()


class EnhancedBacktestEngine:
    """增强回测引擎"""
    
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
        
        print("\nFetching fundamental data...")
        fundamental = strategy.get_fundamental_data(stock_pool)
        print(f"Got fundamental data for {len(fundamental)} stocks")
        
        print("\nFetching money flow data...")
        money_flow = strategy.get_money_flow(stock_pool)
        print(f"Got money flow data for {len(money_flow)} stocks")
        
        print("\nCalculating factors...")
        factors = strategy.calculate_factors(price_data, fundamental, money_flow)
        
        if factors.empty:
            print("ERROR: No valid factors")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        selected_stocks = strategy.select_stocks(factors)
        
        if not selected_stocks:
            print("ERROR: No stocks selected")
            return {"equity_curve": pd.Series(dtype=float), "trades": []}
        
        print(f"\nBuilding portfolio with {len(selected_stocks)} stocks...")
        
        capital = self.initial_capital
        equal_weight = capital / len(selected_stocks)
        
        trades = []
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
        
        return {
            "equity_curve": pd.Series([portfolio_value], index=[datetime.now()]),
            "trades": trades,
            "selected_stocks": selected_stocks,
            "factors": factors,
            "holdings": holdings,
            "portfolio_value": portfolio_value,
        }


def calculate_metrics(portfolio_value: float, initial_capital: float) -> dict:
    """计算指标"""
    total_ret = (portfolio_value / initial_capital - 1)
    
    return {
        "total_return": f"{total_ret:.2%}",
        "portfolio_value": f"{portfolio_value:,.0f}",
        "initial_capital": f"{initial_capital:,.0f}",
    }
