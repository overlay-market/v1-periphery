from .utils import RiskParameter


def test_ovl_fixture(ovl):
    assert ovl.decimals() == 18
    assert ovl.name() == "Overlay"
    assert ovl.symbol() == "OVL"
    assert ovl.totalSupply() == 8000000000000000000000000


def test_token_fixtures(dai, weth, uni):
    assert dai.name() == "Dai Stablecoin"
    assert weth.name() == "Wrapped Ether"
    assert uni.name() == "Uniswap"


def test_pool_fixtures(dai, weth, uni, uni_factory, pool_daiweth_30bps,
                       pool_uniweth_30bps):
    assert pool_daiweth_30bps.fee() == 3000
    assert pool_daiweth_30bps.token0() == dai
    assert pool_daiweth_30bps.token1() == weth
    assert pool_daiweth_30bps == uni_factory.getPool(dai, weth, 3000)

    assert pool_uniweth_30bps.fee() == 3000
    assert pool_uniweth_30bps.token0() == uni
    assert pool_uniweth_30bps.token1() == weth
    assert pool_uniweth_30bps == uni_factory.getPool(uni, weth, 3000)


def test_factory_fixture(factory, ovl, fee_recipient, market, feed_factory):
    assert factory.ovl() == ovl
    assert factory.feeRecipient() == fee_recipient

    assert factory.isFeedFactory(feed_factory) is True
    assert factory.isMarket(market) is True


def test_feed_fixture(feed, pool_daiweth_30bps, pool_uniweth_30bps, dai, weth,
                      uni, feed_factory):
    assert feed.marketPool() == pool_daiweth_30bps
    assert feed.ovlXPool() == pool_uniweth_30bps
    assert feed.ovl() == uni
    assert feed.x() == weth
    assert feed.marketBaseAmount() == 1000000000000000000
    assert feed.marketBaseToken() == weth
    assert feed.marketQuoteToken() == dai
    assert feed.microWindow() == 600
    assert feed.macroWindow() == 1800

    assert feed_factory.isFeed(feed) is True


def test_mock_feed_fixture(mock_feed, mock_feed_factory):
    assert mock_feed.price() == 1000000000000000000
    assert mock_feed.reserve() == 2000000000000000000000000
    assert mock_feed.microWindow() == 600
    assert mock_feed.macroWindow() == 1800


def test_market_fixture(market, feed, ovl, factory, gov,
                        minter_role, burner_role):
    # check addresses set properly
    assert market.ovl() == ovl
    assert market.feed() == feed
    assert market.factory() == factory

    # risk params
    expect_params = [
        1220000000000,
        500000000000000000,
        2500000000000000,
        5000000000000000000,
        800000000000000000000000,
        5000000000000000000,
        2592000,
        66670000000000000000000,
        100000000000000000,
        100000000000000000,
        50000000000000000,
        750000000000000,
        100000000000000,
        25000000000000,
        14
    ]
    actual_params = [market.params(name.value) for name in RiskParameter]
    assert expect_params == actual_params

    # check market has minter and burner roles on ovl token
    assert ovl.hasRole(minter_role, market) is True
    assert ovl.hasRole(burner_role, market) is True

    # check oi related quantities are zero
    assert market.oiLong() == 0
    assert market.oiShort() == 0
    assert market.oiLongShares() == 0
    assert market.oiShortShares() == 0

    # check timestamp update last is same as block when market was deployed
    assert market.timestampUpdateLast() != 0


def test_mock_market_fixture(mock_market, mock_feed, ovl, factory, gov,
                             minter_role, burner_role):
    # check addresses set properly
    assert mock_market.ovl() == ovl
    assert mock_market.feed() == mock_feed
    assert mock_market.factory() == factory

    # risk params
    expect_params = [
        1220000000000,
        500000000000000000,
        2500000000000000,
        5000000000000000000,
        800000000000000000000000,
        5000000000000000000,
        2592000,
        66670000000000000000000,
        100000000000000000,
        100000000000000000,
        50000000000000000,
        750000000000000,
        100000000000000,
        25000000000000,
        14
    ]
    actual_params = [mock_market.params(name.value) for name in RiskParameter]
    assert expect_params == actual_params

    # check market has minter and burner roles on ovl token
    assert ovl.hasRole(minter_role, mock_market) is True
    assert ovl.hasRole(burner_role, mock_market) is True

    # check oi related quantities are zero
    assert mock_market.oiLong() == 0
    assert mock_market.oiShort() == 0
    assert mock_market.oiLongShares() == 0
    assert mock_market.oiShortShares() == 0

    # check timestamp update last is same as block when market was deployed
    assert mock_market.timestampUpdateLast() != 0


def test_state_fixture(factory, state):
    assert state.factory() == factory
