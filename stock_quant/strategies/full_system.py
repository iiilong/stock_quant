import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import json
import os
import warnings
import time
warnings.filterwarnings('ignore')


class FullMarketScanner:
    """全市场股票扫描器"""
    
    def __init__(self):
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_all_stocks(self) -> list:
        """获取全市场股票列表"""
        cache_file = os.path.join(self.cache_dir, "stock_list.pkl")
        
        if os.path.exists(cache_file):
            mod_time = os.path.getmtime(cache_file)
            if time.time() - mod_time < 86400:
                return pd.read_pickle(cache_file)
        
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                codes = df.iloc[:, 1].tolist()
                codes = [c for c in codes if isinstance(c, str) and len(c) == 6]
                pd.Series(codes).to_pickle(cache_file)
                return codes
        except Exception as e:
            print(f"Error fetching stock list: {e}")
        
        return []
    
    def get_industry_stocks(self) -> dict:
        """获取行业分类"""
        cache_file = os.path.join(self.cache_dir, "industry.pkl")
        
        if os.path.exists(cache_file):
            mod_time = os.path.getmtime(cache_file)
            if time.time() - mod_time < 86400:
                return pd.read_pickle(cache_file)
        
        result = {}
        try:
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    industry_name = row.iloc[0]
                    try:
                        stocks = ak.stock_board_industry_cons_em(symbol=industry_name)
                        if stocks is not None and not stocks.empty:
                            codes = stocks.iloc[:, 0].tolist()
                            result[industry_name] = codes
                    except Exception:
                        continue
                    time.sleep(0.3)
        except Exception:
            pass
        
        if result:
            pd.Series(result).to_pickle(cache_file)
        
        return result


class PortfolioMonitor:
    """持仓监控器"""
    
    def __init__(self, portfolio_file: str = "portfolio.json"):
        self.portfolio_file = portfolio_file
        self.portfolio = self._load_portfolio()
    
    def _load_portfolio(self) -> dict:
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "holdings": {},
            "cash": 0,
            "initial_capital": 100000,
            "history": [],
        }
    
    def _save_portfolio(self):
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(self.portfolio, f, ensure_ascii=False, indent=2, default=str)
    
    def update_prices(self, price_data: dict):
        """更新持仓价格"""
        for code, holding in self.portfolio["holdings"].items():
            if code in price_data:
                df = price_data[code]
                current_price = float(df.iloc[-1, 2])
                holding["current_price"] = current_price
                holding["market_value"] = holding["shares"] * current_price
                holding["pnl"] = (current_price - holding["buy_price"]) / holding["buy_price"]
        
        self._save_portfolio()
    
    def add_position(self, code: str, shares: int, price: float, date: str):
        """添加持仓"""
        if code in self.portfolio["holdings"]:
            h = self.portfolio["holdings"][code]
            total_shares = h["shares"] + shares
            avg_price = (h["shares"] * h["buy_price"] + shares * price) / total_shares
            h["shares"] = total_shares
            h["buy_price"] = avg_price
        else:
            self.portfolio["holdings"][code] = {
                "shares": shares,
                "buy_price": price,
                "buy_date": date,
                "current_price": price,
                "market_value": shares * price,
                "pnl": 0,
            }
        
        cost = shares * price * 1.001
        self.portfolio["cash"] -= cost
        self._save_portfolio()
    
    def remove_position(self, code: str, price: float, date: str):
        """移除持仓"""
        if code in self.portfolio["holdings"]:
            h = self.portfolio["holdings"][code]
            revenue = h["shares"] * price * 0.998
            self.portfolio["cash"] += revenue
            
            self.portfolio["history"].append({
                "code": code,
                "shares": h["shares"],
                "buy_price": h["buy_price"],
                "sell_price": price,
                "pnl": h["pnl"],
                "date": date,
            })
            
            del self.portfolio["holdings"][code]
            self._save_portfolio()
    
    def get_summary(self) -> dict:
        """获取持仓摘要"""
        total_market_value = sum(
            h.get("market_value", 0) 
            for h in self.portfolio["holdings"].values()
        )
        total_value = self.portfolio["cash"] + total_market_value
        total_pnl = (total_value / self.portfolio["initial_capital"] - 1) * 100
        
        return {
            "cash": self.portfolio["cash"],
            "market_value": total_market_value,
            "total_value": total_value,
            "total_pnl": f"{total_pnl:.2f}%",
            "holdings": self.portfolio["holdings"],
            "history_count": len(self.portfolio["history"]),
        }


class AutoTrader:
    """自动交易系统（模拟）"""
    
    def __init__(self, portfolio_monitor: PortfolioMonitor):
        self.monitor = portfolio_monitor
    
    def execute_signals(self, signals: list, price_data: dict, date: str):
        """执行交易信号"""
        for signal in signals:
            code = signal["code"]
            action = signal["action"]
            
            if action == "BUY":
                if code not in self.monitor.portfolio["holdings"]:
                    price = signal.get("price")
                    if not price and code in price_data:
                        price = float(price_data[code].iloc[-1, 2])
                    
                    if price:
                        available_cash = self.monitor.portfolio["cash"] * 0.95
                        shares = int(available_cash / price / 100) * 100
                        if shares >= 100:
                            self.monitor.add_position(code, shares, price, date)
                            print(f"  BUY {code}: {shares} shares @ {price:.2f}")
            
            elif action == "SELL":
                if code in self.monitor.portfolio["holdings"]:
                    price = signal.get("price")
                    if not price and code in price_data:
                        price = float(price_data[code].iloc[-1, 2])
                    
                    if price:
                        self.monitor.remove_position(code, price, date)
                        print(f"  SELL {code} @ {price:.2f}")


class EnhancedMultiFactorStrategy:
    """增强多因子策略（含行业轮动）"""
    
    def __init__(self, top_n=5):
        self.top_n = top_n
    
    def get_price_data(self, codes: list, days: int = 120) -> dict:
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
                if (i + 1) % 50 == 0:
                    print(f"  Fetched {i+1}/{len(codes)} stocks...")
                time.sleep(0.1)
            except Exception:
                continue
        return result
    
    def get_realtime_data(self, codes: list) -> dict:
        """获取实时数据"""
        result = {"pe": {}, "money_flow": {}, "industry": {}}
        
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
                                elif '行业' in col_name:
                                    result["industry"][code] = str(val)
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
    
    def calculate_factors(self, price_data: dict, realtime: dict) -> pd.DataFrame:
        """计算因子"""
        records = []
        
        for code, df in price_data.items():
            try:
                close = df.iloc[:, 2].astype(float)
                volume = df.iloc[:, 5].astype(float)
                
                n = len(close)
                if n < 30:
                    continue
                
                mom_5 = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if n >= 5 else 0
                mom_20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if n >= 20 else 0
                mom_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100 if n >= 60 else mom_20
                
                reversal_5 = -mom_5
                
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
                
                pe = realtime.get("pe", {}).get(code, None)
                money_flow = realtime.get("money_flow", {}).get(code, 0)
                industry = realtime.get("industry", {}).get(code, "unknown")
                
                records.append({
                    "code": code,
                    "mom_5": mom_5,
                    "mom_20": mom_20,
                    "mom_60": mom_60,
                    "reversal_5": reversal_5,
                    "vol_20": vol_20_val,
                    "vol_ratio": vol_ratio,
                    "trend_score": trend_score,
                    "pe": pe,
                    "money_flow": money_flow,
                    "industry": industry,
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
        """选股，最多top_n只"""
        valid = factors.dropna(subset=["total_score"])
        if valid.empty:
            return []
        
        selected = valid.nlargest(self.top_n, "total_score")
        return selected["code"].tolist()


class Scheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.tasks = []
    
    def add_task(self, name: str, func, schedule: str = "monthly"):
        self.tasks.append({
            "name": name,
            "func": func,
            "schedule": schedule,
            "last_run": None,
        })
    
    def run_pending(self):
        now = datetime.now()
        for task in self.tasks:
            if self._should_run(task, now):
                print(f"\nRunning task: {task['name']}")
                task["func"]()
                task["last_run"] = now
    
    def _should_run(self, task: dict, now: datetime) -> bool:
        if task["last_run"] is None:
            return True
        
        if task["schedule"] == "daily":
            return now.date() > task["last_run"].date()
        elif task["schedule"] == "monthly":
            return now.month != task["last_run"].month or now.year != task["last_run"].year
        return False


def create_monthly_report(portfolio_monitor: PortfolioMonitor, 
                          selected_stocks: list,
                          market_regime: str) -> str:
    """生成月度报告"""
    summary = portfolio_monitor.get_summary()
    
    report = f"""
========================================
  Monthly Report - {datetime.now().strftime('%Y-%m-%d')}
========================================

Market Regime: {market_regime}

Portfolio Summary:
  Cash: {summary['cash']:,.0f}
  Market Value: {summary['market_value']:,.0f}
  Total Value: {summary['total_value']:,.0f}
  Total PnL: {summary['total_pnl']}

Holdings:
"""
    for code, h in summary["holdings"].items():
        report += f"  {code}: {h['shares']} shares @ {h['buy_price']:.2f} -> {h.get('current_price', 0):.2f} ({h.get('pnl', 0):.1%})\n"
    
    report += f"\nSelected Stocks for Next Month:\n"
    for code in selected_stocks:
        report += f"  {code}\n"
    
    report += f"\nTrade History: {summary['history_count']} trades\n"
    report += "========================================\n"
    
    return report
