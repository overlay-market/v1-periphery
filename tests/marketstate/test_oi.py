import pytest
from pytest import approx
from brownie import chain, reverts
from decimal import Decimal
from math import exp, sqrt

from .utils import mid_from_feed, RiskParameter


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_ois(market_state, market, feed, ovl, alice, bob):
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

    # get the actual values
    actual_oi_long, actual_oi_short = market_state.ois(feed)

    # get mid price
    data = feed.latest()
    mid = Decimal(mid_from_feed(data)) / Decimal(1e18)

    # check oi for alice immediately after build
    notional_alice = Decimal(input_collateral_alice) \
        * Decimal(input_leverage_alice) / Decimal(1e18)
    expect_oi_long = int(notional_alice / mid)

    assert int(actual_oi_long) == approx(expect_oi_long)
    assert actual_oi_short == 0

    # build position for bob
    timestamp_update_last = market.timestampUpdateLast()
    market.build(input_collateral_bob, input_leverage_bob,
                 input_is_long_bob, input_price_limit_bob, {"from": bob})

    # get the actual values
    actual_oi_long, actual_oi_short = market_state.ois(feed)

    # get mid price
    data = feed.latest()
    mid = Decimal(mid_from_feed(data)) / Decimal(1e18)

    # check oi for bob immediately after build
    notional_bob = Decimal(input_collateral_bob) \
        * Decimal(input_leverage_bob) / Decimal(1e18)
    expect_oi_short = int(notional_bob / mid)

    # calculate expect_oi_long due to funding decay since last build
    time_elapsed = Decimal(chain[-1]["timestamp"] - timestamp_update_last)
    k = Decimal(market.params(RiskParameter.K.value)) / Decimal(1e18)

    expect_oi_long *= exp(-2*k*time_elapsed)
    expect_oi_long = int(expect_oi_long)

    assert int(actual_oi_long) == approx(expect_oi_long)
    assert int(actual_oi_short) == approx(expect_oi_short)

    # forward the chain and check market state oi accounts for funding
    # without any updates to the market itself
    dt = 600
    chain.mine(timedelta=dt)

    # get the actual values
    actual_oi_long, actual_oi_short = market_state.ois(feed)

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

    assert int(actual_oi_long) == approx(expect_oi_long)
    assert int(actual_oi_short) == approx(expect_oi_short)


def test_ois_is_zero_when_no_positions(market_state, feed):
    actual_oi_long, actual_oi_short = market_state.ois(feed)
    assert actual_oi_long == 0
    assert actual_oi_short == 0


def test_ois_reverts_when_no_market(market_state, rando):
    with reverts("OVLV1:!market"):
        _, _ = market_state.ois(rando)


def test_cap_oi(market_state, market, feed):
    actual = market_state.capOi(feed)

    data = feed.latest()
    cap = market.params(RiskParameter.CAP_NOTIONAL.value)
    cap = market.capNotionalAdjustedForBounds(data, cap)
    mid = mid_from_feed(data)
    expect = int(Decimal(cap) * Decimal(1e18) / Decimal(mid))

    assert expect == approx(int(actual))


def test_cap_oi_reverts_when_no_market(market_state, rando):
    with reverts("OVLV1:!market"):
        _ = market_state.capOi(rando)


def test_fraction_of_cap_oi(market_state, feed):
    oi = 1000000000000000000  # 1
    actual = market_state.fractionOfCapOi(feed, oi)

    # NOTE: capOi tested above
    cap_oi = market_state.capOi(feed)
    expect = int(Decimal(oi) * Decimal(1e18) / Decimal(cap_oi))

    assert expect == approx(int(actual))


def test_fraction_of_cap_oi_when_cap_zero(market_state, factory, market,
                                          feed, gov):
    oi = 1000000000000000000  # 1

    # set capNotional risk param to zero on market
    factory.setRiskParam(feed, RiskParameter.CAP_NOTIONAL.value, 0,
                         {"from": gov})
    assert market.params(RiskParameter.CAP_NOTIONAL.value) == 0

    expect = 2**256 - 1
    actual = market_state.fractionOfCapOi(feed, oi)
    assert expect == actual


def test_fraction_of_cap_oi_reverts_when_no_market(market_state, rando):
    oi = 1000000000000000000  # 1
    with reverts("OVLV1:!market"):
        _ = market_state.fractionOfCapOi(rando, oi)


def test_funding_rate_when_long_gt_short(market_state, feed, ovl, market,
                                         alice, bob):
    # long > short
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

    # build position for bob
    market.build(input_collateral_bob, input_leverage_bob,
                 input_is_long_bob, input_price_limit_bob, {"from": bob})

    # get current ois state
    # NOTE: ois tested above
    oi_long, oi_short = market_state.ois(feed)
    oi_imb = oi_long - oi_short
    oi_tot = oi_long + oi_short

    # get k risk param
    k = market.params(RiskParameter.K.value)

    # calculate instantaneous funding rate
    expect = int(Decimal(2 * k) * Decimal(oi_imb) / Decimal(oi_tot))
    actual = market_state.fundingRate(feed)

    assert expect == approx(int(actual))

    # forward the chain and check instantaneous funding
    # rate still matches
    chain.mine(timedelta=86400)

    # get current ois state
    # NOTE: ois tested above
    oi_long, oi_short = market_state.ois(feed)
    oi_imb = oi_long - oi_short
    oi_tot = oi_long + oi_short

    # calculate instantaneous funding rate
    expect = int(Decimal(2 * k) * Decimal(oi_imb) / Decimal(oi_tot))
    actual = market_state.fundingRate(feed)

    assert expect == approx(int(actual))


def test_funding_rate_when_short_gt_long(market_state, feed, ovl, market,
                                         alice, bob):
    # long > short
    # alice build params
    input_collateral_alice = 10000000000000000000  # 10
    input_leverage_alice = 1000000000000000000  # 1
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # bob build params
    input_collateral_bob = 20000000000000000000  # 20
    input_leverage_bob = 1000000000000000000  # 1
    input_is_long_bob = False
    input_price_limit_bob = 0

    # approve max for both
    ovl.approve(market, 2**256-1, {"from": alice})
    ovl.approve(market, 2**256-1, {"from": bob})

    # build position for alice
    market.build(input_collateral_alice, input_leverage_alice,
                 input_is_long_alice, input_price_limit_alice, {"from": alice})

    # build position for bob
    market.build(input_collateral_bob, input_leverage_bob,
                 input_is_long_bob, input_price_limit_bob, {"from": bob})

    # get current ois state
    # NOTE: ois tested above
    oi_long, oi_short = market_state.ois(feed)
    oi_imb = oi_long - oi_short
    oi_tot = oi_long + oi_short

    # get k risk param
    k = market.params(RiskParameter.K.value)

    # calculate instantaneous funding rate
    expect = int(Decimal(2 * k) * Decimal(oi_imb) / Decimal(oi_tot))
    actual = market_state.fundingRate(feed)

    assert expect == approx(int(actual))

    # forward the chain and check instantaneous funding
    # rate still matches
    chain.mine(timedelta=86400)

    # get current ois state
    # NOTE: ois tested above
    oi_long, oi_short = market_state.ois(feed)
    oi_imb = oi_long - oi_short
    oi_tot = oi_long + oi_short

    # calculate instantaneous funding rate
    expect = int(Decimal(2 * k) * Decimal(oi_imb) / Decimal(oi_tot))
    actual = market_state.fundingRate(feed)

    assert expect == approx(int(actual))


def test_funding_rate_when_oi_zero(market_state, feed):
    expect = 0
    actual = market_state.fundingRate(feed)
    assert expect == actual


def test_circuit_breaker_level(market_state, feed, ovl, market,
                               alice):
    # have alice initially build a long to init volume
    input_collateral = 10000000000000000000
    input_leverage = 1000000000000000000
    input_is_long = True
    input_price_limit = 2**256 - 1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    tx = market.build(input_collateral, input_leverage, input_is_long,
                      input_price_limit, {"from": alice})
    pos_id = tx.return_value

    # unwind the position for alice
    fraction = 1000000000000000000  # 1
    output_price_limit = 0
    market.unwind(pos_id, fraction, output_price_limit, {"from": alice})

    # check snapshotMinted registers the burned losses from trade
    snap = market.snapshotMinted()
    (_, _, accumulator) = snap

    # check circuit breaker level matches expect
    one = 1000000000000000000
    expect = market.capNotionalAdjustedForCircuitBreaker(one)
    actual = market_state.circuitBreakerLevel(feed)
    assert expect == actual


# TODO: test circuit breaker level using mock feed to mint some OVL on unwind
