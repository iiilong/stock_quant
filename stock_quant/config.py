from dataclasses import dataclass, field
from typing import List


@dataclass
class BacktestConfig:
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.001
    slippage: float = 0.001
    max_position_pct: float = 0.3
    max_holdings: int = 5
    stop_loss: float = 0.08
    take_profit: float = 0.20
    benchmark: str = "sh000300"
    start_date: str = "20230101"
    end_date: str = "20260101"


@dataclass
class StrategyConfig:
    short_window: int = 5
    mid_window: int = 20
    long_window: int = 60
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    atr_period: int = 14
    momentum_lookback: int = 20
    volume_ma_period: int = 20


@dataclass
class StockPool:
    codes: List[str] = field(default_factory=lambda: [
        "000001", "000002", "000063", "000100", "000157",
        "000333", "000568", "000651", "000725", "000858",
        "002027", "002230", "002241", "002304", "002415",
        "002594", "002714", "002916", "003816", "600000",
        "600009", "600016", "600028", "600030", "600036",
        "600048", "600050", "600089", "600104", "600196",
        "600276", "600309", "600340", "600406", "600436",
        "600438", "600489", "600519", "600570", "600585",
        "600588", "600600", "600690", "600703", "600745",
        "600809", "600837", "600887", "600893", "600900",
        "600919", "601012", "601088", "601111", "601138",
        "601166", "601169", "601186", "601211", "601225",
        "601228", "601229", "601231", "601288", "601288",
        "601318", "601319", "601328", "601336", "601360",
        "601377", "601390", "601398", "601601", "601628",
        "601668", "601669", "601688", "601766", "601788",
        "601800", "601808", "601818", "601838", "601857",
        "601877", "601878", "601881", "601888", "601898",
        "601899", "601901", "601919", "601933", "601939",
        "601985", "601988", "601989", "601995", "601998",
        "603019", "603056", "603160", "603259", "603260",
        "603288", "603290", "603369", "603501", "603517",
        "603799", "603833", "603899", "603986", "603993",
    ])


bt_config = BacktestConfig()
strategy_config = StrategyConfig()
stock_pool = StockPool()
