import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.multi_factor import (
    MultiFactorStrategy, MultiFactorBacktestEngine, calculate_simple_metrics
)
from engine.visualization import plot_equity_curve


def main():
    print("=" * 70)
    print("  Multi-Factor Stock Selection Strategy")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print(f"  Top N: 10 stocks per rebalance")
    print("=" * 70)

    strategy = MultiFactorStrategy(top_n=10, rebalance_days=20)
    
    engine = MultiFactorBacktestEngine(
        initial_capital=bt_config.initial_capital,
        commission_rate=bt_config.commission_rate,
        stamp_tax_rate=bt_config.stamp_tax_rate,
        slippage=bt_config.slippage
    )
    
    print("\nRunning multi-factor strategy...")
    result = engine.run(stock_pool.codes, strategy)
    
    if result["equity_curve"].empty:
        print("\nERROR: No valid results")
        return
    
    metrics = calculate_simple_metrics(result["equity_curve"])
    
    print("\n" + "=" * 70)
    print("  Performance Summary")
    print("=" * 70)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("  Selected Stocks (Latest Rebalance)")
    print("=" * 70)
    
    if "factors" in result:
        factors = result["factors"]
        top10 = factors.nlargest(10, "total_score")
        for _, row in top10.iterrows():
            pe = row.get("市盈率(动态)", "N/A")
            pb = row.get("市净率", "N/A")
            mom60 = row.get("mom60", 0)
            score = row["total_score"]
            print(f"  {row['code']}: score={score:.4f}, PE={pe}, PB={pb}, mom60={mom60:.1f}%")
    
    output_dir = "output_multi_factor"
    os.makedirs(output_dir, exist_ok=True)
    
    plot_equity_curve(
        result["equity_curve"],
        title="Multi-Factor Strategy",
        save_path=os.path.join(output_dir, "equity_curve.png")
    )
    
    print(f"\n{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")
    
    print(f"\n  Strategy Logic:")
    print(f"    1. Value Factor (25%): Low PE + Low PB")
    print(f"    2. Momentum Factor (35%): 20/60 day momentum")
    print(f"    3. Low Volatility Factor (20%): Lower risk")
    print(f"    4. Short-term Momentum (20%): Recent strength")
    print(f"\n  Monthly rebalance, top 10 stocks")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
