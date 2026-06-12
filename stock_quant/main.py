import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, strategy_config, stock_pool
from data.fetcher import DataFetcher
from engine.backtest import BacktestEngine
from engine.visualization import (
    plot_equity_curve, plot_monthly_returns,
    plot_trade_analysis, plot_strategy_comparison
)
from utils.metrics import calculate_all_metrics
from strategies.strategies import (
    TrendFollowStrategy, MeanReversionStrategy,
    MomentumStrategy, MACDStrategy, CompositeStrategy
)


def print_metrics(metrics: dict, title: str = "Performance Metrics"):
    print(f"\n--- {title} ---")
    for key, value in metrics.items():
        print(f"  {key}: {value}")


def run_single_strategy(strategy, data: dict, config, strategy_name: str):
    print(f"\nRunning strategy: {strategy_name}")
    engine = BacktestEngine(config)
    results = engine.run(data, strategy)
    aggregated = engine.aggregate_results(results)

    if aggregated["equity_curve"].empty:
        print(f"  Strategy {strategy_name} has no valid trades")
        return None

    metrics = calculate_all_metrics(aggregated["equity_curve"], aggregated["trades"])
    print_metrics(metrics, f"{strategy_name} - Performance Metrics")

    return {
        "strategy": strategy,
        "equity_curve": aggregated["equity_curve"],
        "trades": aggregated["trades"],
        "metrics": metrics,
        "config": config,
    }


def main():
    print("=" * 60)
    print("  A Stock Quant Backtest System")
    print("=" * 60)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Period: {bt_config.start_date} - {bt_config.end_date}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print("=" * 60)

    fetcher = DataFetcher(cache_dir="cache")

    print("\nFetching stock data...")
    data = fetcher.batch_get_stock_data(
        stock_pool.codes,
        bt_config.start_date,
        bt_config.end_date,
        sleep=0.3
    )

    if not data:
        print("ERROR: No data fetched. Check network and stock pool config.")
        return

    print(f"Successfully fetched {len(data)} stocks")

    strategies = [
        ("TrendFollow", TrendFollowStrategy(
            short_window=strategy_config.short_window,
            mid_window=strategy_config.mid_window,
            long_window=strategy_config.long_window
        )),
        ("MeanReversion", MeanReversionStrategy(
            period=strategy_config.bollinger_period,
            std_dev=strategy_config.bollinger_std
        )),
        ("Momentum", MomentumStrategy(
            lookback=strategy_config.momentum_lookback,
            rsi_period=strategy_config.rsi_period
        )),
        ("MACD", MACDStrategy(
            fast=strategy_config.macd_fast,
            slow=strategy_config.macd_slow,
            signal=strategy_config.macd_signal
        )),
        ("Composite", CompositeStrategy()),
    ]

    all_results = {}
    for name, strategy in strategies:
        result = run_single_strategy(strategy, data, bt_config, name)
        if result:
            all_results[name] = result

    if all_results:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        best_name = max(all_results.keys(),
                       key=lambda k: float(all_results[k]["metrics"]["sharpe"].replace("%", "")))
        best = all_results[best_name]

        print(f"\n{'=' * 60}")
        print(f"  Best Strategy: {best_name}")
        print(f"{'=' * 60}")

        plot_equity_curve(
            best["equity_curve"],
            title=f"Best Strategy - {best_name}",
            save_path=os.path.join(output_dir, "equity_curve.png")
        )

        plot_monthly_returns(
            best["equity_curve"],
            save_path=os.path.join(output_dir, "monthly_returns.png")
        )

        plot_trade_analysis(
            best["trades"],
            save_path=os.path.join(output_dir, "trade_analysis.png")
        )

        plot_strategy_comparison(
            {k: {"equity_curve": v["equity_curve"]} for k, v in all_results.items()},
            save_path=os.path.join(output_dir, "strategy_comparison.png")
        )

        print(f"\n--- Strategy Comparison ---")
        print(f"{'Strategy':<15} {'Ann Return':>12} {'Sharpe':>8} {'Max DD':>10} {'Win Rate':>10} {'Trades':>8}")
        print("-" * 70)
        for name, result in all_results.items():
            m = result["metrics"]
            print(f"{name:<15} {m['ann_return']:>12} {m['sharpe']:>8} {m['max_dd']:>10} {m['win_rate']:>10} {str(m.get('trades', 0)):>8}")

        print(f"\n{'=' * 60}")
        print(f"  Backtest Complete!")
        print(f"  Output: {os.path.abspath(output_dir)}")
        print(f"  Best Strategy: {best_name}")
        print(f"  Ann Return: {best['metrics']['ann_return']}")
        print(f"  Sharpe: {best['metrics']['sharpe']}")
        print(f"  Max DD: {best['metrics']['max_dd']}")
        print(f"{'=' * 60}")
        print(f"  NOTE: Past performance does not guarantee future results.")
        print(f"  Invest responsibly!")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
