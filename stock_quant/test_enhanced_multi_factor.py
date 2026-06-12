import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.enhanced_multi_factor import (
    EnhancedMultiFactorStrategy, EnhancedBacktestEngine, calculate_metrics
)


def main():
    print("=" * 70)
    print("  Enhanced Multi-Factor Strategy")
    print("  (Value + Momentum + Low Vol + Trend + Money Flow)")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print(f"  Top N: 10 stocks")
    print("=" * 70)

    subset_codes = stock_pool.codes[:50]
    
    strategy = EnhancedMultiFactorStrategy(top_n=10, rebalance_days=20)
    
    engine = EnhancedBacktestEngine(
        initial_capital=bt_config.initial_capital,
        commission_rate=bt_config.commission_rate,
        stamp_tax_rate=bt_config.stamp_tax_rate,
        slippage=bt_config.slippage
    )
    
    print("\nRunning enhanced multi-factor strategy...")
    result = engine.run(subset_codes, strategy)
    
    if result["equity_curve"].empty:
        print("\nERROR: No valid results")
        return
    
    metrics = calculate_metrics(result["portfolio_value"], bt_config.initial_capital)
    
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
        print(f"  {'Code':<10} {'Score':>8} {'PE':>8} {'Mom20':>10} {'Flow%':>8} {'Trend':>8}")
        print(f"  {'-'*60}")
        for _, row in top10.iterrows():
            pe_str = f"{row['pe']:.1f}" if row['pe'] is not None and row['pe'] > 0 else "N/A"
            print(f"  {row['code']:<10} {row['total_score']:>8.4f} {pe_str:>8} {row['mom_20']:>10.1f}% {row['main_net_pct']:>8.1f}% {row['trend_score']:>8.0f}")
    
    output_dir = "output_enhanced_multi_factor"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")
    
    print(f"\n  Strategy Logic (7 Factors):")
    print(f"    1. Value Factor (15%): Low PE + Low PB")
    print(f"    2. Momentum Factor (25%): 20/60 day momentum")
    print(f"    3. Reversal Factor (10%): 5 day mean reversion")
    print(f"    4. Low Volatility Factor (15%): Lower risk")
    print(f"    5. Volume Factor (10%): Volume expansion")
    print(f"    6. Trend Factor (15%): MA alignment")
    print(f"    7. Money Flow Factor (10%): Main fund inflow")
    print(f"\n  Equal weight portfolio, 10 stocks")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
