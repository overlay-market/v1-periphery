import pytest
from pytest import approx
from brownie import reverts
from decimal import Decimal


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_calc_incentive_reward(fee_disperser, pool_daiweth_30bps):
    # reward attribute
    total_reward = 100000000000000000000  # 100

    # uni pool attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()

    # weight attributes
    weight = 1000000000000000000  # 1
    total_weight = 2000000000000000000  # 2

    # build the incentive struct
    incentive = (token0, token1, fee, weight)

    # check expect in line with actual
    expect = int((Decimal(weight) / Decimal(total_weight))
                 * Decimal(total_reward))
    actual = int(fee_disperser.calcIncentiveReward(
        incentive, total_reward, total_weight))
    assert expect == approx(actual)


def test_calc_incentive_reward_when_weight_zero(fee_disperser,
                                                pool_daiweth_30bps):
    # reward attribute
    total_reward = 100000000000000000000  # 100

    # uni pool attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()

    # weight attributes
    weight = 0
    total_weight = 2000000000000000000  # 2

    # build the incentive struct
    incentive = (token0, token1, fee, weight)

    # check expect in line with actual
    expect = 0
    actual = fee_disperser.calcIncentiveReward(
        incentive, total_reward, total_weight)
    assert expect == actual


def test_is_incentive(fee_disperser, pool_daiweth_30bps, gov):
    # uni pool attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()

    # check is incentive when no incentive has been added yet
    expect = False
    actual = fee_disperser.isIncentive(token0, token1, fee)
    assert expect == actual

    # add the incentive
    # NOTE: addIncentive() tests in test_setters.py
    weight = 1000000000000000000  # 1
    fee_disperser.addIncentive(token0, token1, fee, weight, {"from": gov})

    # check is incentive after incentives has been added
    expect = True
    actual = fee_disperser.isIncentive(token0, token1, fee)
    assert expect == actual


def test_get_incentive_index(fee_disperser, pool_daiweth_30bps, gov):
    # uni pool attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()

    # add the incentive
    # NOTE: addIncentive() tests in test_setters.py
    weight = 1000000000000000000  # 1
    fee_disperser.addIncentive(token0, token1, fee, weight, {"from": gov})

    # check get incentive idx after incentives has been added
    # NOTE: should be idx=1 given initialize with an empty zero element
    expect = 1
    actual = fee_disperser.getIncentiveIndex(token0, token1, fee)
    assert expect == actual


def test_get_incentive_index_reverts_when_no_incentive(fee_disperser,
                                                       pool_daiweth_30bps,
                                                       gov):
    # uni pool attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()

    # check reverts if no incentive added yet
    with reverts("OVLV1: !incentive"):
        fee_disperser.getIncentiveIndex(token0, token1, fee)
