from enum import Enum
from typing import Any


class RiskParameter(Enum):
    K = 0
    LMBDA = 1
    DELTA = 2
    CAP_PAYOFF = 3
    CAP_NOTIONAL = 4
    CAP_LEVERAGE = 5
    CIRCUIT_BREAKER_WINDOW = 6
    CIRCUIT_BREAKER_MINT_TARGET = 7
    MAINTENANCE_MARGIN_FRACTION = 8
    MAINTENANCE_MARGIN_BURN_RATE = 9
    LIQUIDATION_FEE_RATE = 10
    TRADING_FEE_RATE = 11
    MIN_COLLATERAL = 12
    PRICE_DRIFT_UPPER_LIMIT = 13
    AVERAGE_BLOCK_TIME = 14


def mid_from_feed(data: Any) -> float:
    """
    Returns mid price from oracle feed data
    """
    (_, _, _, price_micro, price_macro, _, _, _) = data
    ask = max(price_micro, price_macro)
    bid = min(price_micro, price_macro)
    mid = (ask + bid) / 2
    return mid
