import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_equity_curve(equity_curve: pd.Series, benchmark: pd.Series = None,
                      title: str = "Equity Curve", save_path: str = None):
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])

    ax1 = axes[0]
    normalized = equity_curve / equity_curve.iloc[0]
    ax1.plot(normalized.index, normalized.values, label="Strategy", color="#2196F3", linewidth=2)

    if benchmark is not None:
        bench_normalized = benchmark / benchmark.iloc[0]
        ax1.plot(bench_normalized.index, bench_normalized.values,
                 label="Benchmark (CSI300)", color="#FF9800", linewidth=1.5, linestyle="--")

    ax1.set_title(title, fontsize=16, fontweight="bold")
    ax1.set_ylabel("Net Value", fontsize=12)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    drawdown = (equity_curve - equity_curve.cummax()) / equity_curve.cummax()
    ax2.fill_between(drawdown.index, drawdown.values, 0, color="#F44336", alpha=0.5)
    ax2.set_ylabel("Drawdown", fontsize=12)
    ax2.set_xlabel("Date", fontsize=12)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return fig


def plot_monthly_returns(equity_curve: pd.Series, save_path: str = None):
    monthly = equity_curve.resample('ME').last()
    monthly_returns = monthly.pct_change().dropna()
    monthly_returns.index = monthly_returns.index.to_period('M')

    returns_matrix = monthly_returns.groupby([monthly_returns.index.year, monthly_returns.index.month]).first()
    returns_matrix = returns_matrix.unstack()

    fig, ax = plt.subplots(figsize=(14, 6))
    returns_matrix.plot(kind='bar', ax=ax, colormap='RdYlGn')
    ax.set_title("Monthly Returns", fontsize=16, fontweight="bold")
    ax.set_ylabel("Return", fontsize=12)
    ax.legend(title="Month", fontsize=10)
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return fig


def plot_trade_analysis(trades: list, save_path: str = None):
    if not trades:
        return None

    pnls = [t["pnl_pct"] for t in trades]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ax1 = axes[0]
    colors = ["#4CAF50" if p > 0 else "#F44336" for p in pnls]
    ax1.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
    ax1.axhline(y=0, color='black', linewidth=0.5)
    ax1.set_title("Trade P&L", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Trade #", fontsize=12)
    ax1.set_ylabel("Return", fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')

    ax2 = axes[1]
    cum_pnl = pd.Series(pnls).cumsum()
    ax2.plot(range(len(cum_pnl)), cum_pnl.values, color="#2196F3", linewidth=2)
    ax2.fill_between(range(len(cum_pnl)), cum_pnl.values, 0,
                     where=cum_pnl.values >= 0, color="#4CAF50", alpha=0.3)
    ax2.fill_between(range(len(cum_pnl)), cum_pnl.values, 0,
                     where=cum_pnl.values < 0, color="#F44336", alpha=0.3)
    ax2.set_title("Cumulative Returns", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Trade #", fontsize=12)
    ax2.set_ylabel("Cumulative Return", fontsize=12)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return fig


def plot_strategy_comparison(results_dict: dict, save_path: str = None):
    fig, ax = plt.subplots(figsize=(14, 8))

    colors = ["#2196F3", "#FF9800", "#4CAF50", "#F44336", "#9C27B0"]
    for i, (name, result) in enumerate(results_dict.items()):
        eq = result["equity_curve"]
        normalized = eq / eq.iloc[0]
        color = colors[i % len(colors)]
        ax.plot(normalized.index, normalized.values, label=name,
                color=color, linewidth=2)

    ax.set_title("Strategy Comparison", fontsize=16, fontweight="bold")
    ax.set_ylabel("Net Value", fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return fig
