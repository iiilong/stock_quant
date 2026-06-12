import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.optimized import OptimizedBacktest, calculate_metrics
from engine.visualization import plot_equity_curve


def main():
    print("=" * 70)
    print("  Optimized Multi-Factor Strategy")
    print("  (Market Regime + Risk Control + Position Management)")
    print("=" * 70)
    print(f"  Initial Capital: {bt_config.initial_capital:,.0f}")
    print(f"  Stock Pool: {len(stock_pool.codes)} stocks")
    print(f"  Top N: 5 stocks (max 20% per stock)")
    print(f"  Stop Loss: 8% per position")
    print(f"  Max Drawdown: 15% (pause trading)")
    print(f"  Market Filter: Bear market = empty position")
    print("=" * 70)

    subset_codes = stock_pool.codes[:50]
    
    engine = OptimizedBacktest(
        initial_capital=bt_config.initial_capital,
        top_n=5,
        max_position_pct=0.20,
        stop_loss_pct=0.08,
        max_drawdown_pct=0.15,
        commission_rate=bt_config.commission_rate,
        stamp_tax_rate=bt_config.stamp_tax_rate,
        slippage=bt_config.slippage
    )
    
    print("\nRunning optimized backtest...")
    result = engine.run(
        subset_codes,
        market_index=bt_config.benchmark,
        start_date=bt_config.start_date,
        end_date=bt_config.end_date
    )
    
    if result["equity_curve"].empty:
        print("\nERROR: No valid results")
        return
    
    metrics = calculate_metrics(result["equity_curve"], bt_config.initial_capital)
    
    print("\n" + "=" * 70)
    print("  Backtest Performance")
    print("=" * 70)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print(f"\n  Rebalance Count: {len(result['rebalances'])}")
    print(f"  Total Trades: {len(result['trades'])}")
    
    sell_trades = [t for t in result['trades'] if t['action'] == 'SELL']
    bear_sells = sum(1 for t in sell_trades if t['reason'] == 'bear_market')
    stop_loss_sells = sum(1 for t in sell_trades if t['reason'] == 'stop_loss')
    dd_sells = sum(1 for t in sell_trades if t['reason'] == 'max_drawdown')
    rebalance_sells = sum(1 for t in sell_trades if t['reason'] == 'rebalance')
    
    print(f"\n  Sell Reasons:")
    print(f"    Bear Market: {bear_sells}")
    print(f"    Stop Loss: {stop_loss_sells}")
    print(f"    Max Drawdown: {dd_sells}")
    print(f"    Rebalance: {rebalance_sells}")
    
    print("\n" + "=" * 70)
    print("  Market Regime Analysis")
    print("=" * 70)
    regime_counts = {}
    for reb in result['rebalances']:
        regime = reb['market_regime']
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
    for regime, count in regime_counts.items():
        print(f"  {regime}: {count} months")
    
    print("\n" + "=" * 70)
    print("  Latest Holdings")
    print("=" * 70)
    if result["final_holdings"]:
        for code, (shares, buy_price, buy_date) in result["final_holdings"].items():
            print(f"  {code}: {shares} shares @ {buy_price:.2f} (bought {buy_date.strftime('%Y-%m-%d')})")
    else:
        print("  No holdings (cash)")
    
    output_dir = "output_optimized"
    os.makedirs(output_dir, exist_ok=True)
    
    plot_equity_curve(
        result["equity_curve"],
        title="Optimized Multi-Factor Strategy",
        save_path=os.path.join(output_dir, "equity_curve.png")
    )
    
    print(f"\n{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_dir)}")
    print(f"{'=' * 70}")
    
    print(f"\n  Strategy Features:")
    print(f"    1. Market Regime Filter: Empty position in bear market")
    print(f"    2. Position Limit: Max 5 stocks, 20% per stock")
    print(f"    3. Stop Loss: 8% per position")
    print(f"    4. Max Drawdown Control: 15% pause trading")
    print(f"    5. 7-Factor Model with equal weight")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
