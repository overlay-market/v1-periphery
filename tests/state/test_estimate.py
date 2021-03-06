from pytest import approx
from brownie.test import given, strategy
from decimal import Decimal

from .utils import price_to_tick, RiskParameter


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

    # oi total and oi total shares on side
    # NOTE: state.ois() tested in test_oi.py
    oi_long, oi_short = state.ois(market)
    oi_total = oi_long if is_long else oi_short
    oi_total_shares = market.oiLongShares() \
        if is_long else market.oiShortShares()

    # calculate the oi and oi shares
    # NOTE: state.fractionOfCapOi() tested in test_oi.py
    oi = int(Decimal(notional) * Decimal(1e18) / Decimal(mid_price))
    oi_shares = int(Decimal(oi) * Decimal(oi_total_shares)
                    / Decimal(oi_total)) if oi_total > 0 else oi
    fraction_oi = state.fractionOfCapOi(market, oi)

    # get the entry price
    # NOTE: state.bid() and state.ask() tested in test_price.py
    entry_price = state.ask(market, fraction_oi) if is_long else state.bid(
        market, fraction_oi)

    # calculate expected values
    expect_notional = notional
    expect_debt = expect_notional - collateral
    expect_is_long = is_long
    expect_mid_tick = price_to_tick(mid_price)
    expect_entry_tick = price_to_tick(entry_price)
    expect_liquidated = False
    expect_oi_shares = oi_shares
    expect_fraction_remaining = 10000

    # check market position is same as position returned from state
    expect = (expect_notional, expect_debt, expect_mid_tick, expect_entry_tick,
              expect_is_long, expect_liquidated, expect_oi_shares,
              expect_fraction_remaining)
    actual = state.positionEstimate(market, collateral, leverage, is_long)
    assert expect == actual


@given(is_long=strategy('bool'))
def test_debt_estimate(state, market, feed, alice, ovl, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = 3000000000000000000  # 3

    # calculate the notional
    notional = int(Decimal(collateral)
                   * Decimal(leverage) / Decimal(1e18))

    # calculate expected values
    expect_notional = notional
    expect_debt = expect_notional - collateral

    # check position's debt is same as position returned from state
    expect = expect_debt
    actual = state.debtEstimate(market, collateral, leverage, is_long)
    assert expect == actual


@given(is_long=strategy('bool'))
def test_cost_estimate(state, market, feed, alice, ovl, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = 3000000000000000000  # 3

    # check position's cost is same as position returned from state
    expect = collateral
    actual = state.costEstimate(market, collateral, leverage, is_long)
    assert expect == actual


@given(is_long=strategy('bool'))
def test_oi_estimate(state, market, feed, alice, ovl, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = 3000000000000000000  # 3

    # calculate the notional
    notional = int(Decimal(collateral)
                   * Decimal(leverage) / Decimal(1e18))

    # get the mid price
    # NOTE: state.mid() tested in test_price.py
    mid_price = state.mid(market)

    # calculate the oi
    oi = int(Decimal(notional) * Decimal(1e18) / Decimal(mid_price))

    # check position's oi is same as position returned from state
    # NOTE: rel 1e-4 given tick precision to 1bps
    expect = oi
    actual = state.oiEstimate(market, collateral, leverage, is_long)
    assert expect == approx(actual, rel=1e-4)


@given(is_long=strategy('bool'))
def test_maintenance_margin_estimate(state, market, feed, alice, ovl, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = 3000000000000000000  # 3

    # calculate the notional
    notional = int(Decimal(collateral)
                   * Decimal(leverage) / Decimal(1e18))

    # calculate expected values
    expect_maintenance_margin_fraction = market.params(
        RiskParameter.MAINTENANCE_MARGIN_FRACTION.value)
    expect_maintenance_margin = Decimal(
        notional) * Decimal(expect_maintenance_margin_fraction) / Decimal(1e18)

    # check position's maintenance is same as position returned from state
    expect = expect_maintenance_margin
    actual = state.maintenanceMarginEstimate(
        market, collateral, leverage, is_long)
    assert expect == actual


@given(is_long=strategy('bool'))
def test_liquidation_price_estimate(state, market, feed, alice, ovl, is_long):
    # alice build params
    collateral = 20000000000000000000  # 20
    leverage = 3000000000000000000  # 3

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
    maintenance_margin_fraction = market.params(
        RiskParameter.MAINTENANCE_MARGIN_FRACTION.value)
    maintenance_margin = Decimal(
        notional) * Decimal(maintenance_margin_fraction) / Decimal(1e18)
    liq_fee_rate = market.params(
        RiskParameter.LIQUIDATION_FEE_RATE.value)

    # calculate liquidation price
    dp = (Decimal(collateral) - Decimal(maintenance_margin) * Decimal(1e18)
          / (Decimal(1e18) - Decimal(liq_fee_rate))) / Decimal(oi)
    dp *= Decimal(1e18)

    expect_liquidation_price = entry_price - dp \
        if is_long else entry_price + dp

    # check position's maintenance is same as position returned from state
    # NOTE: rel 1e-4 given tick precision to 1bps
    expect = int(expect_liquidation_price)
    actual = int(state.liquidationPriceEstimate(
        market, collateral, leverage, is_long))
    assert expect == approx(actual, rel=1e-4)
