import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import json
import os
import warnings
import time
warnings.filterwarnings('ignore')


class RobustScheduler:
    """稳健调度器 - 处理节假日和执行时序"""
    
    def __init__(self):
        self.trade_calendar = None
    
    def get_trade_calendar(self) -> list:
        """获取交易日历"""
        if self.trade_calendar is not None:
            return self.trade_calendar
        
        try:
            df = ak.tool_trade_date_hist_sina()
            if df is not None and not df.empty:
                self.trade_calendar = pd.to_datetime(df.iloc[:, 0]).tolist()
                return self.trade_calendar
        except Exception:
            pass
        
        return []
    
    def get_last_trade_date(self, date: datetime = None) -> datetime:
        """获取最近的交易日"""
        if date is None:
            date = datetime.now()
        
        calendar = self.get_trade_calendar()
        if not calendar:
            return date
        
        date = pd.Timestamp(date)
        past_dates = [d for d in calendar if d <= date]
        
        if past_dates:
            return past_dates[-1]
        return date
    
    def get_next_trade_date(self, date: datetime = None) -> datetime:
        """获取下一个交易日"""
        if date is None:
            date = datetime.now()
        
        calendar = self.get_trade_calendar()
        if not calendar:
            return date + timedelta(days=1)
        
        date = pd.Timestamp(date)
        future_dates = [d for d in calendar if d > date]
        
        if future_dates:
            return future_dates[0]
        return date + timedelta(days=1)
    
    def get_month_start_trade_date(self, year: int, month: int) -> datetime:
        """获取某月第一个交易日"""
        first_day = datetime(year, month, 1)
        return self.get_next_trade_date(first_day - timedelta(days=1))
    
    def get_month_end_trade_date(self, year: int, month: int) -> datetime:
        """获取某月最后一个交易日"""
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return self.get_last_trade_date(last_day)
    
    def should_rebalance(self, today: datetime = None) -> bool:
        """判断今天是否应该调仓"""
        if today is None:
            today = datetime.now()
        
        today = pd.Timestamp(today)
        
        calendar = self.get_trade_calendar()
        if not calendar:
            return today.day <= 3
        
        month_start = self.get_month_start_trade_date(today.year, today.month)
        
        return today.date() == month_start.date()


class RobustOrderExecutor:
    """稳健订单执行器"""
    
    def __init__(self, slippage: float = 0.002, 
                 max_slippage: float = 0.03):
        self.slippage = slippage
        self.max_slippage = max_slippage
    
    def check_executable(self, code: str, price_data: dict, 
                         date: datetime) -> dict:
        """检查股票是否可执行"""
        result = {
            "executable": True,
            "reason": "",
            "estimated_price": None,
        }
        
        if code not in price_data:
            result["executable"] = False
            result["reason"] = "no_data"
            return result
        
        df = price_data[code]
        
        if date not in df.index:
            result["executable"] = False
            result["reason"] = "no_trading_today"
            return result
        
        row = df.loc[date]
        open_price = float(row.iloc[1])
        close_price = float(row.iloc[2])
        high_price = float(row.iloc[3])
        low_price = float(row.iloc[4])
        
        if high_price == low_price:
            result["executable"] = False
            result["reason"] = "limit_up_or_down"
            return result
        
        if close_price >= high_price * 0.99:
            result["executable"] = False
            result["reason"] = "near_limit_up"
            return result
        
        if close_price <= low_price * 1.01:
            result["executable"] = False
            result["reason"] = "near_limit_down"
            return result
        
        result["estimated_price"] = open_price * (1 + self.slippage)
        
        return result
    
    def estimate_slippage(self, order_size: float, 
                          volume: float) -> float:
        """估算滑点"""
        if volume == 0:
            return self.max_slippage
        
        participation = order_size / volume
        
        if participation < 0.01:
            return self.slippage
        elif participation < 0.05:
            return self.slippage * 2
        elif participation < 0.1:
            return self.slippage * 3
        else:
            return min(self.max_slippage, self.slippage * 5)


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, max_positions: int = 5,
                 max_position_pct: float = 0.20,
                 min_position_pct: float = 0.10,
                 cash_reserve_pct: float = 0.10):
        self.max_positions = max_positions
        self.max_position_pct = max_position_pct
        self.min_position_pct = min_position_pct
        self.cash_reserve_pct = cash_reserve_pct
    
    def calculate_order_sizes(self, total_capital: float,
                               target_stocks: list,
                               current_holdings: dict,
                               price_data: dict,
                               date: datetime) -> list:
        """计算订单大小"""
        orders = []
        
        available_capital = total_capital * (1 - self.cash_reserve_pct)
        
        stocks_to_sell = [s for s in current_holdings if s not in target_stocks]
        for code in stocks_to_sell:
            if code in price_data and date in price_data[code].index:
                price = float(price_data[code].loc[date].iloc[2])
                shares = current_holdings[code]["shares"]
                orders.append({
                    "code": code,
                    "action": "SELL",
                    "shares": shares,
                    "price": price,
                })
        
        stocks_to_buy = [s for s in target_stocks if s not in current_holdings]
        
        if stocks_to_buy:
            existing_value = sum(
                current_holdings[s]["shares"] * 
                (float(price_data[s].loc[date].iloc[2]) if s in price_data and date in price_data[s].index else 0)
                for s in current_holdings if s not in stocks_to_sell
            )
            
            buy_budget = available_capital - existing_value
            buy_budget = max(0, buy_budget)
            
            per_stock_budget = buy_budget / len(stocks_to_buy)
            per_stock_budget = min(per_stock_budget, total_capital * self.max_position_pct)
            per_stock_budget = max(per_stock_budget, total_capital * self.min_position_pct)
            
            for code in stocks_to_buy:
                if code in price_data and date in price_data[code].index:
                    price = float(price_data[code].loc[date].iloc[2])
                    shares = int(per_stock_budget / price / 100) * 100
                    if shares >= 100:
                        orders.append({
                            "code": code,
                            "action": "BUY",
                            "shares": shares,
                            "price": price,
                        })
        
        return orders


class RiskMonitor:
    """风险监控器"""
    
    def __init__(self, max_drawdown: float = 0.15,
                 max_single_loss: float = 0.08,
                 max_sector_exposure: float = 0.40):
        self.max_drawdown = max_drawdown
        self.max_single_loss = max_single_loss
        self.max_sector_exposure = max_sector_exposure
        self.peak_value = 0
    
    def check_portfolio_risk(self, holdings: dict, 
                             price_data: dict,
                             date: datetime) -> dict:
        """检查组合风险"""
        total_value = 0
        for code, h in holdings.items():
            if code in price_data and date in price_data[code].index:
                current_price = float(price_data[code].loc[date].iloc[2])
                total_value += h["shares"] * current_price
        
        if total_value > self.peak_value:
            self.peak_value = total_value
        
        drawdown = (total_value - self.peak_value) / self.peak_value if self.peak_value > 0 else 0
        
        alerts = []
        
        if drawdown < -self.max_drawdown:
            alerts.append({
                "type": "MAX_DRAWDOWN",
                "message": f"Drawdown {drawdown:.2%} exceeds limit",
                "action": "SELL_ALL"
            })
        
        for code, h in holdings.items():
            if code in price_data and date in price_data[code].index:
                current_price = float(price_data[code].loc[date].iloc[2])
                pnl = (current_price - h["buy_price"]) / h["buy_price"]
                
                if pnl < -self.max_single_loss:
                    alerts.append({
                        "type": "STOP_LOSS",
                        "message": f"{code} loss {pnl:.2%} exceeds limit",
                        "action": "SELL",
                        "code": code
                    })
        
        return {
            "total_value": total_value,
            "drawdown": drawdown,
            "alerts": alerts,
            "risk_level": "HIGH" if alerts else "NORMAL"
        }


def create_robust_monthly_report(portfolio_summary: dict,
                                  selected_stocks: list,
                                  market_regime: str,
                                  risk_status: dict,
                                  trade_date: datetime) -> str:
    """生成稳健月度报告"""
    report = f"""
========================================
  Monthly Report - {trade_date.strftime('%Y-%m-%d')}
========================================

Market Regime: {market_regime}
Risk Level: {risk_status.get('risk_level', 'UNKNOWN')}
Current Drawdown: {risk_status.get('drawdown', 0):.2%}

Portfolio Summary:
  Total Value: {portfolio_summary.get('total_value', 0):,.0f}
  Cash: {portfolio_summary.get('cash', 0):,.0f}
  Holdings Value: {portfolio_summary.get('market_value', 0):,.0f}

Selected Stocks for Next Month:
"""
    for i, code in enumerate(selected_stocks, 1):
        report += f"  {i}. {code}\n"
    
    if risk_status.get('alerts'):
        report += f"\nRisk Alerts:\n"
        for alert in risk_status['alerts']:
            report += f"  - {alert['type']}: {alert['message']}\n"
    
    report += f"\nExecution Notes:\n"
    report += f"  - Execute on first trading day of next month\n"
    report += f"  - Check for limit up/down before executing\n"
    report += f"  - Reserve 10% cash buffer\n"
    report += f"  - Monitor positions daily\n"
    report += "========================================\n"
    
    return report
