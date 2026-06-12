import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime


def test_notification():
    """测试通知功能"""
    print("=" * 60)
    print("  Testing Notification System")
    print("=" * 60)
    
    config_file = "notify_config.json"
    
    if not os.path.exists(config_file):
        print("\nCreating notify_config.json...")
        config = {
            "wechat_webhook": "",
            "enabled": False
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print("  Created. Please fill in your webhook.")
        return
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    print(f"\nCurrent config:")
    print(f"  WeChat webhook: {config.get('wechat_webhook', 'NOT SET')}")
    print(f"  Enabled: {config.get('enabled', False)}")
    
    if not config.get("wechat_webhook"):
        print("\n  Please set your WeChat webhook in notify_config.json")
        print("  Then run this script again.")
        return
    
    print("\nSending test notification...")
    
    try:
        import urllib.request
        data = {
            "msgtype": "text",
            "text": {
                "content": f"量化系统测试通知\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n状态: 系统正常运行"
            }
        }
        
        req = urllib.request.Request(
            config["wechat_webhook"],
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req)
        print("  Notification sent successfully!")
    except Exception as e:
        print(f"  Failed: {e}")


def test_broker():
    """测试券商连接"""
    print("\n" + "=" * 60)
    print("  Testing Broker Connection")
    print("=" * 60)
    
    config_file = "broker_config.json"
    
    if not os.path.exists(config_file):
        print("\nCreating broker_config.json...")
        config = {
            "broker": "simulated",
            "account": "",
            "password": "",
            "qmt_path": ""
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print("  Created.")
    
    from trading_integration import BrokerAPI
    
    broker = BrokerAPI(broker="simulated")
    broker.connect()
    
    account = broker.get_account_info()
    print(f"\n  Account Info:")
    print(f"    Total Asset: {account['total_asset']:,.0f}")
    print(f"    Cash: {account['cash']:,.0f}")
    print(f"    Market Value: {account['market_value']:,.0f}")
    
    print("\n  Broker test passed!")


def setup_now():
    """立即配置"""
    print("=" * 60)
    print("  Quick Setup")
    print("=" * 60)
    
    print("\nPlease provide your WeChat webhook URL:")
    print("(Get it from: 企业微信群 → 右上角 → 群机器人 → 添加机器人)")
    print("\nPaste your webhook URL here (or press Enter to skip):")
    
    webhook = input("> ").strip()
    
    config = {
        "wechat_webhook": webhook,
        "enabled": bool(webhook)
    }
    
    with open("notify_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    
    if webhook:
        print("\nTesting notification...")
        test_notification()
    else:
        print("\nSkipped. You can configure later.")
    
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. python test_notify.py  - Test notification")
    print("2. python trading_system.py --mode full  - Run system")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_now()
    elif len(sys.argv) > 1 and sys.argv[1] == "broker":
        test_broker()
    else:
        test_notification()
