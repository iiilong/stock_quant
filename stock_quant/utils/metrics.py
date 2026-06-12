import pandas as pd
import numpy as np


def total_return(equity_curve: pd.Series) -> float:
    return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1


def annual_return(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
    total_days = len(equity_curve)
    total_ret = total_return(equity_curve)
    return (1 + total_ret) ** (periods_per_year / total_days) - 1


def annual_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    return returns.std() * np.sqrt(periods_per_year)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03,
                 periods_per_year: int = 252) -> float:
    excess = returns.mean() * periods_per_year - risk_free_rate
    vol = annual_volatility(returns)
    return excess / vol if vol > 0 else 0


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.03,
                  periods_per_year: int = 252) -> float:
    excess = returns.mean() * periods_per_year - risk_free_rate
    downside = returns[returns < 0].std() * np.sqrt(periods_per_year)
    return excess / downside if downside > 0 else 0


def max_drawdown(equity_curve: pd.Series) -> float:
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()


def max_drawdown_duration(equity_curve: pd.Series) -> int:
    peak = equity_curve.cummax()
    is_dd = equity_curve < peak
    durations = []
    count = 0
    for val in is_dd:
        if val:
            count += 1
        else:
            if count > 0:
                durations.append(count)
            count = 0
    if count > 0:
        durations.append(count)
    return max(durations) if durations else 0


def calmar_ratio(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
    ann_ret = annual_return(equity_curve, periods_per_year)
    mdd = abs(max_drawdown(equity_curve))
    return ann_ret / mdd if mdd > 0 else 0


def profit_factor(returns: pd.Series) -> float:
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    return gains / losses if losses > 0 else float('inf')


def win_rate(returns: pd.Series) -> float:
    wins = (returns > 0).sum()
    total = (returns != 0).sum()
    return wins / total if total > 0 else 0


def avg_win_loss(returns: pd.Series) -> tuple:
    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = returns[returns < 0].mean() if (returns < 0).any() else 0
    return avg_win, avg_loss


def sharpe_ratio_rolling(returns: pd.Series, window: int = 60,
                         risk_free_rate: float = 0.03) -> pd.Series:
    excess = returns - risk_free_rate / 252
    return np.sqrt(252) * excess.rolling(window).mean() / excess.rolling(window).std()


def calculate_all_metrics(equity_curve: pd.Series, trades: list = None) -> dict:
    returns = equity_curve.pct_change().dropna()
    metrics = {
        "total_return": f"{total_return(equity_curve):.2%}",
        "ann_return": f"{annual_return(equity_curve):.2%}",
        "ann_volatility": f"{annual_volatility(returns):.2%}",
        "sharpe": f"{sharpe_ratio(returns):.3f}",
        "sortino": f"{sortino_ratio(returns):.3f}",
        "max_dd": f"{max_drawdown(equity_curve):.2%}",
        "max_dd_days": max_drawdown_duration(equity_curve),
        "calmar": f"{calmar_ratio(equity_curve):.3f}",
        "profit_factor": f"{profit_factor(returns):.3f}",
        "win_rate": f"{win_rate(returns):.2%}",
    }
    avg_win, avg_loss = avg_win_loss(returns)
    metrics["avg_win"] = f"{avg_win:.4f}"
    metrics["avg_loss"] = f"{avg_loss:.4f}"

    if trades:
        metrics["trades"] = len(trades)
        winning = [t for t in trades if t.get("pnl", 0) > 0]
        metrics["winning_trades"] = len(winning)
        metrics["losing_trades"] = len(trades) - len(winning)

    return metrics
