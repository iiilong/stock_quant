from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    def should_buy(self, row: pd.Series, prev_row: pd.Series) -> bool:
        return False

    def should_sell(self, row: pd.Series, prev_row: pd.Series) -> bool:
        return False

    def position_size(self, row: pd.Series, capital: float,
                      price: float) -> int:
        shares = int(capital * 0.3 / price)
        return (shares // 100) * 100
