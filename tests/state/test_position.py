import pytest
from pytest import approx
from brownie import chain
from decimal import Decimal

from .utils import get_position_key


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

    # check market position oi same as state query oi
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


# TODO: mock_feed to change price
def test_value(state, market, feed, ovl, alice):
    pass


# TODO: mock_feed to change price
def test_notional(state, market, feed, ovl, alice):
    pass
