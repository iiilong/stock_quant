import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from strategies.robust_scheduler import (
    RobustScheduler, RobustOrderExecutor, PositionManager, RiskMonitor,
    create_robust_monthly_report
)


def main():
    print("=" * 70)
    print("  Robust Monthly Rebalance System")
    print("=" * 70)
    
    scheduler = RobustScheduler()
    
    today = datetime.now()
    print(f"\nCurrent Date: {today.strftime('%Y-%m-%d')}")
    
    last_trade_date = scheduler.get_last_trade_date(today)
    next_trade_date = scheduler.get_next_trade_date(today)
    month_start = scheduler.get_month_start_trade_date(today.year, today.month)
    month_end = scheduler.get_month_end_trade_date(today.year, today.month)
    
    print(f"\nTrading Calendar:")
    print(f"  Last Trade Date: {last_trade_date.strftime('%Y-%m-%d')}")
    print(f"  Next Trade Date: {next_trade_date.strftime('%Y-%m-%d')}")
    print(f"  Month Start: {month_start.strftime('%Y-%m-%d')}")
    print(f"  Month End: {month_end.strftime('%Y-%m-%d')}")
    
    should_rebalance = scheduler.should_rebalance(today)
    print(f"\nShould Rebalance Today: {should_rebalance}")
    
    print(f"\nRecommended Execution Timeline:")
    print(f"  1. {month_end.strftime('%Y-%m-%d')} (Month End): Run stock selection")
    print(f"  2. {month_start.strftime('%Y-%m-%d')} (Month Start): Execute trades")
    print(f"  3. {scheduler.get_next_trade_date(month_start).strftime('%Y-%m-%d')}: Verify execution")
    
    executor = RobustOrderExecutor(slippage=0.002, max_slippage=0.03)
    
    print(f"\nOrder Execution Rules:")
    print(f"  - Slippage: 0.2%")
    print(f"  - Max Slippage: 3%")
    print(f"  - Check limit up/down before execution")
    print(f"  - Check volume for liquidity")
    
    position_mgr = PositionManager(
        max_positions=5,
        max_position_pct=0.20,
        min_position_pct=0.10,
        cash_reserve_pct=0.10
    )
    
    print(f"\nPosition Management Rules:")
    print(f"  - Max Positions: 5")
    print(f"  - Max Position Size: 20%")
    print(f"  - Min Position Size: 10%")
    print(f"  - Cash Reserve: 10%")
    
    risk_monitor = RiskMonitor(
        max_drawdown=0.15,
        max_single_loss=0.08,
        max_sector_exposure=0.40
    )
    
    print(f"\nRisk Management Rules:")
    print(f"  - Max Drawdown: 15%")
    print(f"  - Stop Loss: 8% per position")
    print(f"  - Max Sector Exposure: 40%")
    
    print(f"\n" + "=" * 70)
    print(f"  How to Use")
    print(f"{'=' * 70}")
    print(f"""
1. Monthly Selection (Run on month end):
   python trading_system.py --mode select

2. Monthly Execution (Run on month start):
   python trading_system.py --mode monitor

3. Check Portfolio Anytime:
   python trading_system.py --mode monitor

4. Full System (Auto-detect timing):
   python trading_system.py --mode full
""")
    
    print(f"Key Dates Each Month:")
    print(f"  - {month_end.strftime('%d')}th: Selection day")
    print(f"  - {month_start.strftime('%d')}th: Execution day")
    print(f"  - {scheduler.get_next_trade_date(month_start).strftime('%d')}th: Verification day")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
