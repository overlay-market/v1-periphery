from brownie import web3
from decimal import Decimal
from enum import Enum
from hexbytes import HexBytes
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


def get_position_key(owner: str, id: int) -> HexBytes:
    """
    Returns the position key to retrieve an individual position
    from positions mapping
    """
    return web3.solidityKeccak(['address', 'uint256'], [owner, id])


def calculate_mid_ratio(entry_price: int, mid_price: int) -> int:
    """
    Returns mid ratio from entry price and mid price

    NOTE: mid_ratio is uint48 format and mid, entry prices
    are int FixedPoint format
    """
    # NOTE: mid_ratio "ONE" is 1e14 given uint48
    mid_ratio = int(Decimal(entry_price) * Decimal(1e14) / Decimal(mid_price))
    return mid_ratio


def position_entry_price(position: Any) -> float:
    """
    Returns the position entry price from an individual position tuple.

    entry = ratio * mid = ratio * (notional / oi)
    """
    (notional, debt, ratio, is_long, liquidated, oi_shares) = position
    ratio_fixed_point = Decimal(ratio) * Decimal(1e4)
    entry = float(ratio_fixed_point * Decimal(notional) / Decimal(oi_shares))
    return entry


def transform_snapshot(snapshot: Any, timestamp: int, window: int,
                       value: int) -> Any:
    """
    Returns the transformed snapshot factoring in
    decay in accumulator value over prior rolling window
    """
    (snap_timestamp, snap_window, snap_accumulator) = snapshot
    dt = timestamp - snap_timestamp

    # decay the acccumulator value for time that has passed
    if dt > snap_window:
        snap_accumulator = 0
    else:
        snap_accumulator -= snap_accumulator * dt / snap_window

    # set accumulator value now
    snap_accumulator_now = int(snap_accumulator + value)

    # calculate the window_now
    w1 = abs(snap_accumulator)
    w2 = abs(value)
    if snap_accumulator_now == 0:
        snap_window_now = window
    else:
        snap_window_now = int((w1 * snap_window + w2 * window) / (w1 + w2))

    # snap timestamp now is simply the new timestamp value
    snap_timestamp_now = timestamp

    snap_now = (snap_timestamp_now, snap_window_now, snap_accumulator_now)
    return snap_now
