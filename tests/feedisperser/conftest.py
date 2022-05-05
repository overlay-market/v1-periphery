import pytest
from brownie import Contract, OverlayV1FeeDisperser, web3


@pytest.fixture(scope="module")
def ovl_v1_core(pm):
    return pm("overlay-market/v1-core@1.0.0-beta.2")


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
def minter_role():
    yield web3.solidityKeccak(['string'], ["MINTER"])


@pytest.fixture(scope="module")
def burner_role():
    yield web3.solidityKeccak(['string'], ["BURNER"])


@pytest.fixture(scope="module")
def governor_role():
    yield web3.solidityKeccak(['string'], ["GOVERNOR"])


@pytest.fixture(scope="module", params=[8000000])
def create_token(ovl_v1_core, gov, alice, bob, governor_role, request):
    sup = request.param

    def create_token(supply=sup):
        ovl = ovl_v1_core.OverlayV1Token
        tok = gov.deploy(ovl)
        tok.grantRole(governor_role, gov, {"from": gov})
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
def usdc():
    yield Contract.from_explorer("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")


@pytest.fixture(scope="module")
def pool_daiweth_30bps():
    yield Contract.from_explorer("0xC2e9F25Be6257c210d7Adf0D4Cd6E3E881ba25f8")


@pytest.fixture(scope="module")
def pool_uniweth_30bps():
    # to be used as example ovlweth pool
    yield Contract.from_explorer("0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801")


@pytest.fixture(scope="module")
def pool_daiusdc_5bps():
    yield Contract.from_explorer("0x6c6Bc977E13Df9b0de53b251522280BB72383700")


@pytest.fixture(scope="module")
def uni_factory():
    yield Contract.from_explorer("0x1F98431c8aD98523631AE4a59f267346ea31F984")


@pytest.fixture(scope="module")
def pos_manager():
    yield Contract.from_explorer("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")


@pytest.fixture(scope="module")
def staker():
    # NOTE: For testing only
    yield Contract.from_explorer("0xf574E14f28ACb46aF71c42d827CD4Ff389E7723D")


@pytest.fixture(scope="module", params=[(2592000, 86400, 31536000)])
def create_fee_disperser(ovl, staker, rando, request):
    min_replenish_duration, incentive_lead, incentive_duration = request.param

    def create_fee_disperser(repl_duration=min_replenish_duration,
                             lead=incentive_lead, duration=incentive_duration):
        fee_disperser = rando.deploy(
            OverlayV1FeeDisperser, ovl, staker, repl_duration, lead, duration)
        return fee_disperser

    yield create_fee_disperser


@pytest.fixture(scope="module")
def fee_disperser(create_fee_disperser):
    yield create_fee_disperser()
