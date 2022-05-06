from brownie.test import given, strategy
from decimal import Decimal

from .utils import calculate_mid_ratio


@given(
    leverage=strategy('decimal', min_value='1.0', max_value='5.0', places=3),
    is_long=strategy('bool'))
def test_position_estimate(state, market, feed, alice, ovl, leverage, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = leverage * Decimal(1e18)

    # calculate the notional
    notional = int(Decimal(collateral)
                   * Decimal(leverage) / Decimal(1e18))

    # get the mid price
    # NOTE: state.mid() tested in test_price.py
    mid_price = state.mid(market)

    # calculate the oi
    # NOTE: state.fractionOfCapOi() tested in test_oi.py
    oi = int(Decimal(notional) * Decimal(1e18) / Decimal(mid_price))
    fraction_oi = state.fractionOfCapOi(market, oi)

    # get the entry price
    # NOTE: state.bid() and state.ask() tested in test_price.py
    entry_price = state.ask(market, fraction_oi) if is_long else state.bid(
        market, fraction_oi)

    # calculate expected values
    expect_notional = notional
    expect_debt = expect_notional - collateral
    expect_is_long = is_long
    expect_mid_ratio = calculate_mid_ratio(entry_price, mid_price)
    expect_liquidated = False
    expect_oi_shares = oi

    # check market position is same as position returned from state
    expect = (expect_notional, expect_debt, expect_mid_ratio, expect_is_long,
              expect_liquidated, expect_oi_shares)
    actual = state.positionEstimate(market, collateral, leverage, is_long)
    assert expect == actual
