import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(series: pd.Series, period: int = 20,
                    std_dev: float = 2.0) -> tuple:
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3) -> tuple:
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    return k, d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low)


def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val
    minus_di = 100 * ema(minus_dm, period) / atr_val
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return ema(dx, period)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series,
         volume: pd.Series) -> pd.Series:
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def squeeze_momentum(high: pd.Series, low: pd.Series, close: pd.Series,
                     vol_ma_period: int = 20) -> pd.Series:
    upper, middle, lower = bollinger_bands(close, 20, 1.5)
    bb_width = (upper - lower) / middle
    bb_width_ma = sma(bb_width, vol_ma_period)
    squeeze = bb_width < bb_width_ma
    highest = high.rolling(window=14).max()
    lowest = low.rolling(window=14).min()
    hl2 = (highest + lowest) / 2
    linear_reg = close - sma((hl2 + sma(close, 14)) / 2, 14)
    return linear_reg


def add_all_indicators(df: pd.DataFrame, config) -> pd.DataFrame:
    df = df.copy()
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    df["ma_short"] = sma(close, config.short_window)
    df["ma_mid"] = sma(close, config.mid_window)
    df["ma_long"] = sma(close, config.long_window)
    df["ema_short"] = ema(close, config.short_window)
    df["ema_mid"] = ema(close, config.mid_window)

    df["rsi"] = rsi(close, config.rsi_period)
    macd_line, signal_line, histogram = macd(close, config.macd_fast, config.macd_slow, config.macd_signal)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = histogram

    upper, middle, lower = bollinger_bands(close, config.bollinger_period, config.bollinger_std)
    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower
    df["bb_width"] = (upper - lower) / middle

    df["atr"] = atr(high, low, close, config.atr_period)
    k, d = stochastic(high, low, close)
    df["stoch_k"] = k
    df["stoch_d"] = d
    df["williams_r"] = williams_r(high, low, close)
    df["adx"] = adx(high, low, close)
    df["obv"] = obv(close, volume)
    df["vwap"] = vwap(high, low, close, volume)

    df["volume_ma"] = sma(volume, config.volume_ma_period)
    df["volume_ratio"] = volume / df["volume_ma"]
    df["pct_change"] = close.pct_change()
    df["volatility"] = df["pct_change"].rolling(window=20).std() * np.sqrt(252)

    df = df.dropna()
    return df
