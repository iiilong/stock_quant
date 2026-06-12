import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import bt_config, stock_pool
from strategies.full_system import (
    FullMarketScanner, PortfolioMonitor, AutoTrader,
    EnhancedMultiFactorStrategy, Scheduler, create_monthly_report
)
import akshare as ak
from datetime import datetime
import time


def detect_market_regime() -> str:
    """检测大盘趋势"""
    try:
        df = ak.stock_zh_index_daily(symbol=bt_config.benchmark)
        if df is not None and not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            close = df["close"].astype(float)
            
            if len(close) < 60:
                return "neutral"
            
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1]
            current = close.iloc[-1]
            
            if ma20 > ma60 and current > ma5 and current > ma20:
                return "bull"
            elif ma20 < ma60:
                return "bear"
            else:
                return "neutral"
    except Exception:
        pass
    return "neutral"


def run_monthly_selection():
    """执行每月选股"""
    print("\n" + "=" * 60)
    print("  Monthly Stock Selection")
    print("=" * 60)
    
    print("\nDetecting market regime...")
    regime = detect_market_regime()
    print(f"Market Regime: {regime}")
    
    if regime == "bear":
        print("\nBEAR MARKET - Recommend empty position!")
        return {
            "regime": "bear",
            "selected": [],
            "action": "SELL_ALL"
        }
    
    print("\nScanning stocks...")
    scanner = FullMarketScanner()
    all_stocks = scanner.get_all_stocks()
    print(f"Found {len(all_stocks)} stocks")
    
    subset = all_stocks[:100]
    
    strategy = EnhancedMultiFactorStrategy(top_n=5)
    
    print("\nFetching price data...")
    price_data = strategy.get_price_data(subset, days=120)
    print(f"Got data for {len(price_data)} stocks")
    
    print("\nFetching realtime data...")
    realtime = strategy.get_realtime_data(list(price_data.keys()))
    
    print("\nCalculating factors...")
    factors = strategy.calculate_factors(price_data, realtime)
    
    if factors.empty:
        print("ERROR: No valid factors")
        return {"regime": regime, "selected": [], "action": "HOLD"}
    
    selected = strategy.select_stocks(factors)
    
    print(f"\nSelected {len(selected)} stocks:")
    for code in selected:
        row = factors[factors["code"] == code].iloc[0]
        pe = row.get("pe", "N/A")
        pe_str = f"{pe:.1f}" if pe and pe > 0 else "N/A"
        print(f"  {code}: score={row['total_score']:.4f}, PE={pe_str}, "
              f"mom20={row['mom_20']:.1f}%, flow={row['money_flow']:.1f}%")
    
    return {
        "regime": regime,
        "selected": selected,
        "action": "REBALANCE",
        "factors": factors,
    }


def run_portfolio_monitor():
    """运行持仓监控"""
    print("\n" + "=" * 60)
    print("  Portfolio Monitor")
    print("=" * 60)
    
    monitor = PortfolioMonitor()
    summary = monitor.get_summary()
    
    print(f"\nPortfolio Summary:")
    print(f"  Cash: {summary['cash']:,.0f}")
    print(f"  Market Value: {summary['market_value']:,.0f}")
    print(f"  Total Value: {summary['total_value']:,.0f}")
    print(f"  Total PnL: {summary['total_pnl']}")
    
    if summary["holdings"]:
        print(f"\nHoldings:")
        for code, h in summary["holdings"].items():
            print(f"  {code}: {h['shares']} shares @ {h['buy_price']:.2f}")
    else:
        print(f"\nNo holdings")
    
    return summary


def run_full_system():
    """运行完整系统"""
    print("\n" + "=" * 60)
    print("  Full Trading System")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    selection = run_monthly_selection()
    
    summary = run_portfolio_monitor()
    
    if selection["action"] == "SELL_ALL":
        print("\nBear market detected - Suggest selling all positions")
    elif selection["action"] == "REBALANCE":
        print(f"\nRebalance with {len(selection['selected'])} stocks")
    
    report = create_monthly_report(
        PortfolioMonitor(),
        selection.get("selected", []),
        selection.get("regime", "unknown")
    )
    
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"report_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    print(report)
    
    return selection, summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Stock Quant Trading System")
    parser.add_argument("--mode", choices=["select", "monitor", "full"], 
                        default="full", help="Run mode")
    args = parser.parse_args()
    
    if args.mode == "select":
        run_monthly_selection()
    elif args.mode == "monitor":
        run_portfolio_monitor()
    else:
        run_full_system()


if __name__ == "__main__":
    import pandas as pd
    main()
