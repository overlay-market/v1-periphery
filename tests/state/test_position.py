import pytest
from pytest import approx
from brownie import chain, reverts
from brownie.test import given, strategy
from decimal import Decimal

from .utils import get_position_key, position_entry_price, RiskParameter


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
    actual = state.position(feed, alice.address, pos_id)

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
    (_, expect_debt, _, _, _, _) = market.positions(pos_key)
    actual_debt = state.debt(feed, alice.address, pos_id)

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
    (expect_notional_initial, expect_debt, _, _,
     _, _) = market.positions(pos_key)
    expect_cost = expect_notional_initial - expect_debt
    actual_cost = state.cost(feed, alice.address, pos_id)

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
    (_, _, _, _, _, expect_oi_shares) = market.positions(pos_key)
    expect_oi_long_shares = market.oiLongShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, _ = state.ois(feed)

    # check expect equals actual for position oi
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    actual_oi = int(state.oi(feed, alice.address, pos_id))
    assert expect_oi == approx(actual_oi)

    # forward the chain to check oi expectations in line after funding
    chain.mine(timedelta=600)

    # NOTE: ois() tests in test_oi.py
    expect_oi_long_shares = market.oiLongShares()
    actual_oi_long, _ = state.ois(feed)

    # check expect equals actual for position oi
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    actual_oi = int(state.oi(feed, alice.address, pos_id))
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
    (expect_notional_initial, expect_debt, _, _, _,
     expect_oi_shares) = market.positions(pos_key)
    expect_oi_long_shares = market.oiLongShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, _ = state.ois(feed)

    # calculate the expected collateral amount: Q * (OI(t) / OI(0)) - D
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    expect_oi_initial = expect_oi_shares
    expect_collateral = int(expect_notional_initial
                            * (expect_oi / expect_oi_initial) - expect_debt)

    # check expect collateral matches actual queried from state
    actual_collateral = int(state.collateral(feed, alice.address, pos_id))
    assert expect_collateral == approx(actual_collateral)

    # forward the chain to check collateral expectations in line after funding
    chain.mine(timedelta=600)

    # NOTE: ois() tests in test_oi.py
    expect_oi_long_shares = market.oiLongShares()
    actual_oi_long, _ = state.ois(feed)

    # calculate the expected collateral amount: Q * (OI(t) / OI(0)) - D
    expect_oi = int(
        Decimal(actual_oi_long) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_long_shares)
    )
    expect_oi_initial = expect_oi_shares
    expect_collateral = int(expect_notional_initial
                            * (expect_oi / expect_oi_initial) - expect_debt)

    # check expect collateral matches actual queried from state
    actual_collateral = int(state.collateral(feed, alice.address, pos_id))
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
    (expect_notional_initial, expect_debt, expect_mid_ratio, _, _,
     expect_oi_shares) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(feed)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # calculate the expected value of position
    # V(t) = N(t) +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = expect_oi_shares
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # get the entry price
    expect_entry_price = position_entry_price(pos)
    expect_entry_price = int(expect_entry_price)

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(feed, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        feed, frac_cap_oi) if is_long else state.ask(feed, frac_cap_oi)
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
    actual_value = int(state.value(feed, alice.address, pos_id))
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
    (expect_notional_initial, expect_debt, expect_mid_ratio, _, _,
     expect_oi_shares) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(feed)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = expect_oi_shares
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # get the entry price
    expect_entry_price = position_entry_price(pos)
    expect_entry_price = int(expect_entry_price)

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(feed, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        feed, frac_cap_oi) if is_long else state.ask(feed, frac_cap_oi)
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
    actual_notional = int(state.notional(feed, alice.address, pos_id))
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
    (expect_notional_initial, expect_debt, expect_mid_ratio, _, _,
     expect_oi_shares) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(feed)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = expect_oi_shares
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # get the entry price
    expect_entry_price = position_entry_price(pos)
    expect_entry_price = int(expect_entry_price)

    # NOTE: fractionOfCapOi tests in test_oi.py
    frac_cap_oi = state.fractionOfCapOi(feed, expect_oi)

    # NOTE: bid, ask tests in test_price.py
    expect_exit_price = state.bid(
        feed, frac_cap_oi) if is_long else state.ask(feed, frac_cap_oi)
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
    actual_trading_fee = int(state.tradingFee(feed, alice.address, pos_id))
    assert expect_trading_fee == approx(actual_trading_fee)


# TODO: mock market!
def test_liquidatable(state, market, feed, ovl, alice):
    pass


# TODO: mock market!
def test_liquidation_fee(state, market, feed, ovl, alice):
    pass


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
    (expect_notional_initial, expect_debt, expect_mid_ratio, _, _,
     expect_oi_shares) = pos

    # calculate the expected maintenance margin: MM * Q
    expect_maintenance_margin_fraction = market.params(
        RiskParameter.MAINTENANCE_MARGIN_FRACTION.value)
    expect_maintenance_margin = int(Decimal(
        expect_maintenance_margin_fraction) * Decimal(expect_notional_initial)
        / Decimal(1e18))

    # check expect maintenance in line with actual from state
    actual_maintenance_margin = int(
        state.maintenanceMargin(feed, alice.address, pos_id))
    assert expect_maintenance_margin == approx(actual_maintenance_margin)


# TODO: mock market!
def test_margin_excess_before_liquidation(state, market, feed, ovl, alice):
    pass


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
    (expect_notional_initial, expect_debt, expect_mid_ratio, _, _,
     expect_oi_shares) = pos
    expect_oi_tot_shares_on_side = market.oiLongShares() if is_long \
        else market.oiShortShares()

    # NOTE: ois() tests in test_oi.py
    actual_oi_long, actual_oi_short = state.ois(feed)
    actual_oi_tot_on_side = actual_oi_long if is_long else actual_oi_short

    # calculate the expected value of position
    # V(t) = N(t) + D +/- OI(t) * [P(t) - P(0)]
    expect_oi_initial = expect_oi_shares
    expect_oi = int(
        Decimal(actual_oi_tot_on_side) * Decimal(expect_oi_shares)
        / Decimal(expect_oi_tot_shares_on_side)
    )

    # get the entry price
    expect_entry_price = position_entry_price(pos)
    expect_entry_price = int(expect_entry_price)

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
        state.liquidationPrice(feed, alice.address, pos_id))
    assert expect_liquidation_price == approx(actual_liquidation_price)


def test_liquidation_price_reverts_when_oi_is_zero(state, market, feed,
                                                   ovl, alice):
    # try for a position that doesn't exist
    with reverts("OVLV1: oi == 0"):
        _ = state.liquidationPrice(feed, alice.address, 0)
