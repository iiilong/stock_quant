import pandas as pd
import numpy as np
from datetime import datetime


class BacktestEngine:
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.initial_capital
        self.commission_rate = config.commission_rate
        self.stamp_tax_rate = config.stamp_tax_rate
        self.slippage = config.slippage
        self.max_position_pct = config.max_position_pct
        self.max_holdings = config.max_holdings
        self.stop_loss = config.stop_loss
        self.take_profit = config.take_profit

    def run(self, data: dict, strategy) -> dict:
        all_results = {}
        for code, df in data.items():
            result = self._backtest_single(code, df, strategy)
            if result is not None:
                all_results[code] = result
        return all_results

    def _backtest_single(self, code: str, data: pd.DataFrame,
                         strategy) -> dict:
        try:
            signals_df = strategy.generate_signals(data)
        except Exception as e:
            print(f"策略生成信号失败 {code}: {e}")
            return None

        capital = self.initial_capital
        position = 0
        buy_price = 0
        trades = []
        equity_curve = []
        holding = False

        for i in range(1, len(signals_df)):
            row = signals_df.iloc[i]
            prev_row = signals_df.iloc[i - 1]
            price = row["close"]
            date = signals_df.index[i]

            if holding:
                pnl_pct = (price - buy_price) / buy_price
                if pnl_pct <= -self.stop_loss or pnl_pct >= self.take_profit:
                    sell_price = price * (1 - self.slippage)
                    commission = sell_price * position * self.commission_rate
                    tax = sell_price * position * self.stamp_tax_rate
                    revenue = sell_price * position - commission - tax
                    capital += revenue
                    trades.append({
                        "code": code,
                        "buy_date": trades[-1]["buy_date"] if trades else date,
                        "sell_date": date,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "shares": position,
                        "pnl": revenue - buy_price * position,
                        "pnl_pct": pnl_pct,
                        "reason": "止损" if pnl_pct <= -self.stop_loss else "止盈"
                    })
                    position = 0
                    holding = False

            if row["signal"] == 1 and not holding:
                max_invest = capital * self.max_position_pct
                shares = int(max_invest / price / 100) * 100
                if shares >= 100:
                    buy_price_exec = price * (1 + self.slippage)
                    cost = buy_price_exec * shares
                    commission = cost * self.commission_rate
                    total_cost = cost + commission
                    if total_cost <= capital:
                        capital -= total_cost
                        position = shares
                        buy_price = buy_price_exec
                        holding = True
                        trades.append({
                            "code": code,
                            "buy_date": date,
                            "buy_price": buy_price_exec,
                            "shares": shares,
                            "reason": "买入信号"
                        })

            elif row["signal"] == -1 and holding:
                sell_price = price * (1 - self.slippage)
                commission = sell_price * position * self.commission_rate
                tax = sell_price * position * self.stamp_tax_rate
                revenue = sell_price * position - commission - tax
                pnl = revenue - buy_price * position
                pnl_pct = (sell_price - buy_price) / buy_price
                capital += revenue
                trades.append({
                    "code": code,
                    "buy_date": trades[-1]["buy_date"],
                    "sell_date": date,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "shares": position,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": "卖出信号"
                })
                position = 0
                holding = False

            total_value = capital + position * price
            equity_curve.append({"date": date, "equity": total_value})

        if not equity_curve:
            return None

        equity_df = pd.DataFrame(equity_curve).set_index("date")
        completed_trades = [t for t in trades if "sell_date" in t]

        return {
            "code": code,
            "equity_curve": equity_df["equity"],
            "trades": completed_trades,
            "final_capital": capital + position * signals_df.iloc[-1]["close"] if position > 0 else capital,
        }

    def aggregate_results(self, results: dict) -> dict:
        if not results:
            return {"equity_curve": pd.Series(dtype=float), "trades": []}

        all_equity = []
        all_trades = []
        for code, result in results.items():
            all_trades.extend(result["trades"])
            all_equity.append(result["equity_curve"])

        if not all_equity:
            return {"equity_curve": pd.Series(dtype=float), "trades": all_trades}

        combined = pd.concat(all_equity, axis=1)
        portfolio_equity = combined.mean(axis=1)

        return {
            "equity_curve": portfolio_equity,
            "trades": all_trades,
            "stock_results": results,
        }
