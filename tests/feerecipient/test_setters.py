from collections import OrderedDict
# from brownie import reverts


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


def test_add_incentive_reverts_when_not_governor(fee_recipient):
    pass


def test_add_incentive_reverts_when_weight_zero(fee_recipient):
    pass


def test_add_incentive_reverts_when_incentive_exists(fee_recipient):
    pass


def test_add_incentive_reverts_when_uni_pool_not_exists(fee_recipient):
    pass


def test_update_incentive(fee_recipient):
    pass


def test_update_incentive_reverts_when_not_governor(fee_recipient):
    pass


def test_update_incentive_reverts_when_incentive_not_exists(fee_recipient):
    pass
