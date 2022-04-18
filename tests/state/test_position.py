import pytest
from pytest import approx
from brownie import chain
from brownie.test import given, strategy
from decimal import Decimal

from .utils import get_position_key, position_entry_price


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


# TODO: mock_feed to change price for value and notional

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


def test_notional(state, market, feed, ovl, alice):
    pass
