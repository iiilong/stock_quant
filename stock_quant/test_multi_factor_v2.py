import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.multi_factor_v2 import (
    MultiFactorStrategy, MultiFactorBacktestEngine, calculate_metrics
)


def main():
    print("=" * 70)
    print("  Multi-Factor Stock Selection Strategy")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print(f"  Top N: 10 stocks")
    print("=" * 70)

    subset_codes = stock_pool.codes[:50]
    
    strategy = MultiFactorStrategy(top_n=10, rebalance_days=20)
    
    engine = MultiFactorBacktestEngine(
        initial_capital=bt_config.initial_capital,
        commission_rate=bt_config.commission_rate,
        stamp_tax_rate=bt_config.stamp_tax_rate,
        slippage=bt_config.slippage
    )
    
    print("\nRunning multi-factor strategy...")
    result = engine.run(subset_codes, strategy)
    
    if result["equity_curve"].empty:
        print("\nERROR: No valid results")
        return
    
    metrics = calculate_metrics(result["equity_curve"], bt_config.initial_capital)
    
    print("\n" + "=" * 70)
    print("  Performance Summary")
    print("=" * 70)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("  Factor Analysis")
    print("=" * 70)
    
    if "factors" in result:
        factors = result["factors"]
        top10 = factors.nlargest(10, "total_score")
        print(f"\n  Top 10 Stocks by Total Score:")
        print(f"  {'Code':<10} {'Score':>8} {'Mom20':>10} {'Mom60':>10} {'Vol20':>10} {'Trend':>8}")
        print(f"  {'-'*60}")
        for _, row in top10.iterrows():
            print(f"  {row['code']:<10} {row['total_score']:>8.4f} {row['mom_20']:>10.1f}% {row['mom_60']:>10.1f}% {row['vol_20']:>10.1%} {row['trend_score']:>8.0f}")
    
    output_dir = "output_multi_factor"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")
    
    print(f"\n  Strategy Logic:")
    print(f"    1. Momentum Factor (30%): 20/60/120 day momentum")
    print(f"    2. Reversal Factor (15%): 5 day mean reversion")
    print(f"    3. Low Volatility Factor (20%): Lower risk is better")
    print(f"    4. Volume Factor (15%): Volume expansion")
    print(f"    5. Trend Factor (20%): MA alignment")
    print(f"\n  Equal weight portfolio, 10 stocks")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
