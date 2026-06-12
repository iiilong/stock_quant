import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, strategy_config, stock_pool
from data.fetcher import DataFetcher
from strategies.enhanced_macd import (
    EnhancedMACDStrategy, EnhancedBacktestEngine,
    optimize_macd_params, calculate_sharpe, calculate_max_dd, calculate_calmar
)
from engine.visualization import (
    plot_equity_curve, plot_monthly_returns,
    plot_trade_analysis, plot_strategy_comparison
)
from utils.metrics import calculate_all_metrics


def run_optimized_strategy(data, best_params, config):
    strategy = EnhancedMACDStrategy(**best_params)
    engine = EnhancedBacktestEngine(config)
    results = engine.run(data, strategy)
    aggregated = engine.aggregate_results(results)
    return aggregated, strategy


def main():
    print("=" * 70)
    print("  MACD Strategy Optimization")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Period: {bt_config.start_date} - {bt_config.end_date}")
    print("=" * 70)

    fetcher = DataFetcher(cache_dir="cache")

    print("\nFetching stock data (using top 20 stocks for optimization)...")
    subset_codes = stock_pool.codes[:20]
    data = fetcher.batch_get_stock_data(
        subset_codes,
        bt_config.start_date,
        bt_config.end_date,
        sleep=0.3
    )

    if not data:
        print("ERROR: No data fetched.")
        return

    print(f"Fetched {len(data)} stocks")

    print("\nOptimizing MACD parameters...")
    print("-" * 70)

    top_results = optimize_macd_params(data, bt_config, n_iter=50)

    if not top_results:
        print("No valid parameter combinations found.")
        return

    print("\n" + "=" * 70)
    print("  Top 10 Parameter Combinations")
    print("=" * 70)

    for i, result in enumerate(top_results):
        p = result["params"]
        print(f"\n  Rank #{i+1} (Score: {result['score']:.4f})")
        print(f"    MACD: fast={p['fast']}, slow={p['slow']}, signal={p['signal']}")
        print(f"    Stop Loss: {p['stop_loss']:.1%}, Take Profit: {p['take_profit']:.1%}")
        print(f"    Trailing Stop: {p['trailing_stop']:.1%}")
        print(f"    Volume Ratio: {p['volume_ratio']:.1f}, RSI: {p['rsi_low']}-{p['rsi_high']}")
        print(f"    Sharpe: {result['sharpe']:.3f}, Max DD: {result['max_dd']:.2%}")
        print(f"    Calmar: {result['calmar']:.3f}, Win Rate: {result['win_rate']:.1%}")
        print(f"    Total Return: {result['total_return']:.2%}, Trades: {result['trades']}")

    best = top_results[0]
    best_params = best["params"]

    output_dir = "output_optimized"
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print("  Running Best Strategy on Full Stock Pool")
    print("=" * 70)

    full_data = fetcher.batch_get_stock_data(
        stock_pool.codes,
        bt_config.start_date,
        bt_config.end_date,
        sleep=0.3
    )

    if not full_data:
        print("ERROR: Could not fetch full stock pool data.")
        return

    aggregated, strategy = run_optimized_strategy(full_data, best_params, bt_config)

    if aggregated["equity_curve"].empty:
        print("No valid trades with best parameters.")
        return

    metrics = calculate_all_metrics(aggregated["equity_curve"], aggregated["trades"])

    print(f"\n--- Optimized MACD Performance (Full Pool) ---")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    plot_equity_curve(
        aggregated["equity_curve"],
        title="Optimized MACD Strategy",
        save_path=os.path.join(output_dir, "equity_curve.png")
    )

    plot_monthly_returns(
        aggregated["equity_curve"],
        save_path=os.path.join(output_dir, "monthly_returns.png")
    )

    plot_trade_analysis(
        aggregated["trades"],
        save_path=os.path.join(output_dir, "trade_analysis.png")
    )

    from engine.backtest import BacktestEngine
    from strategies.strategies import MACDStrategy

    print("\nRunning original MACD for comparison...")
    original_strategy = MACDStrategy(fast=12, slow=26, signal=9)
    original_engine = BacktestEngine(bt_config)
    original_results = original_engine.run(full_data, original_strategy)
    original_aggregated = original_engine.aggregate_results(original_results)

    comparison = {}
    if not original_aggregated["equity_curve"].empty:
        comparison["Original MACD"] = {"equity_curve": original_aggregated["equity_curve"]}
    comparison["Optimized MACD"] = {"equity_curve": aggregated["equity_curve"]}

    if len(comparison) > 1:
        plot_strategy_comparison(
            comparison,
            save_path=os.path.join(output_dir, "comparison.png")
        )

    print(f"\n{'=' * 70}")
    print(f"  Optimization Complete!")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")

    print(f"\n  Best Parameters:")
    print(f"    fast={best_params['fast']}, slow={best_params['slow']}, signal={best_params['signal']}")
    print(f"    stop_loss={best_params['stop_loss']:.1%}, take_profit={best_params['take_profit']:.1%}")
    print(f"    trailing_stop={best_params['trailing_stop']:.1%}")
    print(f"    volume_ratio={best_params['volume_ratio']:.1f}")
    print(f"    rsi_low={best_params['rsi_low']}, rsi_high={best_params['rsi_high']}")

    print(f"\n  Optimized Performance:")
    print(f"    Sharpe: {best['sharpe']:.3f}")
    print(f"    Max DD: {best['max_dd']:.2%}")
    print(f"    Calmar: {best['calmar']:.3f}")
    print(f"    Win Rate: {best['win_rate']:.1%}")
    print(f"    Total Return: {best['total_return']:.2%}")
    print(f"    Trades: {best['trades']}")

    if not original_aggregated["equity_curve"].empty:
        orig_sharpe = calculate_sharpe(original_aggregated["equity_curve"])
        orig_dd = calculate_max_dd(original_aggregated["equity_curve"])
        print(f"\n  Improvement over Original:")
        print(f"    Sharpe: {orig_sharpe:.3f} -> {best['sharpe']:.3f}")
        print(f"    Max DD: {orig_dd:.2%} -> {best['max_dd']:.2%}")

    print(f"\n  NOTE: Optimized parameters may overfit. Validate on out-of-sample data.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
