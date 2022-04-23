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


def test_uni_factory_fixture(uni_factory):
    uni_factory.owner() == "0x1a9C8182C09F50C8318d769245beA52c32BE35BC"


def test_pos_manager_fixture(pos_manager, uni_factory):
    pos_manager.name() == "Uniswap V3 Positions NFT-V1"
    pos_manager.factory() == uni_factory


def test_staker_fixture(staker, uni_factory, pos_manager):
    staker.factory() == uni_factory
    staker.nonfungiblePositionManager() == pos_manager
    staker.maxIncentiveStartLeadTime() == 2592000
    staker.maxIncentiveDuration() == 63072000


def test_fee_recipient_fixture(fee_recipient, ovl, staker):
    fee_recipient.ovl() == ovl
    fee_recipient.staker() == staker

    fee_recipient.minReplenishDuration() == 2592000
    fee_recipient.incentiveLeadTime() == 86400
    fee_recipient.incentiveDuration() == 31536000
