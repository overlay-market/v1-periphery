import pytest
from brownie import reverts
from collections import OrderedDict


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_add_incentive(fee_recipient, pool_daiweth_30bps, pool_uniweth_30bps,
                       gov, rando):
    # pool 1 incentive attributes
    expect_pool1_token0 = pool_daiweth_30bps.token0()
    expect_pool1_token1 = pool_daiweth_30bps.token1()
    expect_pool1_fee = pool_daiweth_30bps.fee()
    expect_pool1_weight = 1000000000000000000  # 1

    # add pool 1 incentive
    tx_pool1 = fee_recipient.addIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight, {"from": gov})

    # check pool 1 incentive stored
    # NOTE: should be 1 index as 0 index is empty for incentives array
    expect_pool1_incentive_id = 1
    expect_pool1_incentive = (
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight)
    actual_pool1_incentive = fee_recipient.incentives(
        expect_pool1_incentive_id, {"from": rando})
    assert expect_pool1_incentive == actual_pool1_incentive

    # check total weight increased
    expect_total_weight = 0
    expect_total_weight += expect_pool1_weight

    # check incentive id stored
    actual_pool1_incentive_id = fee_recipient.incentiveIds(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        {"from": rando})
    assert expect_pool1_incentive_id == actual_pool1_incentive_id

    # check the reversed token1, token0 pairings also stores incentive id
    actual_pool1_incentive_id = fee_recipient.incentiveIds(
        expect_pool1_token1, expect_pool1_token0, expect_pool1_fee,
        {"from": rando})
    assert expect_pool1_incentive_id == actual_pool1_incentive_id

    # test event emitted
    assert 'IncentiveAdded' in tx_pool1.events
    expect_pool1_event = OrderedDict({
        "user": gov.address,
        "id": expect_pool1_incentive_id,
        "weight": expect_pool1_weight
    })
    actual_pool1_event = tx_pool1.events["IncentiveAdded"][0]
    assert expect_pool1_event == actual_pool1_event

    # pool 2 incentive attributes
    expect_pool2_token0 = pool_uniweth_30bps.token0()
    expect_pool2_token1 = pool_uniweth_30bps.token1()
    expect_pool2_fee = pool_uniweth_30bps.fee()
    expect_pool2_weight = 3000000000000000000  # 3

    # add pool 2 incentive
    tx_pool2 = fee_recipient.addIncentive(
        expect_pool2_token0, expect_pool2_token1, expect_pool2_fee,
        expect_pool2_weight, {"from": gov})

    # check pool 2 incentive stored
    # NOTE: should be 2 index as 0 index is empty for incentives array
    expect_pool2_incentive_id = 2
    expect_pool2_incentive = (
        expect_pool2_token0, expect_pool2_token1, expect_pool2_fee,
        expect_pool2_weight)
    actual_pool2_incentive = fee_recipient.incentives(
        expect_pool2_incentive_id, {"from": rando})
    assert expect_pool2_incentive == actual_pool2_incentive

    # check total weight increased
    expect_total_weight += expect_pool2_weight

    # check incentive id stored
    actual_pool2_incentive_id = fee_recipient.incentiveIds(
        expect_pool2_token0, expect_pool2_token1, expect_pool2_fee,
        {"from": rando})
    assert expect_pool2_incentive_id == actual_pool2_incentive_id

    # check the reversed token1, token0 pairings also stores incentive id
    actual_pool2_incentive_id = fee_recipient.incentiveIds(
        expect_pool2_token1, expect_pool2_token0, expect_pool2_fee,
        {"from": rando})
    assert expect_pool2_incentive_id == actual_pool2_incentive_id

    # test event emitted
    assert 'IncentiveAdded' in tx_pool2.events
    expect_pool2_event = OrderedDict({
        "user": gov.address,
        "id": expect_pool2_incentive_id,
        "weight": expect_pool2_weight
    })
    actual_pool2_event = tx_pool2.events["IncentiveAdded"][0]
    assert expect_pool2_event == actual_pool2_event


def test_add_incentive_reverts_when_not_governor(fee_recipient,
                                                 pool_daiusdc_5bps, rando):
    # incentive attributes
    token0 = pool_daiusdc_5bps.token0()
    token1 = pool_daiusdc_5bps.token1()
    fee = pool_daiusdc_5bps.fee()
    weight = 1000000000000000000  # 1

    # attempt to add incentive from rando
    with reverts("OVLV1: !governor"):
        fee_recipient.addIncentive(
            token0, token1, fee, weight, {"from": rando})


def test_add_incentive_reverts_when_weight_zero(fee_recipient,
                                                pool_daiusdc_5bps, gov):
    # incentive attributes
    token0 = pool_daiusdc_5bps.token0()
    token1 = pool_daiusdc_5bps.token1()
    fee = pool_daiusdc_5bps.fee()
    weight = 0  # 0

    # attempt to add incentive with weight 0
    with reverts("OVLV1: incentive weight == 0"):
        fee_recipient.addIncentive(
            token0, token1, fee, weight, {"from": gov})


def test_add_incentive_reverts_when_incentive_exists(fee_recipient,
                                                     pool_daiweth_30bps, gov):
    # incentive attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()
    weight = 1000000000000000000  # 1

    # add incentive
    fee_recipient.addIncentive(token0, token1, fee, weight, {"from": gov})

    # attempt to add incentive when already exists
    with reverts("OVLV1: incentive exists"):
        fee_recipient.addIncentive(
            token0, token1, fee, weight, {"from": gov})


def test_add_incentive_reverts_when_uni_pool_not_exists(fee_recipient,
                                                        pool_daiusdc_5bps,
                                                        rando, gov):
    # incentive attributes
    token0 = pool_daiusdc_5bps.token0()
    token1 = pool_daiusdc_5bps.token1()
    fee = 0  # zero fee so pool won't exist
    weight = 1000000000000000000  # 1

    # attempt to add incentive when already exists
    with reverts("OVLV1: !UniswapV3Pool"):
        fee_recipient.addIncentive(
            token0, token1, fee, weight, {"from": gov})


def test_update_incentive(fee_recipient, pool_daiweth_30bps, gov, rando):
    # pool 1 incentive attributes
    expect_pool1_token0 = pool_daiweth_30bps.token0()
    expect_pool1_token1 = pool_daiweth_30bps.token1()
    expect_pool1_fee = pool_daiweth_30bps.fee()
    expect_pool1_weight_add = 1000000000000000000  # 1

    # add pool 1 incentive
    tx_add = fee_recipient.addIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight_add, {"from": gov})
    expect_pool1_id = tx_add.events["IncentiveAdded"][0]["id"]

    # total weight before update
    expect_total_weight = fee_recipient.totalWeight()

    # update the incentive for pool 1
    expect_pool1_weight_update = 3000000000000000000  # 3
    tx_updated = fee_recipient.updateIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight_update, {"from": gov})

    # check total weight updated
    expect_total_weight -= expect_pool1_weight_add
    expect_total_weight += expect_pool1_weight_update

    actual_total_weight = fee_recipient.totalWeight()
    assert expect_total_weight == actual_total_weight

    # check incentive weight attribute updated
    expect_incentive = (expect_pool1_token0, expect_pool1_token1,
                        expect_pool1_fee, expect_pool1_weight_update)
    actual_incentive = fee_recipient.incentives(expect_pool1_id)
    assert expect_incentive == actual_incentive

    # check event emitted
    assert "IncentiveUpdated" in tx_updated.events
    expect_event = OrderedDict({
        "user": gov.address,
        "id": expect_pool1_id,
        "weight": expect_pool1_weight_update
    })
    actual_event = tx_updated.events["IncentiveUpdated"][0]
    assert expect_event == actual_event


def test_update_incentive_to_weight_zero(fee_recipient, pool_daiweth_30bps,
                                         gov, rando):
    # incentive attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()
    weight = 1000000000000000000  # 1

    # add incentive
    fee_recipient.addIncentive(token0, token1, fee, weight, {"from": gov})

    # update incentive to zero weight
    weight = 0
    fee_recipient.updateIncentive(token0, token1, fee, weight, {"from": gov})

    # get the incentive from id
    (_, _, _, actual_weight) = fee_recipient.incentives(1, {"from": rando})
    expect_weight = 0
    assert expect_weight == actual_weight


def test_update_incentive_reverts_when_not_governor(fee_recipient,
                                                    pool_daiweth_30bps,
                                                    gov, rando):
    # incentive attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()
    weight = 1000000000000000000  # 1

    # add incentive
    fee_recipient.addIncentive(token0, token1, fee, weight, {"from": gov})

    # attempt to update incentive from rando
    with reverts("OVLV1: !governor"):
        fee_recipient.updateIncentive(
            token0, token1, fee, weight, {"from": rando})


def test_update_incentive_reverts_when_incentive_not_exists(fee_recipient,
                                                            pool_daiweth_30bps,
                                                            gov):
    # incentive attributes
    token0 = pool_daiweth_30bps.token0()
    token1 = pool_daiweth_30bps.token1()
    fee = pool_daiweth_30bps.fee()
    weight = 1000000000000000000  # 1

    # attempt to update incentive when does not exist
    with reverts("OVLV1: !incentive"):
        fee_recipient.updateIncentive(
            token0, token1, fee, weight, {"from": gov})
