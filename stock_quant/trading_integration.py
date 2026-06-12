import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from strategies.daily_risk import DailyRiskMonitor
from strategies.robust_scheduler import RobustScheduler
import json


class TaskScheduler:
    """Windows任务计划程序配置器"""
    
    def __init__(self):
        self.batch_dir = "scheduler"
        os.makedirs(self.batch_dir, exist_ok=True)
    
    def create_daily_risk_task(self):
        """创建每日风控检查任务"""
        bat_content = f'''@echo off
cd /d {os.getcwd()}
python test_daily_risk.py >> logs/daily_risk.log 2>&1
'''
        bat_file = os.path.join(self.batch_dir, "daily_risk.bat")
        with open(bat_file, 'w', encoding='gbk') as f:
            f.write(bat_content)
        
        ps1_content = f'''# 创建每日风控检查任务（每个交易日15:30运行）
$taskName = "StockQuant_DailyRisk"
$taskPath = "{os.path.abspath(bat_file)}"
$trigger = New-ScheduledTaskTrigger -Daily -At "15:30"
$action = New-ScheduledTaskAction -Execute $taskPath
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Force
Write-Host "Created daily risk task: $taskName"
'''
        ps1_file = os.path.join(self.batch_dir, "create_daily_task.ps1")
        with open(ps1_file, 'w', encoding='utf-8') as f:
            f.write(ps1_content)
        
        return ps1_file
    
    def create_monthly_selection_task(self):
        """创建每月选股任务"""
        bat_content = f'''@echo off
cd /d {os.getcwd()}
python trading_system.py --mode select >> logs/monthly_selection.log 2>&1
'''
        bat_file = os.path.join(self.batch_dir, "monthly_selection.bat")
        with open(bat_file, 'w', encoding='gbk') as f:
            f.write(bat_content)
        
        ps1_content = f'''# 创建每月选股任务（每月最后一天17:00运行）
$taskName = "StockQuant_MonthlySelection"
$taskPath = "{os.path.abspath(bat_file)}"
$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 28 -At "17:00"
$action = New-ScheduledTaskAction -Execute $taskPath
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Force
Write-Host "Created monthly selection task: $taskName"
'''
        ps1_file = os.path.join(self.batch_dir, "create_monthly_task.ps1")
        with open(ps1_file, 'w', encoding='utf-8') as f:
            f.write(ps1_content)
        
        return ps1_file
    
    def create_monthly_execution_task(self):
        """创建每月执行任务"""
        bat_content = f'''@echo off
cd /d {os.getcwd()}
python trading_system.py --mode full >> logs/monthly_execution.log 2>&1
'''
        bat_file = os.path.join(self.batch_dir, "monthly_execution.bat")
        with open(bat_file, 'w', encoding='gbk') as f:
            f.write(bat_content)
        
        ps1_content = f'''# 创建每月执行任务（每月1日9:35运行）
$taskName = "StockQuant_MonthlyExecution"
$taskPath = "{os.path.abspath(bat_file)}"
$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1 -At "09:35"
$action = New-ScheduledTaskAction -Execute $taskPath
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Force
Write-Host "Created monthly execution task: $taskName"
'''
        ps1_file = os.path.join(self.batch_dir, "create_execution_task.ps1")
        with open(ps1_file, 'w', encoding='utf-8') as f:
            f.write(ps1_content)
        
        return ps1_file
    
    def create_all_tasks(self):
        """创建所有定时任务"""
        os.makedirs("logs", exist_ok=True)
        
        files = []
        files.append(self.create_daily_risk_task())
        files.append(self.create_monthly_selection_task())
        files.append(self.create_monthly_execution_task())
        
        readme = f"""
========================================
  定时任务配置说明
========================================

请以管理员身份运行PowerShell，然后执行以下命令：

1. 创建每日风控任务:
   ./{files[0]}

2. 创建每月选股任务:
   ./{files[1]}

3. 创建每月执行任务:
   ./{files[2]}

或者运行 setup_scheduler.bat 一键配置

任务说明:
- StockQuant_DailyRisk: 每日15:30运行风控检查
- StockQuant_MonthlySelection: 每月28日17:00运行选股
- StockQuant_MonthlyExecution: 每月1日9:35运行交易

日志目录: logs/
========================================
"""
        readme_file = os.path.join(self.batch_dir, "README.txt")
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        
        setup_bat = f'''@echo off
echo Setting up scheduled tasks...
echo.
echo Please run PowerShell as Administrator, then execute:
echo   .\\scheduler\\create_daily_task.ps1
echo   .\\scheduler\\create_monthly_task.ps1  
echo   .\\scheduler\\create_execution_task.ps1
echo.
pause
'''
        setup_file = os.path.join(self.batch_dir, "setup_scheduler.bat")
        with open(setup_file, 'w', encoding='gbk') as f:
            f.write(setup_bat)
        
        print(f"\nCreated scheduler files in {self.batch_dir}/:")
        for f in files:
            print(f"  {f}")
        
        return files


class Notifier:
    """通知器"""
    
    def __init__(self, config_file: str = "notify_config.json"):
        self.config = self._load_config(config_file)
    
    def _load_config(self, config_file: str) -> dict:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "wechat_webhook": "",
            "email": "",
            "sms_phone": "",
            "enabled": False
        }
    
    def send_wechat(self, title: str, content: str) -> bool:
        """发送微信通知（通过企业微信机器人）"""
        import urllib.request
        
        webhook = self.config.get("wechat_webhook", "")
        if not webhook:
            print("  WeChat webhook not configured")
            return False
        
        data = {
            "msgtype": "text",
            "text": {
                "content": f"{title}\n\n{content}"
            }
        }
        
        try:
            req = urllib.request.Request(
                webhook,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
            print("  WeChat notification sent")
            return True
        except Exception as e:
            print(f"  WeChat notification failed: {e}")
            return False
    
    def send_email(self, subject: str, body: str) -> bool:
        """发送邮件通知"""
        import smtplib
        from email.mime.text import MIMEText
        
        email = self.config.get("email", "")
        if not email:
            print("  Email not configured")
            return False
        
        print(f"  Email notification would be sent to: {email}")
        print(f"  Subject: {subject}")
        return True
    
    def send_sms(self, message: str) -> bool:
        """发送短信通知"""
        phone = self.config.get("sms_phone", "")
        if not phone:
            print("  SMS phone not configured")
            return False
        
        print(f"  SMS notification would be sent to: {phone}")
        return True
    
    def notify(self, title: str, content: str):
        """发送通知"""
        if not self.config.get("enabled", False):
            print("  Notifications disabled")
            return
        
        self.send_wechat(title, content)
        self.send_email(title, content)
        self.send_sms(f"{title}: {content[:100]}")


class BrokerAPI:
    """券商API接口（模拟）"""
    
    def __init__(self, broker: str = "simulated"):
        self.broker = broker
        self.connected = False
    
    def connect(self) -> bool:
        """连接券商"""
        if self.broker == "simulated":
            self.connected = True
            print("  Connected to simulated broker")
            return True
        
        print(f"  Broker {self.broker} not implemented")
        print("  Available brokers: simulated, qmt, ptrade")
        return False
    
    def get_account_info(self) -> dict:
        """获取账户信息"""
        if not self.connected:
            return {"error": "not connected"}
        
        return {
            "total_asset": 100000,
            "cash": 50000,
            "market_value": 50000,
            "available_cash": 50000,
        }
    
    def get_positions(self) -> list:
        """获取持仓"""
        if not self.connected:
            return []
        
        return []
    
    def place_order(self, code: str, action: str, 
                    shares: int, price: float = None) -> dict:
        """下单"""
        if not self.connected:
            return {"error": "not connected"}
        
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        print(f"  Order placed: {action} {code} {shares} shares @ {price}")
        
        return {
            "order_id": order_id,
            "status": "filled",
            "code": code,
            "action": action,
            "shares": shares,
            "price": price,
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        print(f"  Order cancelled: {order_id}")
        return True
    
    def get_order_status(self, order_id: str) -> dict:
        """获取订单状态"""
        return {
            "order_id": order_id,
            "status": "filled",
        }


class TradingExecutor:
    """交易执行器"""
    
    def __init__(self, broker: BrokerAPI = None, notifier: Notifier = None):
        self.broker = broker or BrokerAPI()
        self.notifier = notifier or Notifier()
    
    def execute_selection(self, stocks: list):
        """执行选股结果"""
        print(f"\nExecuting selection: {stocks}")
        
        account = self.broker.get_account_info()
        available_cash = account.get("available_cash", 0)
        
        if available_cash <= 0:
            print("  No available cash")
            return
        
        positions = self.broker.get_positions()
        current_codes = [p["code"] for p in positions]
        
        stocks_to_sell = [s for s in current_codes if s not in stocks]
        stocks_to_buy = [s for s in stocks if s not in current_codes]
        
        for code in stocks_to_sell:
            self.broker.place_order(code, "SELL", 0)
        
        if stocks_to_buy:
            per_stock_cash = available_cash * 0.9 / len(stocks_to_buy)
            
            for code in stocks_to_buy:
                self.broker.place_order(code, "BUY", 0)
        
        self.notifier.notify(
            "交易执行完成",
            f"买入: {stocks_to_buy}\n卖出: {stocks_to_sell}"
        )
    
    def execute_risk_signals(self, signals: list):
        """执行风控信号"""
        print(f"\nExecuting risk signals: {len(signals)} signals")
        
        for signal in signals:
            if signal["action"] == "SELL":
                self.broker.place_order(
                    signal["code"], "SELL", 0, signal.get("price")
                )
        
        if signals:
            self.notifier.notify(
                "风控信号执行",
                f"执行了{len(signals)}个卖出信号"
            )


def setup_all():
    """一键配置所有功能"""
    print("=" * 60)
    print("  Setting up Stock Quant System")
    print("=" * 60)
    
    print("\n1. Creating scheduler...")
    scheduler = TaskScheduler()
    scheduler.create_all_tasks()
    
    print("\n2. Creating notify config...")
    notify_config = {
        "wechat_webhook": "",
        "email": "",
        "sms_phone": "",
        "enabled": False
    }
    with open("notify_config.json", "w", encoding="utf-8") as f:
        json.dump(notify_config, f, indent=2)
    print("  Created notify_config.json (please fill in your config)")
    
    print("\n3. Creating broker config...")
    broker_config = {
        "broker": "simulated",
        "qmt_path": "",
        "ptrade_path": "",
    }
    with open("broker_config.json", "w", encoding="utf-8") as f:
        json.dump(broker_config, f, indent=2)
    print("  Created broker_config.json")
    
    print("\n" + "=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print("""
Next steps:
1. Configure notify_config.json (WeChat webhook, email, phone)
2. Configure broker_config.json (QMT/Ptrade path)
3. Run scheduler/setup_scheduler.bat as Administrator
4. Test with: python trading_system.py --mode full
""")


if __name__ == "__main__":
    setup_all()
