import pandas as pd
import numpy as np
from itertools import product
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')


class EnhancedMACDStrategy:
    def __init__(self, fast=12, slow=26, signal=9,
                 trend_filter=True, volume_filter=True,
                 atr_filter=True, rsi_filter=True,
                 stop_loss=0.05, take_profit=0.15,
                 trailing_stop=0.08,
                 trend_period=60, volume_ratio=1.2,
                 rsi_low=35, rsi_high=65):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.trend_filter = trend_filter
        self.volume_filter = volume_filter
        self.atr_filter = atr_filter
        self.rsi_filter = rsi_filter
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        self.trend_period = trend_period
        self.volume_ratio = volume_ratio
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.name = "EnhancedMACD"

    def _calc_rsi(self, series, period=14):
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calc_atr(self, high, low, close, period=14):
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0

        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        df["macd_line"] = ema_fast - ema_slow
        df["signal_line"] = df["macd_line"].ewm(span=self.signal, adjust=False).mean()
        df["macd_hist"] = df["macd_line"] - df["signal_line"]

        df["ema_trend"] = df["close"].ewm(span=self.trend_period, adjust=False).mean()
        df["rsi"] = self._calc_rsi(df["close"])
        df["atr"] = self._calc_atr(df["high"], df["low"], df["close"])
        df["volume_ma"] = df["volume"].rolling(20).mean()

        df["hist_rising"] = df["macd_hist"] > df["macd_hist"].shift(1)
        df["hist_falling"] = df["macd_hist"] < df["macd_hist"].shift(1)

        macd_cross_up = (
            (df["macd_line"] > df["signal_line"]) &
            (df["macd_line"].shift(1) <= df["signal_line"].shift(1))
        )
        macd_cross_down = (
            (df["macd_line"] < df["signal_line"]) &
            (df["macd_line"].shift(1) >= df["signal_line"].shift(1))
        )

        buy_mask = macd_cross_up.copy()
        sell_mask = macd_cross_down.copy()

        if self.trend_filter:
            buy_mask = buy_mask & (df["close"] > df["ema_trend"])

        if self.volume_filter:
            buy_mask = buy_mask & (df["volume"] > df["volume_ma"] * self.volume_ratio)

        if self.rsi_filter:
            buy_mask = buy_mask & (df["rsi"] > self.rsi_low) & (df["rsi"] < self.rsi_high)
            sell_mask = sell_mask | (df["rsi"] > 75)

        if self.atr_filter:
            atr_pct = df["atr"] / df["close"]
            buy_mask = buy_mask & (atr_pct > 0.01) & (atr_pct < 0.05)

        df.loc[buy_mask, "signal"] = 1
        df.loc[sell_mask, "signal"] = -1

        df["position"] = df["signal"]
        return df


class EnhancedBacktestEngine:
    def __init__(self, config):
        self.config = config

    def run(self, data: dict, strategy) -> dict:
        all_results = {}
        for code, df in data.items():
            result = self._backtest_single(code, df, strategy)
            if result is not None:
                all_results[code] = result
        return all_results

    def _backtest_single(self, code: str, data: pd.DataFrame, strategy) -> dict:
        try:
            signals_df = strategy.generate_signals(data)
        except Exception:
            return None

        capital = self.config.initial_capital
        position = 0
        buy_price = 0
        highest_since_buy = 0
        trades = []
        equity_curve = []
        holding = False
        commission_rate = self.config.commission_rate
        stamp_tax_rate = self.config.stamp_tax_rate
        slippage = self.config.slippage

        for i in range(1, len(signals_df)):
            row = signals_df.iloc[i]
            price = row["close"]
            date = signals_df.index[i]

            if holding:
                highest_since_buy = max(highest_since_buy, price)
                trailing_stop_price = highest_since_buy * (1 - strategy.trailing_stop)
                pnl_pct = (price - buy_price) / buy_price

                should_stop = False
                stop_reason = ""
                if pnl_pct <= -strategy.stop_loss:
                    should_stop = True
                    stop_reason = "stop_loss"
                elif pnl_pct >= strategy.take_profit:
                    should_stop = True
                    stop_reason = "take_profit"
                elif price <= trailing_stop_price and pnl_pct > 0.02:
                    should_stop = True
                    stop_reason = "trailing_stop"

                if should_stop:
                    sell_price = price * (1 - slippage)
                    commission = sell_price * position * commission_rate
                    tax = sell_price * position * stamp_tax_rate
                    revenue = sell_price * position - commission - tax
                    capital += revenue
                    trades.append({
                        "code": code,
                        "buy_date": trades[-1]["buy_date"],
                        "sell_date": date,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "shares": position,
                        "pnl": revenue - buy_price * position,
                        "pnl_pct": pnl_pct,
                        "reason": stop_reason
                    })
                    position = 0
                    holding = False

            if row["signal"] == 1 and not holding:
                max_invest = capital * self.config.max_position_pct
                shares = int(max_invest / price / 100) * 100
                if shares >= 100:
                    buy_price_exec = price * (1 + slippage)
                    cost = buy_price_exec * shares
                    commission = cost * commission_rate
                    total_cost = cost + commission
                    if total_cost <= capital:
                        capital -= total_cost
                        position = shares
                        buy_price = buy_price_exec
                        highest_since_buy = buy_price_exec
                        holding = True
                        trades.append({
                            "code": code,
                            "buy_date": date,
                            "buy_price": buy_price_exec,
                            "shares": shares,
                            "reason": "buy_signal"
                        })

            elif row["signal"] == -1 and holding:
                sell_price = price * (1 - slippage)
                commission = sell_price * position * commission_rate
                tax = sell_price * position * stamp_tax_rate
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
                    "reason": "sell_signal"
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


def calculate_sharpe(equity_curve):
    returns = equity_curve.pct_change().dropna()
    if len(returns) < 10 or returns.std() == 0:
        return -10
    return returns.mean() / returns.std() * np.sqrt(252)


def calculate_max_dd(equity_curve):
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    return dd.min()


def calculate_calmar(equity_curve):
    total_days = len(equity_curve)
    total_ret = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / total_days) - 1 if total_days > 0 else 0
    mdd = abs(calculate_max_dd(equity_curve))
    return ann_ret / mdd if mdd > 0 else 0


def optimize_macd_params(data: dict, config, n_iter: int = 50) -> list:
    import random
    random.seed(42)

    param_ranges = {
        "fast": [6, 8, 10, 12, 14],
        "slow": [20, 22, 24, 26, 28, 30],
        "signal": [6, 7, 8, 9, 10, 11],
        "stop_loss": [0.03, 0.04, 0.05, 0.06, 0.08, 0.10],
        "take_profit": [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25],
        "trailing_stop": [0.04, 0.06, 0.08, 0.10, 0.12],
        "volume_ratio": [0.8, 1.0, 1.2, 1.5],
        "rsi_low": [25, 30, 35, 40],
        "rsi_high": [60, 65, 70, 75],
    }

    results = []
    engine = EnhancedBacktestEngine(config)

    print(f"Running {n_iter} random parameter combinations...")

    for i in range(n_iter):
        params = {k: random.choice(v) for k, v in param_ranges.items()}

        if params["fast"] >= params["slow"]:
            params["slow"] = params["fast"] + 10

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{n_iter}")

        strategy = EnhancedMACDStrategy(**params)
        backtest_results = engine.run(data, strategy)
        aggregated = engine.aggregate_results(backtest_results)

        if aggregated["equity_curve"].empty or len(aggregated["equity_curve"]) < 50:
            continue

        equity = aggregated["equity_curve"]
        trades = aggregated["trades"]

        sharpe = calculate_sharpe(equity)
        max_dd = calculate_max_dd(equity)
        calmar = calculate_calmar(equity)
        total_ret = equity.iloc[-1] / equity.iloc[0] - 1

        n_trades = len(trades)
        winning = [t for t in trades if t.get("pnl", 0) > 0]
        win_rate = len(winning) / n_trades if n_trades > 0 else 0

        score = (
            sharpe * 0.35 +
            calmar * 0.25 +
            win_rate * 5 * 0.15 +
            (1 + total_ret) * 0.15 +
            (1 - abs(max_dd)) * 0.10
        )

        if max_dd < -0.15:
            score *= 0.5
        if n_trades < 10:
            score *= 0.7

        results.append({
            "params": params,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "calmar": calmar,
            "total_return": total_ret,
            "win_rate": win_rate,
            "trades": n_trades,
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]
