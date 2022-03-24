import pytest
from pytest import approx
from brownie import chain
from decimal import Decimal
from math import exp, sqrt

from .utils import mid_from_feed


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_oi(market_state, market, feed, ovl, alice, bob):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 1000000000000000000  # 1
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # bob build params
    input_collateral_bob = 10000000000000000000  # 10
    input_leverage_bob = 1000000000000000000  # 1
    input_is_long_bob = False
    input_price_limit_bob = 0

    # approve max for both
    ovl.approve(market, 2**256-1, {"from": alice})
    ovl.approve(market, 2**256-1, {"from": bob})

    # build position for alice
    market.build(input_collateral_alice, input_leverage_alice,
                 input_is_long_alice, input_price_limit_alice, {"from": alice})

    # get mid price
    data = feed.latest()
    mid = Decimal(mid_from_feed(data)) / Decimal(1e18)

    # check oi for alice immediately after build
    notional_alice = Decimal(input_collateral_alice) \
        * Decimal(input_leverage_alice) / Decimal(1e18)
    expect_oi_long = int(notional_alice / mid)
    actual_oi_long, actual_oi_short = market_state.oi(feed)

    assert int(actual_oi_long) == approx(expect_oi_long)
    assert actual_oi_short == 0

    # build position for bob
    timestamp_update_last = market.timestampUpdateLast()
    market.build(input_collateral_bob, input_leverage_bob,
                 input_is_long_bob, input_price_limit_bob, {"from": bob})

    # get mid price
    data = feed.latest()
    mid = Decimal(mid_from_feed(data)) / Decimal(1e18)

    # check oi for bob immediately after build
    notional_bob = Decimal(input_collateral_bob) \
        * Decimal(input_leverage_bob) / Decimal(1e18)
    expect_oi_short = int(notional_bob / mid)
    actual_oi_long, actual_oi_short = market_state.oi(feed)

    # calculate expect_oi_long due to funding decay since last build
    time_elapsed = Decimal(chain[-1]["timestamp"] - timestamp_update_last)
    k = Decimal(market.k()) / Decimal(1e18)

    expect_oi_long *= exp(-2*k*time_elapsed)
    expect_oi_long = int(expect_oi_long)

    assert int(actual_oi_long) == approx(expect_oi_long)
    assert int(actual_oi_short) == approx(expect_oi_short)

    # forward the chain and check market state oi accounts for funding
    # without any updates to the market itself
    dt = 600
    chain.mine(timedelta=dt)

    expect_oi_imb = Decimal(expect_oi_long - expect_oi_short)
    expect_oi_tot = Decimal(expect_oi_long + expect_oi_short)

    # adjust total oi for funding
    expect_oi_tot *= Decimal(sqrt(1 - (expect_oi_imb / expect_oi_tot)**2
                                  * Decimal(1 - exp(-4*k*dt))))

    # adjust oi imbalance for funding
    expect_oi_imb *= Decimal(exp(-2*k*dt))

    # update long and short values
    expect_oi_long = int((expect_oi_tot + expect_oi_imb) / Decimal(2))
    expect_oi_short = int((expect_oi_tot - expect_oi_imb) / Decimal(2))

    actual_oi_long, actual_oi_short = market_state.oi(feed)
    assert int(actual_oi_long) == approx(expect_oi_long)
    assert int(actual_oi_short) == approx(expect_oi_short)


def test_oi_is_zero_when_no_positions(market_state, feed):
    actual_oi_long, actual_oi_short = market_state.oi(feed)
    assert actual_oi_long == 0
    assert actual_oi_short == 0
