import pytest
from pytest import approx
from brownie import chain
from brownie.test import given, strategy
from decimal import Decimal

from .utils import RiskParameter, mid_from_feed, transform_snapshot


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_mid(state, market, feed):
    data = feed.latest()

    expect = int(mid_from_feed(data))
    actual = state.mid(market)

    assert expect == approx(actual)


@given(
    fraction=strategy('decimal', min_value='0.001', max_value='2.000',
                      places=3))
def test_bid(state, market, feed, fraction):
    fraction = int(fraction * Decimal(1e18))
    snap = market.snapshotVolumeBid()
    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the bid should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = market.bid(data, accumulator)
    actual = state.bid(market, fraction)
    assert expect == actual


@given(
    initial_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                              places=3),
    peek_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                           places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_bid_when_oi_on_market(state, market, feed, initial_fraction,
                               peek_fraction, dt, ovl, bob):
    # have bob initially build a short to init volume
    cap_notional = market.params(RiskParameter.CAP_NOTIONAL.value)
    input_collateral = initial_fraction * cap_notional
    input_leverage = 1000000000000000000
    input_is_long = False
    input_price_limit = 0

    # approve max for bob
    ovl.approve(market, 2**256-1, {"from": bob})

    # build position for bob
    market.build(input_collateral, input_leverage, input_is_long,
                 input_price_limit, {"from": bob})

    # mine the chain forward
    chain.mine(timedelta=dt)

    fraction = int(peek_fraction * Decimal(1e18))
    snap = market.snapshotVolumeBid()
    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the bid should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = int(market.bid(data, accumulator))
    actual = int(state.bid(market, fraction))
    assert expect == approx(actual)


@given(
    fraction=strategy('decimal', min_value='0.001', max_value='2.000',
                      places=3))
def test_ask(state, market, feed, fraction):
    fraction = int(fraction * Decimal(1e18))
    snap = market.snapshotVolumeAsk()
    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the ask should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = market.ask(data, accumulator)
    actual = state.ask(market, fraction)
    assert expect == actual


@given(
    initial_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                              places=3),
    peek_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                           places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_ask_when_oi_on_market(state, market, feed, initial_fraction,
                               peek_fraction, dt, ovl, alice):
    # have alice initially build a long to init volume
    cap_notional = market.params(RiskParameter.CAP_NOTIONAL.value)
    input_collateral = initial_fraction * cap_notional
    input_leverage = 1000000000000000000
    input_is_long = True
    input_price_limit = 2**256 - 1

    # approve max for alice
    ovl.approve(market, 2**256-1, {"from": alice})

    # build position for alice
    market.build(input_collateral, input_leverage, input_is_long,
                 input_price_limit, {"from": alice})

    # mine the chain forward
    chain.mine(timedelta=dt)

    fraction = int(peek_fraction * Decimal(1e18))
    snap = market.snapshotVolumeAsk()
    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the ask should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = int(market.ask(data, accumulator))
    actual = int(state.ask(market, fraction))
    assert expect == approx(actual)


def test_prices(state, market, feed):
    snap_bid = market.snapshotVolumeBid()
    snap_ask = market.snapshotVolumeAsk()
    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the bid should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    snap_bid = transform_snapshot(snap_bid, timestamp, window, 0)
    (_, _, accumulator_bid) = snap_bid

    # calculate what the ask should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    snap_ask = transform_snapshot(snap_ask, timestamp, window, 0)
    (_, _, accumulator_ask) = snap_ask

    expect_bid = int(market.bid(data, accumulator_bid))
    expect_ask = int(market.ask(data, accumulator_ask))
    expect_mid = int(mid_from_feed(data))

    (actual_bid, actual_ask, actual_mid) = state.prices(market)

    assert expect_bid == approx(int(actual_bid))
    assert expect_ask == approx(int(actual_ask))
    assert expect_mid == approx(int(actual_mid))


@given(
    initial_fraction_alice=strategy('decimal', min_value='0.001',
                                    max_value='0.500', places=3),
    initial_fraction_bob=strategy('decimal', min_value='0.001',
                                  max_value='0.500', places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_prices_when_oi_on_market(state, market, feed, ovl, alice, bob,
                                  initial_fraction_alice, initial_fraction_bob,
                                  dt):
    # have alice and bob initially build a long and short to init volume
    cap_notional = market.params(RiskParameter.CAP_NOTIONAL.value)
    input_collateral_alice = initial_fraction_alice * cap_notional
    input_leverage_alice = 1000000000000000000
    input_is_long_alice = True
    input_price_limit_alice = 2**256 - 1

    input_collateral_bob = initial_fraction_bob * cap_notional
    input_leverage_bob = 1000000000000000000
    input_is_long_bob = False
    input_price_limit_bob = 0

    # approve max for alice and bob
    ovl.approve(market, 2**256-1, {"from": alice})
    ovl.approve(market, 2**256-1, {"from": bob})

    # build positions for alice and bob
    market.build(input_collateral_alice, input_leverage_alice,
                 input_is_long_alice, input_price_limit_alice, {"from": alice})
    market.build(input_collateral_bob, input_leverage_bob, input_is_long_bob,
                 input_price_limit_bob, {"from": bob})

    # mine the chain forward
    chain.mine(timedelta=dt)

    data = feed.latest()
    (_, micro_window, _, _, _, _, _, _) = data

    # calculate what the bid should be given snapshot value
    snap_bid = market.snapshotVolumeBid()
    timestamp_bid = chain[-1]['timestamp']
    window_bid = micro_window
    snap_bid = transform_snapshot(snap_bid, timestamp_bid, window_bid, 0)
    (_, _, accumulator_bid) = snap_bid

    # calculate what the ask should be given snapshot value
    snap_ask = market.snapshotVolumeAsk()
    timestamp_ask = chain[-1]['timestamp']
    window_ask = micro_window
    snap_ask = transform_snapshot(snap_ask, timestamp_ask, window_ask, 0)
    (_, _, accumulator_ask) = snap_ask

    expect_bid = int(market.bid(data, accumulator_bid))
    expect_ask = int(market.ask(data, accumulator_ask))
    expect_mid = int(mid_from_feed(data))

    (actual_bid, actual_ask, actual_mid) = state.prices(market)

    assert expect_bid == approx(int(actual_bid))
    assert expect_ask == approx(int(actual_ask))
    assert expect_mid == approx(int(actual_mid))
