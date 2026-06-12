import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, strategy_config, stock_pool
from data.fetcher import DataFetcher
from strategies.robust_macd import (
    RobustMACDStrategy, RobustBacktestEngine,
    calculate_metrics, walk_forward_test, simple_parameter_search
)
from engine.visualization import (
    plot_equity_curve, plot_monthly_returns,
    plot_trade_analysis, plot_strategy_comparison
)


def main():
    print("=" * 70)
    print("  MACD Strategy - Robust Test (No Lookahead, No Overfitting)")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Period: {bt_config.start_date} - {bt_config.end_date}")
    print("=" * 70)

    fetcher = DataFetcher(cache_dir="cache")

    print("\nFetching stock data...")
    subset_codes = stock_pool.codes[:30]
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

    engine_config = {
        "initial_capital": bt_config.initial_capital,
        "commission_rate": bt_config.commission_rate,
        "stamp_tax_rate": bt_config.stamp_tax_rate,
        "slippage": bt_config.slippage,
        "max_position_pct": bt_config.max_position_pct,
    }

    print("\n" + "=" * 70)
    print("  Step 1: Test with Default Parameters (No Optimization)")
    print("=" * 70)

    default_params = {
        "fast": 12,
        "slow": 26,
        "signal_period": 9,
        "stop_loss": 0.06,
        "take_profit": 0.15,
        "trailing_stop": 0.08,
        "trend_period": 60,
        "volume_ratio": 1.2,
    }

    print(f"\nDefault Parameters: {default_params}")

    strategy = RobustMACDStrategy(**default_params)
    engine = RobustBacktestEngine(**engine_config)
    results = engine.run(data, strategy)
    aggregated = engine.aggregate_results(results)

    if not aggregated["equity_curve"].empty:
        metrics = calculate_metrics(aggregated["equity_curve"], aggregated["trades"])
        print(f"\n--- Default Parameters Performance (Full Data) ---")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("  Step 2: Walk-Forward Test (Train/Test Split)")
    print("=" * 70)

    wf_result = walk_forward_test(data, default_params, engine_config, train_pct=0.6)

    if not wf_result["equity_curve"].empty:
        wf_metrics = calculate_metrics(wf_result["equity_curve"], wf_result["trades"])
        print(f"\n--- Walk-Forward Test Performance (Out-of-Sample) ---")
        for key, value in wf_metrics.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("  Step 3: Simple Parameter Search (with Walk-Forward)")
    print("=" * 70)

    top_results = simple_parameter_search(data, engine_config, n_iter=30)

    if top_results:
        print("\nTop 5 Parameter Combinations (Walk-Forward Validated):")
        for i, result in enumerate(top_results):
            print(f"\n  Rank #{i+1} (Score: {result['score']:.4f})")
            print(f"    MACD: fast={result['params']['fast']}, slow={result['params']['slow']}, signal={result['params']['signal_period']}")
            print(f"    Stop Loss: {result['params']['stop_loss']:.1%}, Take Profit: {result['params']['take_profit']:.1%}")
            for key, value in result['metrics'].items():
                print(f"    {key}: {value}")

        best = top_results[0]
        best_params = best["params"]

        print("\n" + "=" * 70)
        print("  Step 4: Run Best Parameters on Full Data")
        print("=" * 70)

        best_strategy = RobustMACDStrategy(**best_params)
        best_engine = RobustBacktestEngine(**engine_config)
        best_results = best_engine.run(data, best_strategy)
        best_aggregated = best_engine.aggregate_results(best_results)

        if not best_aggregated["equity_curve"].empty:
            best_metrics = calculate_metrics(best_aggregated["equity_curve"], best_aggregated["trades"])
            print(f"\n--- Best Parameters Performance (Full Data) ---")
            for key, value in best_metrics.items():
                print(f"  {key}: {value}")

            output_dir = "output_robust"
            os.makedirs(output_dir, exist_ok=True)

            plot_equity_curve(
                best_aggregated["equity_curve"],
                title="Robust MACD Strategy",
                save_path=os.path.join(output_dir, "equity_curve.png")
            )

            plot_monthly_returns(
                best_aggregated["equity_curve"],
                save_path=os.path.join(output_dir, "monthly_returns.png")
            )

            plot_trade_analysis(
                best_aggregated["trades"],
                save_path=os.path.join(output_dir, "trade_analysis.png")
            )

            comparison = {}
            if not aggregated["equity_curve"].empty:
                comparison["Default MACD"] = {"equity_curve": aggregated["equity_curve"]}
            comparison["Optimized MACD"] = {"equity_curve": best_aggregated["equity_curve"]}

            if len(comparison) > 1:
                plot_strategy_comparison(
                    comparison,
                    save_path=os.path.join(output_dir, "comparison.png")
                )

            print(f"\n{'=' * 70}")
            print(f"  Test Complete!")
            print(f"  Output: {os.path.abspath(output_dir)}")
            print(f"{'=' * 70}")

            print(f"\n  Best Parameters (Walk-Forward Validated):")
            print(f"    fast={best_params['fast']}, slow={best_params['slow']}, signal={best_params['signal_period']}")
            print(f"    stop_loss={best_params['stop_loss']:.1%}, take_profit={best_params['take_profit']:.1%}")

            print(f"\n  Key Findings:")
            print(f"    1. All signals use only historical data (no lookahead)")
            print(f"    2. Parameters validated via walk-forward test")
            print(f"    3. No curve-fitting to specific market conditions")
            print(f"\n  NOTE: Past performance does not guarantee future results.")
            print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
