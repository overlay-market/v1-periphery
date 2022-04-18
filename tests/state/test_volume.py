import pytest
from pytest import approx
from brownie import chain
from brownie.test import given, strategy
from decimal import Decimal

from .utils import RiskParameter, transform_snapshot


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@given(
    initial_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                              places=3),
    peek_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                           places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_volume_bid(state, market, feed, initial_fraction,
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

    # calculate what the volume bid should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = int(accumulator)
    actual = int(state.volumeBid(feed, fraction))

    assert expect == approx(actual)


@given(
    initial_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                              places=3),
    peek_fraction=strategy('decimal', min_value='0.001', max_value='0.500',
                           places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_volume_ask(state, market, feed, initial_fraction,
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

    # calculate what the volume ask should be given snapshot value
    timestamp = chain[-1]['timestamp']
    window = micro_window
    value = fraction
    snap = transform_snapshot(snap, timestamp, window, value)
    (_, _, accumulator) = snap

    expect = int(accumulator)
    actual = int(state.volumeAsk(feed, fraction))

    assert expect == approx(actual)


@given(
    initial_fraction_alice=strategy('decimal', min_value='0.001',
                                    max_value='0.500', places=3),
    initial_fraction_bob=strategy('decimal', min_value='0.001',
                                  max_value='0.500', places=3),
    dt=strategy('uint256', min_value='10', max_value='600'))
def test_volumes(state, market, feed, ovl, alice, bob,
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

    expect_volume_bid = int(accumulator_bid)
    expect_volume_ask = int(accumulator_ask)

    (actual_volume_bid, actual_volume_ask) = state.volumes(feed)

    assert expect_volume_bid == approx(int(actual_volume_bid))
    assert expect_volume_ask == approx(int(actual_volume_ask))
