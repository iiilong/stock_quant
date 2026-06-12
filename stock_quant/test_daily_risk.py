import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.daily_risk import DailyRiskMonitor, create_daily_report


def main():
    print("=" * 60)
    print("  Daily Risk Monitor")
    print("=" * 60)
    
    monitor = DailyRiskMonitor()
    
    result = monitor.run_daily_check()
    
    report = create_daily_report(result)
    print(report)
    
    if result["signals"]:
        print("\nExecute these signals? (y/n)")
        response = input("> ").strip().lower()
        if response == 'y':
            monitor.execute_signals(result["signals"], result["prices"])
            print("Signals executed!")
        else:
            print("Signals not executed")
    else:
        print("No signals to execute")


if __name__ == "__main__":
    main()
