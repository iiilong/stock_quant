import pandas as pd
from .base import BaseStrategy


class TrendFollowStrategy(BaseStrategy):
    def __init__(self, short_window=5, mid_window=20, long_window=60):
        super().__init__("趋势跟踪")
        self.short_window = short_window
        self.mid_window = mid_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0

        df["ma_short"] = df["close"].rolling(self.short_window).mean()
        df["ma_mid"] = df["close"].rolling(self.mid_window).mean()
        df["ma_long"] = df["close"].rolling(self.long_window).mean()

        golden_cross = (
            (df["ma_short"] > df["ma_mid"]) &
            (df["ma_short"].shift(1) <= df["ma_mid"].shift(1))
        )
        df.loc[golden_cross, "signal"] = 1

        death_cross = (
            (df["ma_short"] < df["ma_mid"]) &
            (df["ma_short"].shift(1) >= df["ma_mid"].shift(1))
        )
        df.loc[death_cross, "signal"] = -1

        above_long = df["close"] > df["ma_long"]
        df.loc[~above_long & (df["signal"] == 1), "signal"] = 0

        df["position"] = df["signal"]
        return df


class MeanReversionStrategy(BaseStrategy):
    def __init__(self, period=20, std_dev=2.0):
        super().__init__("均值回归")
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0

        df["bb_mid"] = df["close"].rolling(self.period).mean()
        df["bb_std"] = df["close"].rolling(self.period).std()
        df["bb_upper"] = df["bb_mid"] + self.std_dev * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - self.std_dev * df["bb_std"]

        df["z_score"] = (df["close"] - df["bb_mid"]) / df["bb_std"]

        buy_signal = (
            (df["close"] < df["bb_lower"]) &
            (df["close"].shift(1) >= df["bb_lower"].shift(1))
        )
        df.loc[buy_signal, "signal"] = 1

        sell_signal = (
            (df["close"] > df["bb_upper"]) &
            (df["close"].shift(1) <= df["bb_upper"].shift(1))
        )
        df.loc[sell_signal, "signal"] = -1

        neutral = (df["close"] > df["bb_mid"] * 0.98) & (df["close"] < df["bb_mid"] * 1.02)
        df.loc[neutral, "signal"] = 0

        df["position"] = df["signal"]
        return df


class MomentumStrategy(BaseStrategy):
    def __init__(self, lookback=20, rsi_period=14,
                 rsi_oversold=30, rsi_overbought=70):
        super().__init__("动量策略")
        self.lookback = lookback
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0

        df["momentum"] = df["close"].pct_change(self.lookback)

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        buy_signal = (
            (df["momentum"] > 0.05) &
            (df["rsi"] < self.rsi_overbought) &
            (df["rsi"].shift(1) >= self.rsi_overbought)
        )
        df.loc[buy_signal, "signal"] = 1

        sell_signal = (
            (df["momentum"] < -0.05) |
            (df["rsi"] > self.rsi_overbought)
        )
        df.loc[sell_signal, "signal"] = -1

        df["position"] = df["signal"]
        return df


class MACDStrategy(BaseStrategy):
    def __init__(self, fast=12, slow=26, signal=9):
        super().__init__("MACD策略")
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0

        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        df["macd_line"] = ema_fast - ema_slow
        df["signal_line"] = df["macd_line"].ewm(span=self.signal_period, adjust=False).mean()
        df["macd_hist"] = df["macd_line"] - df["signal_line"]

        buy_signal = (
            (df["macd_line"] > df["signal_line"]) &
            (df["macd_line"].shift(1) <= df["signal_line"].shift(1))
        )
        df.loc[buy_signal, "signal"] = 1

        sell_signal = (
            (df["macd_line"] < df["signal_line"]) &
            (df["macd_line"].shift(1) >= df["signal_line"].shift(1))
        )
        df.loc[sell_signal, "signal"] = -1

        df["position"] = df["signal"]
        return df


class CompositeStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("复合策略")
        self.strategies = [
            TrendFollowStrategy(),
            MeanReversionStrategy(),
            MomentumStrategy(),
            MACDStrategy(),
        ]

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 0
        df["vote_score"] = 0

        for strategy in self.strategies:
            signals = strategy.generate_signals(data)
            df["vote_score"] += signals["signal"]

        threshold = len(self.strategies) * 0.5

        df.loc[df["vote_score"] >= threshold, "signal"] = 1
        df.loc[df["vote_score"] <= -threshold, "signal"] = -1

        df["position"] = df["signal"]
        return df
