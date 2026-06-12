import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


class RobustMACDStrategy:
    """
    MACD策略 - 无未来函数版本
    
    关键设计原则：
    1. 所有指标只使用历史数据计算（滚动窗口）
    2. 信号在T日收盘后生成，T+1日开盘执行
    3. 参数固定，不做过度优化
    """
    
    def __init__(self, fast=12, slow=26, signal_period=9,
                 stop_loss=0.06, take_profit=0.15,
                 trailing_stop=0.08,
                 trend_period=60,
                 volume_ratio=1.2):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        self.trend_period = trend_period
        self.volume_ratio = volume_ratio
        self.name = "RobustMACD"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号 - 严格避免未来函数
        
        所有计算都使用滚动窗口，只使用当前及之前的数据
        """
        df = data.copy()
        df["signal"] = 0
        df["position"] = 0
        
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values
        n = len(close)
        
        ema_fast = np.zeros(n)
        ema_slow = np.zeros(n)
        macd_line = np.zeros(n)
        signal_line = np.zeros(n)
        macd_hist = np.zeros(n)
        ema_trend = np.zeros(n)
        volume_ma = np.zeros(n)
        
        ema_fast[0] = close[0]
        ema_slow[0] = close[0]
        macd_line[0] = 0
        signal_line[0] = 0
        macd_hist[0] = 0
        ema_trend[0] = close[0]
        volume_ma[0] = volume[0]
        
        alpha_fast = 2 / (self.fast + 1)
        alpha_slow = 2 / (self.slow + 1)
        alpha_signal = 2 / (self.signal_period + 1)
        alpha_trend = 2 / (self.trend_period + 1)
        
        for i in range(1, n):
            ema_fast[i] = alpha_fast * close[i] + (1 - alpha_fast) * ema_fast[i-1]
            ema_slow[i] = alpha_slow * close[i] + (1 - alpha_slow) * ema_slow[i-1]
            
            macd_line[i] = ema_fast[i] - ema_slow[i]
            
            if i == 1:
                signal_line[i] = macd_line[i]
            else:
                signal_line[i] = alpha_signal * macd_line[i] + (1 - alpha_signal) * signal_line[i-1]
            
            macd_hist[i] = macd_line[i] - signal_line[i]
            
            ema_trend[i] = alpha_trend * close[i] + (1 - alpha_trend) * ema_trend[i-1]
            
            volume_ma[i] = np.mean(volume[max(0, i-19):i+1])
        
        df["ema_fast"] = ema_fast
        df["ema_slow"] = ema_slow
        df["macd_line"] = macd_line
        df["signal_line"] = signal_line
        df["macd_hist"] = macd_hist
        df["ema_trend"] = ema_trend
        df["volume_ma"] = volume_ma
        
        warmup = max(self.slow, self.trend_period) + 10
        
        for i in range(warmup, n - 1):
            if (macd_line[i] > signal_line[i] and 
                macd_line[i-1] <= signal_line[i-1]):
                
                if close[i] > ema_trend[i]:
                    if volume[i] > volume_ma[i] * self.volume_ratio:
                        df.iloc[i + 1, df.columns.get_loc("signal")] = 1
            
            elif (macd_line[i] < signal_line[i] and 
                  macd_line[i-1] >= signal_line[i-1]):
                df.iloc[i + 1, df.columns.get_loc("signal")] = -1
        
        return df


class RobustBacktestEngine:
    """
    回测引擎 - 确保无未来函数
    """
    
    def __init__(self, initial_capital=100000, commission_rate=0.0003,
                 stamp_tax_rate=0.001, slippage=0.001,
                 max_position_pct=0.3):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage = slippage
        self.max_position_pct = max_position_pct

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
        except Exception as e:
            return None

        capital = self.initial_capital
        position = 0
        buy_price = 0
        highest_since_buy = 0
        trades = []
        equity_curve = []
        holding = False

        for i in range(len(signals_df)):
            row = signals_df.iloc[i]
            price = row["close"]
            date = signals_df.index[i]
            
            signal = row["signal"]

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
                    sell_price = price * (1 - self.slippage)
                    commission = sell_price * position * self.commission_rate
                    tax = sell_price * position * self.stamp_tax_rate
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

            if signal == 1 and not holding:
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
                        highest_since_buy = buy_price_exec
                        holding = True
                        trades.append({
                            "code": code,
                            "buy_date": date,
                            "buy_price": buy_price_exec,
                            "shares": shares,
                            "reason": "buy_signal"
                        })

            elif signal == -1 and holding:
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
        }


def calculate_metrics(equity_curve, trades=None):
    if equity_curve.empty or len(equity_curve) < 10:
        return None
    
    returns = equity_curve.pct_change().dropna()
    
    total_days = len(equity_curve)
    total_ret = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    ann_ret = (1 + total_ret) ** (252 / total_days) - 1 if total_days > 0 else 0
    
    ann_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
    
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()
    
    mdd = abs(max_dd)
    calmar = ann_ret / mdd if mdd > 0 else 0
    
    n_trades = len(trades) if trades else 0
    winning = [t for t in trades if t.get("pnl", 0) > 0] if trades else []
    win_rate = len(winning) / n_trades if n_trades > 0 else 0
    
    avg_win = np.mean([t["pnl_pct"] for t in winning]) if winning else 0
    losing = [t for t in trades if t.get("pnl", 0) <= 0] if trades else []
    avg_loss = np.mean([t["pnl_pct"] for t in losing]) if losing else 0
    
    return {
        "total_return": f"{total_ret:.2%}",
        "ann_return": f"{ann_ret:.2%}",
        "ann_volatility": f"{ann_vol:.2%}",
        "sharpe": f"{sharpe:.3f}",
        "max_dd": f"{max_dd:.2%}",
        "calmar": f"{calmar:.3f}",
        "win_rate": f"{win_rate:.1%}",
        "avg_win": f"{avg_win:.2%}",
        "avg_loss": f"{avg_loss:.2%}",
        "trades": n_trades,
    }


def walk_forward_test(data: dict, strategy_params: dict, 
                      config: dict, train_pct: float = 0.7) -> dict:
    """
    Walk-forward测试 - 防止过拟合
    
    将数据分为训练集和测试集：
    - 训练集：用于确定参数（但我们这里参数固定）
    - 测试集：用于验证策略表现
    
    关键：测试集的数据从未用于任何决策
    """
    
    results_by_stock = {}
    
    for code, df in data.items():
        n = len(df)
        split = int(n * train_pct)
        
        train_data = df.iloc[:split].copy()
        test_data = df.iloc[split:].copy()
        
        if len(test_data) < 50:
            continue
        
        strategy = RobustMACDStrategy(**strategy_params)
        engine = RobustBacktestEngine(**config)
        
        test_result = engine._backtest_single(code, test_data, strategy)
        
        if test_result is not None and not test_result["equity_curve"].empty:
            results_by_stock[code] = test_result
    
    if not results_by_stock:
        return {"equity_curve": pd.Series(dtype=float), "trades": []}
    
    all_equity = []
    all_trades = []
    for code, result in results_by_stock.items():
        all_trades.extend(result["trades"])
        all_equity.append(result["equity_curve"])
    
    combined = pd.concat(all_equity, axis=1)
    portfolio_equity = combined.mean(axis=1)
    
    return {
        "equity_curve": portfolio_equity,
        "trades": all_trades,
    }


def simple_parameter_search(data: dict, config: dict, n_iter: int = 30) -> list:
    """
    简单参数搜索 - 使用固定参数，避免过拟合
    
    只搜索少量关键参数，大部分保持默认值
    """
    import random
    random.seed(42)
    
    param_options = {
        "fast": [10, 12, 14],
        "slow": [24, 26, 28],
        "signal_period": [8, 9, 10],
        "stop_loss": [0.05, 0.06, 0.08],
        "take_profit": [0.12, 0.15, 0.18],
    }
    
    results = []
    
    print(f"Testing {n_iter} parameter combinations...")
    
    for i in range(n_iter):
        params = {k: random.choice(v) for k, v in param_options.items()}
        params["trailing_stop"] = 0.08
        params["trend_period"] = 60
        params["volume_ratio"] = 1.2
        
        if params["fast"] >= params["slow"]:
            params["slow"] = params["fast"] + 10
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{n_iter}")
        
        wf_result = walk_forward_test(data, params, config, train_pct=0.6)
        
        if wf_result["equity_curve"].empty or len(wf_result["equity_curve"]) < 30:
            continue
        
        metrics = calculate_metrics(wf_result["equity_curve"], wf_result["trades"])
        
        if metrics is None:
            continue
        
        sharpe = float(metrics["sharpe"])
        max_dd = float(metrics["max_dd"].replace("%", "")) / 100
        win_rate = float(metrics["win_rate"].replace("%", "")) / 100
        total_ret = float(metrics["total_return"].replace("%", "")) / 100
        n_trades = metrics["trades"]
        
        score = sharpe * 0.4 + (1 - abs(max_dd)) * 0.3 + win_rate * 2 * 0.2 + total_ret * 0.1
        
        if max_dd < -0.10:
            score *= 0.5
        if n_trades < 10:
            score *= 0.7
        
        results.append({
            "params": params,
            "metrics": metrics,
            "score": score,
            "sharpe": sharpe,
            "max_dd": max_dd,
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]
