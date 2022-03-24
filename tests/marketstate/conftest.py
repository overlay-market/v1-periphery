import pytest
from brownie import interface, Contract, OverlayV1MarketState


@pytest.fixture(scope="module")
def ovl_v1_core(pm):
    return pm("overlay-market/v1-core@1.0.0-beta.1")


@pytest.fixture(scope="module")
def gov(accounts):
    yield accounts[0]


@pytest.fixture(scope="module")
def alice(accounts):
    yield accounts[1]


@pytest.fixture(scope="module")
def bob(accounts):
    yield accounts[2]


@pytest.fixture(scope="module")
def rando(accounts):
    yield accounts[3]


@pytest.fixture(scope="module")
def fee_recipient(accounts):
    yield accounts[4]


@pytest.fixture(scope="module", params=[8000000])
def create_token(ovl_v1_core, gov, alice, bob, request):
    sup = request.param

    def create_token(supply=sup):
        ovl = ovl_v1_core.OverlayV1Token
        tok = gov.deploy(ovl)
        tok.mint(gov, supply * 10 ** tok.decimals(), {"from": gov})
        tok.transfer(alice, (supply/2) * 10 ** tok.decimals(), {"from": gov})
        tok.transfer(bob, (supply/2) * 10 ** tok.decimals(), {"from": gov})
        return tok

    yield create_token


@pytest.fixture(scope="module")
def ovl(create_token):
    yield create_token()


@pytest.fixture(scope="module")
def dai():
    yield Contract.from_explorer("0x6B175474E89094C44Da98b954EedeAC495271d0F")


@pytest.fixture(scope="module")
def weth():
    yield Contract.from_explorer("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture(scope="module")
def uni():
    # to be used as example ovl
    yield Contract.from_explorer("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984")


@pytest.fixture(scope="module")
def pool_daiweth_30bps():
    yield Contract.from_explorer("0xC2e9F25Be6257c210d7Adf0D4Cd6E3E881ba25f8")


@pytest.fixture(scope="module")
def pool_uniweth_30bps():
    # to be used as example ovlweth pool
    yield Contract.from_explorer("0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801")


@pytest.fixture(scope="module", params=[(600, 3600)])
def create_feed_factory(ovl_v1_core, gov, pool_uniweth_30bps, weth,
                        uni, request):
    micro, macro = request.param
    oe_pool = pool_uniweth_30bps.address
    tok = uni.address

    def create_feed_factory(ovlweth_pool=oe_pool, ovl=tok, micro_window=micro,
                            macro_window=macro):
        # deploy feed factory
        ovl_uni_feed_factory = ovl_v1_core.OverlayV1UniswapV3Factory
        feed_factory = gov.deploy(ovl_uni_feed_factory, ovlweth_pool, ovl,
                                  micro_window, macro_window)
        return feed_factory

    yield create_feed_factory


@pytest.fixture(scope="module")
def feed_factory(create_feed_factory):
    yield create_feed_factory()


@pytest.fixture(scope="module", params=[(600, 3600)])
def create_feed(feed_factory, pool_daiweth_30bps, weth, dai, alice):
    def create_feed():
        market_pool = pool_daiweth_30bps
        market_base_token = weth
        market_quote_token = dai
        market_base_amount = 1000000000000000000  # 1e18

        tx = feed_factory.deployFeed(market_pool, market_base_token,
                                     market_quote_token,
                                     market_base_amount, {"from": alice})
        feed_addr = tx.return_value
        return interface.IOverlayV1Feed(feed_addr)

    yield create_feed


@pytest.fixture(scope="module")
def feed(create_feed):
    yield create_feed()


@pytest.fixture(scope="module")
def create_factory(ovl_v1_core, gov, fee_recipient, feed_factory, ovl):
    def create_factory(tok=ovl, recipient=fee_recipient):
        ovl_factory = ovl_v1_core.OverlayV1Factory

        # create the market factory
        factory = gov.deploy(ovl_factory, tok, recipient)

        # grant market factory token admin role
        tok.grantRole(tok.ADMIN_ROLE(), factory, {"from": gov})

        # grant gov the governor role on token to access factory methods
        tok.grantRole(tok.GOVERNOR_ROLE(), gov, {"from": gov})

        # add feed factory as approved for market factory to deploy markets on
        factory.addFeedFactory(feed_factory, {"from": gov})

        return factory

    yield create_factory


@pytest.fixture(scope="module")
def factory(create_factory):
    yield create_factory()


@pytest.fixture(scope="module")
def create_market(ovl_v1_core, factory, feed_factory, feed, gov):
    def create_market(feed, factory, risk_params, governance=gov):
        tx = factory.deployMarket(feed_factory, feed, risk_params,
                                  {"from": gov})
        market_addr = tx.return_value
        market = interface.IOverlayV1Market(market_addr)
        return market

    yield create_market


@pytest.fixture(scope="module", params=[(
    1220000000000,  # k
    500000000000000000,  # lmbda
    2500000000000000,  # delta
    5000000000000000000,  # capPayoff
    800000000000000000000000,  # capNotional
    5000000000000000000,  # capLeverage
    2592000,  # circuitBreakerWindow
    66670000000000000000000,  # circuitBreakerMintTarget
    100000000000000000,  # maintenanceMarginFraction
    100000000000000000,  # maintenanceMarginBurnRate
    10000000000000000,  # liquidationFeeRate
    750000000000000,  # tradingFeeRate
    100000000000000,  # minCollateral
    25000000000000,  # priceDriftUpperLimit
)])
def market(gov, feed, factory, ovl, create_market, request):
    risk_params = request.param
    yield create_market(feed=feed, factory=factory, risk_params=risk_params,
                        governance=gov)


@pytest.fixture(scope="module")
def create_market_state(rando, ovl):
    def create_market_state(factory, deployer=rando):
        market_state = deployer.deploy(OverlayV1MarketState, factory)
        return market_state

    yield create_market_state


@pytest.fixture(scope="module")
def market_state(create_market_state, factory):
    yield create_market_state(factory)
