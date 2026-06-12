import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.monthly_backtest import MonthlyRebalanceBacktest, calculate_backtest_metrics
from engine.visualization import plot_equity_curve, plot_monthly_returns


def main():
    print("=" * 70)
    print("  Monthly Rebalance Multi-Factor Backtest")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print(f"  Top N: 10 stocks per rebalance")
    print(f"  Rebalance: Monthly")
    print("=" * 70)

    subset_codes = stock_pool.codes[:50]
    
    engine = MonthlyRebalanceBacktest(
        initial_capital=bt_config.initial_capital,
        top_n=10,
        commission_rate=bt_config.commission_rate,
        stamp_tax_rate=bt_config.stamp_tax_rate,
        slippage=bt_config.slippage
    )
    
    print("\nRunning monthly rebalance backtest...")
    result = engine.run_backtest(
        subset_codes,
        start_date=bt_config.start_date,
        end_date=bt_config.end_date
    )
    
    if result["equity_curve"].empty:
        print("\nERROR: No valid results")
        return
    
    metrics = calculate_backtest_metrics(result["equity_curve"], bt_config.initial_capital)
    
    print("\n" + "=" * 70)
    print("  Backtest Performance")
    print("=" * 70)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print(f"\n  Rebalance Count: {len(result['rebalances'])}")
    print(f"  Total Trades: {len(result['trades'])}")
    
    print("\n" + "=" * 70)
    print("  Latest Holdings")
    print("=" * 70)
    if result["final_holdings"]:
        for code, (shares, buy_price) in result["final_holdings"].items():
            print(f"  {code}: {shares} shares @ {buy_price:.2f}")
    
    print("\n" + "=" * 70)
    print("  Rebalance History (Last 5)")
    print("=" * 70)
    for reb in result["rebalances"][-5:]:
        print(f"  {reb['date'].strftime('%Y-%m-%d')}: {reb['stocks'][:5]}...")
    
    output_dir = "output_monthly_backtest"
    os.makedirs(output_dir, exist_ok=True)
    
    plot_equity_curve(
        result["equity_curve"],
        title="Monthly Rebalance Multi-Factor Strategy",
        save_path=os.path.join(output_dir, "equity_curve.png")
    )
    
    if len(result["equity_curve"]) > 20:
        plot_monthly_returns(
            result["equity_curve"],
            save_path=os.path.join(output_dir, "monthly_returns.png")
        )
    
    print(f"\n{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")
    
    print(f"\n  Strategy Logic:")
    print(f"    1. Monthly rebalance (no lookahead)")
    print(f"    2. Equal weight portfolio")
    print(f"    3. 7-factor model:")
    print(f"       - Value (15%): Low PE")
    print(f"       - Momentum (25%): 20/60 day momentum")
    print(f"       - Reversal (10%): 5 day mean reversion")
    print(f"       - Low Volatility (15%): Lower risk")
    print(f"       - Volume (10%): Volume expansion")
    print(f"       - Trend (15%): MA alignment")
    print(f"       - Money Flow (10%): Main fund inflow")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
