import pytest
from brownie import reverts


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_market(state, market, feed):
    expect = market
    actual = state.market(feed)
    assert expect == actual


def test_market_reverts_when_feed_not_market(state, rando):
    with reverts("OVLV1:!market"):
        _ = state.market(rando)


def test_data(state, feed):
    expect = feed.latest()
    actual = state.data(feed)
    assert expect == actual
