import pytest
from pytest import approx
from brownie import chain, reverts
from brownie.test import given, strategy
from decimal import Decimal

from .utils import (
    get_position_key,
    tick_to_price,
    RiskParameter
)


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_position(state, market, feed, alice, ovl):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # check market position is same as position returned from state
    expect = market.positions(pos_key)
    actual = state.position(market, alice.address, pos_id)

    assert expect == actual


def test_debt(state, market, feed, ovl, alice):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # check market position debt same as state queried position debt
    (_, expect_debt, _, _, _, _, _, _) = market.positions(pos_key)
    actual_debt = state.debt(market, alice.address, pos_id)

    assert expect_debt == actual_debt


def test_cost(state, market, feed, ovl, alice):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # check market position debt same as state queried position debt
    (expect_notional_initial, expect_debt, _, _, _, _,
     _, _) = market.positions(pos_key)
    expect_cost = expect_notional_initial - expect_debt
    actual_cost = state.cost(market, alice.address, pos_id)

    assert expect_cost == actual_cost


def test_oi(state, market, feed, ovl, alice):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # check market position oi same as state query oi
    (_, _, _, _, _, _, expect_oi_shares, _) = market.positions(pos_key)
    expect_oi_long_shares = market.oiLongShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, _ = state.ois(market)

    # check expect equals actual for position oi
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    actual_oi = int(state.oi(market, alice.address, pos_id))
    assert expect_oi == approx(actual_oi)

    # forward the chain to check oi expectations in line after funding
    chain.mine(timedelta=600)

    # NOTE: ois() tests in test_oi.py
    expect_oi_long_shares = market.oiLongShares()
    actual_oi_long, _ = state.ois(market)

    # check expect equals actual for position oi
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    actual_oi = int(state.oi(market, alice.address, pos_id))
    assert expect_oi == approx(actual_oi)


def test_collateral(state, market, feed, ovl, alice):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = market.positions(pos_key)
    expect_oi_long_shares = market.oiLongShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, _ = state.ois(market)

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected collateral amount: Q * (OI(t) / OI(0)) - D
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_collateral = int(expect_notional_initial
                            * (expect_oi / expect_oi_initial) - expect_debt)

    # check expect collateral matches actual queried from state
    actual_collateral = int(state.collateral(market, alice.address, pos_id))
    assert expect_collateral == approx(actual_collateral)

    # forward the chain to check collateral expectations in line after funding
    chain.mine(timedelta=600)

    # NOTE: ois() tests in test_oi.py
    expect_oi_long_shares = market.oiLongShares()
    actual_oi_long, _ = state.ois(market)

    # calculate the expected collateral amount: Q * (OI(t) / OI(0)) - D
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_collateral = int(expect_notional_initial
                            * (expect_oi / expect_oi_initial) - expect_debt)

    # check expect collateral matches actual queried from state
    actual_collateral = int(state.collateral(market, alice.address, pos_id))
    assert expect_collateral == approx(actual_collateral)


@given(is_long=strategy('bool'))
def test_value(state, market, feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(market, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        market, frac_cap_oi) if is_long else state.ask(market, frac_cap_oi)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1
    expect_value = int(expect_collateral + expect_pnl)

    # check expect value in line with actual from state
    actual_value = int(state.value(market, alice.address, pos_id))
    assert expect_value == approx(actual_value)


@given(is_long=strategy('bool'))
def test_notional(state, market, feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(market, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        market, frac_cap_oi) if is_long else state.ask(market, frac_cap_oi)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL + debt from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_debt = Decimal(expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1
    expect_notional = int(expect_collateral + expect_pnl + expect_debt)

    # check expect notional in line with actual from state
    actual_notional = int(state.notional(market, alice.address, pos_id))
    assert expect_notional == approx(actual_notional)


@given(is_long=strategy('bool'))
def test_trading_fee(state, market, feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(market, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        market, frac_cap_oi) if is_long else state.ask(market, frac_cap_oi)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL + debt from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_debt = Decimal(expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1
    expect_notional = expect_collateral + expect_pnl + expect_debt

    # trading fee is % of notional
    expect_trading_fee_rate = market.params(
        RiskParameter.TRADING_FEE_RATE.value
    )
    expect_trading_fee = Decimal(
        expect_trading_fee_rate) * expect_notional / Decimal(1e18)

    # check expect trade fee in line with actual from state
    actual_trading_fee = int(state.tradingFee(market, alice.address, pos_id))
    assert expect_trading_fee == approx(actual_trading_fee)


@given(is_long=strategy('bool'))
def test_liquidatable(state, mock_market, mock_feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    tol = 1e-4

    # approve max for alice
    ovl.approve(mock_market, 2**256-1, {"from": alice})

    # build position for alice
    tx = mock_market.build(input_collateral_alice, input_leverage_alice,
                           input_is_long_alice, input_price_limit_alice,
                           {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get the market position
    pos = mock_market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos

    # check not liquidatable
    expect_liquidatable = False
    actual_liquidatable = state.liquidatable(
        mock_market, alice.address, pos_id)
    assert expect_liquidatable == actual_liquidatable

    # set price to just beyond liquidation price and make sure liquidatable
    # NOTE: liquidationPrice() tests below in test_liquidation_price
    expect_liquidation_price = state.liquidationPrice(
        mock_market, alice.address, pos_id)
    mock_feed_price = expect_liquidation_price * \
        (1 - tol) if is_long else expect_liquidation_price * (1 + tol)
    mock_feed.setPrice(mock_feed_price, {"from": alice})

    # check liquidatable
    expect_liquidatable = True
    actual_liquidatable = state.liquidatable(
        mock_market, alice.address, pos_id)
    assert expect_liquidatable == actual_liquidatable

    # set price to just before liquidation price and make sure not liquidatable
    mock_feed_price = expect_liquidation_price * \
        (1 + tol) if is_long else expect_liquidation_price * (1 - tol)
    mock_feed.setPrice(mock_feed_price, {"from": alice})

    # check no longer liquidatable
    expect_liquidatable = False
    actual_liquidatable = state.liquidatable(
        mock_market, alice.address, pos_id)
    assert expect_liquidatable == actual_liquidatable


@given(is_long=strategy('bool'))
def test_liquidation_fee(state, mock_market, mock_feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    tol = 1e-4

    # approve max for alice
    ovl.approve(mock_market, 2**256-1, {"from": alice})

    # build position for alice
    tx = mock_market.build(input_collateral_alice, input_leverage_alice,
                           input_is_long_alice, input_price_limit_alice,
                           {"from": alice})
    pos_id = tx.return_value

    # set price to just beyond liquidation price
    # NOTE: liquidationPrice() tests below in test_liquidation_price
    expect_liquidation_price = state.liquidationPrice(
        mock_market, alice.address, pos_id)
    mock_feed_price = expect_liquidation_price * \
        (1 - tol) if is_long else expect_liquidation_price * (1 + tol)
    mock_feed.setPrice(mock_feed_price, {"from": alice})

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = mock_market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = mock_market.oiLongShares() if is_long \
        else mock_market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(mock_market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # mid used for liquidation exit (manipulation resistant)
    # NOTE: mid tests in test_price.py
    expect_exit_price = state.mid(mock_market)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1
    expect_value = expect_collateral + expect_pnl

    # calculate expect liquidation fee as percentage on expected value left
    expect_liq_fee_rate = mock_market.params(
        RiskParameter.LIQUIDATION_FEE_RATE.value)
    expect_liq_fee = int(Decimal(expect_liq_fee_rate)
                         * expect_value / Decimal(1e18))

    # check expect liq fee reward in line with actual
    actual_liq_fee = int(state.liquidationFee(
        mock_market, alice.address, pos_id))
    assert expect_liq_fee == approx(actual_liq_fee)


def test_maintenance_margin(state, market, feed, ovl, alice):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos

    # calculate the expected maintenance margin: MM * Q
    expect_maintenance_margin_fraction = market.params(
        RiskParameter.MAINTENANCE_MARGIN_FRACTION.value)
    expect_maintenance_margin = int(Decimal(
        expect_maintenance_margin_fraction) * Decimal(expect_notional_initial)
        / Decimal(1e18))

    # check expect maintenance in line with actual from state
    actual_maintenance_margin = int(
        state.maintenanceMargin(market, alice.address, pos_id))
    assert expect_maintenance_margin == approx(actual_maintenance_margin)


@given(is_long=strategy('bool'))
def test_margin_excess_before_liquidation(state, mock_market, mock_feed,
                                          ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    # Use 2.5% as diff before/beyond liq
    tol = 2.5e-2

    # approve max for alice
    ovl.approve(mock_market, 2**256-1, {"from": alice})

    # build position for alice
    tx = mock_market.build(input_collateral_alice, input_leverage_alice,
                           input_is_long_alice, input_price_limit_alice,
                           {"from": alice})
    pos_id = tx.return_value

    # set price to just before liquidation price
    # NOTE: liquidationPrice() tests below in test_liquidation_price
    expect_liquidation_price = state.liquidationPrice(
        mock_market, alice.address, pos_id)
    mock_feed_price = expect_liquidation_price * \
        (1 + tol) if is_long else expect_liquidation_price * (1 - tol)
    mock_feed.setPrice(mock_feed_price, {"from": alice})

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = mock_market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = mock_market.oiLongShares() if is_long \
        else mock_market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(mock_market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # mid used for liquidation exit (manipulation resistant)
    # NOTE: mid tests in test_price.py
    expect_exit_price = state.mid(mock_market)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1

    expect_value = int(expect_collateral + expect_pnl)
    if expect_value < 0:
        expect_value = 0

    # calculate expect liquidation fee as percentage on expected value left
    # NOTE: liquidationFee tests above
    expect_liq_fee = int(state.liquidationFee(
        mock_market, alice.address, pos_id))

    # calculate the expect maintenance margin
    # NOTE: maintenanceMargin tests above
    expect_maintenance_margin = int(
        state.maintenanceMargin(mock_market, alice.address, pos_id))

    # calculate expected excess
    expect_excess = expect_value - expect_maintenance_margin - expect_liq_fee
    actual_excess = int(state.marginExcessBeforeLiquidation(
        mock_market, alice.address, pos_id))
    assert expect_excess == approx(actual_excess, rel=1e-4)

    # repeat the same when excess < 0
    # set price to just beyond liquidation price
    expect_liquidation_price = state.liquidationPrice(
        mock_market, alice.address, pos_id)
    mock_feed_price = expect_liquidation_price * \
        (1 - tol) if is_long else expect_liquidation_price * (1 + tol)
    mock_feed.setPrice(mock_feed_price, {"from": alice})

    # mid used for liquidation exit (manipulation resistant)
    # NOTE: mid tests in test_price.py
    expect_exit_price = state.mid(mock_market)
    expect_exit_price = int(expect_exit_price)

    # calculate value with collateral + PnL from price deltas
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)
    expect_pnl = expect_oi * (expect_exit_price
                              - expect_entry_price) / Decimal(1e18)
    if not is_long:
        expect_pnl *= -1

    expect_value = int(expect_collateral + expect_pnl)
    if expect_value < 0:
        expect_value = 0

    # calculate expect liquidation fee as percentage on expected value left
    # NOTE: liquidationFee tests above
    expect_liq_fee = int(state.liquidationFee(
        mock_market, alice.address, pos_id))

    # calculate the expect maintenance margin
    # NOTE: maintenanceMargin tests above
    expect_maintenance_margin = int(
        state.maintenanceMargin(mock_market, alice.address, pos_id))

    # calculate expected excess
    expect_excess = expect_value - expect_maintenance_margin - expect_liq_fee
    actual_excess = int(state.marginExcessBeforeLiquidation(
        mock_market, alice.address, pos_id))
    assert expect_excess == approx(actual_excess, rel=1e-4)


@given(is_long=strategy('bool'))
def test_liquidation_price(state, market, feed, ovl, alice, is_long):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 3000000000000000000  # 3
    input_is_long_alice = is_long
    input_price_limit_alice = 2**256-1 if is_long else 0

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral_alice, input_leverage_alice,
                      input_is_long_alice, input_price_limit_alice,
                      {"from": alice})
    pos_id = tx.return_value

    # get the position key for market query
    pos_key = get_position_key(alice.address, pos_id)

    # get market position oi
    pos = market.positions(pos_key)
    (expect_notional_initial, expect_debt, expect_mid_tick, expect_entry_tick,
     _, _, expect_oi_shares, _) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(market)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # get the entry and mid prices
    expect_mid_price = tick_to_price(expect_mid_tick)
    expect_mid_price = int(expect_mid_price)

    expect_entry_price = tick_to_price(expect_entry_tick)
    expect_entry_price = int(expect_entry_price)

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = Decimal(
        expect_notional_initial) * Decimal(1e18) / Decimal(expect_mid_price)
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # calculate the collateral backing the position
    expect_collateral = Decimal(expect_notional_initial
                                * (expect_oi / expect_oi_initial)-expect_debt)

    # calculate the maintenance margin requirement for the position: MM * Q
    expect_maintenance_margin_fraction = market.params(
        RiskParameter.MAINTENANCE_MARGIN_FRACTION.value)
    expect_maintenance_margin = int(Decimal(
        expect_maintenance_margin_fraction) * Decimal(expect_notional_initial)
        / Decimal(1e18))

    # get the liquidation fee rate
    expect_liq_fee_rate = market.params(
        RiskParameter.LIQUIDATION_FEE_RATE.value)

    # calculate the dp term
    expect_dp = (expect_collateral - expect_maintenance_margin
                 / (Decimal(1) - Decimal(expect_liq_fee_rate) / Decimal(1e18)))
    expect_dp = expect_dp * Decimal(1e18) / Decimal(expect_oi)

    # get the expect liquidation price
    expect_liquidation_price = expect_entry_price - \
        expect_dp if is_long else expect_entry_price + expect_dp
    expect_liquidation_price = int(expect_liquidation_price)

    # check expect liq price in line with actual from state
    actual_liquidation_price = int(
        state.liquidationPrice(market, alice.address, pos_id))
    assert expect_liquidation_price == approx(actual_liquidation_price)


def test_liquidation_price_reverts_when_oi_is_zero(state, market, feed,
                                                   ovl, alice):
    # try for a position that doesn't exist
    with reverts("OVLV1: oi == 0"):
        _ = state.liquidationPrice(market, alice.address, 0)
