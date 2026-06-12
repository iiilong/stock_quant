import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import json
import os
import warnings
import time
warnings.filterwarnings('ignore')


class DailyRiskMonitor:
    """
    日内风控监控器
    
    每个交易日运行：
    1. 检查止损 - 单股亏损超8%立即卖出
    2. 检查移动止损 - 回撤保护
    3. 检查组合回撤 - 总回撤超15%清仓
    4. 检查大盘趋势 - 熊市信号清仓
    """
    
    def __init__(self, portfolio_file: str = "portfolio.json"):
        self.portfolio_file = portfolio_file
        self.stop_loss_pct = 0.08
        self.trailing_stop_pct = 0.10
        self.max_drawdown_pct = 0.15
        
    def load_portfolio(self) -> dict:
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"holdings": {}, "cash": 0, "peak_value": 0}
    
    def save_portfolio(self, portfolio: dict):
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2, default=str)
    
    def get_realtime_prices(self, codes: list) -> dict:
        """获取实时价格"""
        result = {}
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                for code in codes:
                    try:
                        stock_data = df[df.iloc[:, 1] == code]
                        if not stock_data.empty:
                            row = stock_data.iloc[0]
                            price = None
                            change_pct = None
                            for col_idx in range(len(row)):
                                col_name = str(row.index[col_idx])
                                val = row.iloc[col_idx]
                                if '最新价' in col_name or '收盘' in col_name:
                                    try:
                                        price = float(val)
                                    except:
                                        pass
                                elif '涨跌幅' in col_name:
                                    try:
                                        change_pct = float(val)
                                    except:
                                        pass
                            if price:
                                result[code] = {
                                    "price": price,
                                    "change_pct": change_pct or 0
                                }
                    except Exception:
                        continue
        except Exception:
            pass
        return result
    
    def check_stop_loss(self, portfolio: dict, prices: dict) -> list:
        """检查止损"""
        signals = []
        
        for code, holding in portfolio["holdings"].items():
            if code in prices:
                current_price = prices[code]["price"]
                buy_price = holding["buy_price"]
                pnl_pct = (current_price - buy_price) / buy_price
                
                if pnl_pct < -self.stop_loss_pct:
                    signals.append({
                        "code": code,
                        "action": "SELL",
                        "reason": "stop_loss",
                        "pnl_pct": pnl_pct,
                        "price": current_price
                    })
        
        return signals
    
    def check_trailing_stop(self, portfolio: dict, prices: dict) -> list:
        """检查移动止损"""
        signals = []
        
        for code, holding in portfolio["holdings"].items():
            if code in prices:
                current_price = prices[code]["price"]
                highest = holding.get("highest_price", holding["buy_price"])
                
                if current_price > highest:
                    holding["highest_price"] = current_price
                    highest = current_price
                
                trailing_stop = highest * (1 - self.trailing_stop_pct)
                
                if current_price < trailing_stop and current_price > holding["buy_price"]:
                    pnl_pct = (current_price - holding["buy_price"]) / holding["buy_price"]
                    signals.append({
                        "code": code,
                        "action": "SELL",
                        "reason": "trailing_stop",
                        "pnl_pct": pnl_pct,
                        "price": current_price
                    })
        
        return signals
    
    def check_max_drawdown(self, portfolio: dict, prices: dict) -> list:
        """检查组合最大回撤"""
        signals = []
        
        total_value = portfolio["cash"]
        for code, holding in portfolio["holdings"].items():
            if code in prices:
                total_value += holding["shares"] * prices[code]["price"]
        
        peak = portfolio.get("peak_value", total_value)
        if total_value > peak:
            portfolio["peak_value"] = total_value
            peak = total_value
        
        drawdown = (total_value - peak) / peak if peak > 0 else 0
        
        if drawdown < -self.max_drawdown_pct:
            for code, holding in portfolio["holdings"].items():
                if code in prices:
                    signals.append({
                        "code": code,
                        "action": "SELL",
                        "reason": "max_drawdown",
                        "pnl_pct": 0,
                        "price": prices[code]["price"]
                    })
        
        return signals
    
    def check_market_trend(self) -> str:
        """检查大盘趋势"""
        try:
            df = ak.stock_zh_index_daily(symbol="sh000300")
            if df is not None and not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                close = df["close"].astype(float)
                
                if len(close) < 60:
                    return "neutral"
                
                ma20 = close.rolling(20).mean().iloc[-1]
                ma60 = close.rolling(60).mean().iloc[-1]
                current = close.iloc[-1]
                
                if ma20 < ma60 and current < ma20:
                    return "bear"
                elif ma20 > ma60 and current > ma20:
                    return "bull"
                else:
                    return "neutral"
        except Exception:
            pass
        return "neutral"
    
    def run_daily_check(self) -> dict:
        """运行每日检查"""
        print(f"\n{'='*60}")
        print(f"  Daily Risk Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")
        
        portfolio = self.load_portfolio()
        
        if not portfolio["holdings"]:
            print("  No holdings to monitor")
            return {"signals": [], "risk_level": "LOW"}
        
        codes = list(portfolio["holdings"].keys())
        print(f"  Checking {len(codes)} positions...")
        
        prices = self.get_realtime_prices(codes)
        
        if not prices:
            print("  WARNING: Cannot fetch realtime prices")
            return {"signals": [], "risk_level": "UNKNOWN"}
        
        all_signals = []
        
        stop_loss_signals = self.check_stop_loss(portfolio, prices)
        all_signals.extend(stop_loss_signals)
        if stop_loss_signals:
            print(f"  STOP LOSS triggered: {len(stop_loss_signals)} positions")
            for s in stop_loss_signals:
                print(f"    {s['code']}: {s['pnl_pct']:.2%}")
        
        trailing_signals = self.check_trailing_stop(portfolio, prices)
        all_signals.extend(trailing_signals)
        if trailing_signals:
            print(f"  TRAILING STOP triggered: {len(trailing_signals)} positions")
            for s in trailing_signals:
                print(f"    {s['code']}: {s['pnl_pct']:.2%}")
        
        dd_signals = self.check_max_drawdown(portfolio, prices)
        all_signals.extend(dd_signals)
        if dd_signals:
            print(f"  MAX DRAWDOWN triggered: {len(dd_signals)} positions")
        
        market_regime = self.check_market_trend()
        if market_regime == "bear":
            print(f"  BEAR MARKET detected - consider reducing positions")
            for code in codes:
                if code not in [s["code"] for s in all_signals]:
                    all_signals.append({
                        "code": code,
                        "action": "SELL",
                        "reason": "bear_market",
                        "pnl_pct": 0,
                        "price": prices.get(code, {}).get("price", 0)
                    })
        
        print(f"\n  Portfolio Status:")
        total_value = portfolio["cash"]
        for code, holding in portfolio["holdings"].items():
            if code in prices:
                current_price = prices[code]["price"]
                market_value = holding["shares"] * current_price
                total_value += market_value
                pnl = (current_price - holding["buy_price"]) / holding["buy_price"]
                print(f"    {code}: {holding['shares']} shares, "
                      f"buy={holding['buy_price']:.2f}, "
                      f"now={current_price:.2f}, "
                      f"pnl={pnl:.2%}")
        
        print(f"    Total: {total_value:,.0f}")
        
        risk_level = "HIGH" if all_signals else "NORMAL"
        
        print(f"\n  Risk Level: {risk_level}")
        print(f"  Signals: {len(all_signals)}")
        
        return {
            "signals": all_signals,
            "risk_level": risk_level,
            "market_regime": market_regime,
            "portfolio_value": total_value,
            "prices": prices
        }
    
    def execute_signals(self, signals: list, prices: dict):
        """执行信号"""
        if not signals:
            return
        
        portfolio = self.load_portfolio()
        
        for signal in signals:
            code = signal["code"]
            if code in portfolio["holdings"] and code in prices:
                holding = portfolio["holdings"][code]
                sell_price = prices[code]["price"]
                revenue = holding["shares"] * sell_price * 0.998
                portfolio["cash"] += revenue
                
                print(f"  EXECUTED: SELL {code} @ {sell_price:.2f} "
                      f"(reason: {signal['reason']})")
                
                del portfolio["holdings"][code]
        
        self.save_portfolio(portfolio)
        print(f"  Portfolio updated")


class PositionTracker:
    """持仓追踪器 - 记录最高价用于移动止损"""
    
    def __init__(self, portfolio_file: str = "portfolio.json"):
        self.portfolio_file = portfolio_file
    
    def update_highest_prices(self, prices: dict):
        if not os.path.exists(self.portfolio_file):
            return
        
        with open(self.portfolio_file, 'r', encoding='utf-8') as f:
            portfolio = json.load(f)
        
        updated = False
        for code, holding in portfolio["holdings"].items():
            if code in prices:
                current_price = prices[code]["price"]
                highest = holding.get("highest_price", holding["buy_price"])
                if current_price > highest:
                    holding["highest_price"] = current_price
                    updated = True
        
        if updated:
            with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, ensure_ascii=False, indent=2, default=str)


def create_daily_report(result: dict) -> str:
    """生成日报"""
    report = f"""
========================================
  Daily Risk Report - {datetime.now().strftime('%Y-%m-%d')}
========================================

Market Regime: {result.get('market_regime', 'unknown')}
Risk Level: {result.get('risk_level', 'unknown')}
Portfolio Value: {result.get('portfolio_value', 0):,.0f}

Signals: {len(result.get('signals', []))}
"""
    for signal in result.get("signals", []):
        report += f"  - {signal['code']}: {signal['action']} ({signal['reason']})\n"
    
    report += "========================================\n"
    return report
