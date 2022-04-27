import pytest
from brownie import chain, reverts
from decimal import Decimal
from collections import OrderedDict


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def test_replenish_incentives(fee_recipient, staker, pool_daiweth_30bps,
                              pool_uniweth_30bps, ovl, gov, alice, rando):
    # pool 1 incentive attributes
    expect_pool1_token0 = pool_daiweth_30bps.token0()
    expect_pool1_token1 = pool_daiweth_30bps.token1()
    expect_pool1_fee = pool_daiweth_30bps.fee()
    expect_pool1_weight = 1000000000000000000  # 1

    # pool 2 incentive attributes
    expect_pool2_token0 = pool_uniweth_30bps.token0()
    expect_pool2_token1 = pool_uniweth_30bps.token1()
    expect_pool2_fee = pool_daiweth_30bps.fee()
    expect_pool2_weight = 3000000000000000000  # 3

    expect_total_weight = expect_pool1_weight + expect_pool2_weight  # 4

    # add incentives
    fee_recipient.addIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight, {"from": gov})
    fee_recipient.addIncentive(
        expect_pool2_token0, expect_pool2_token1, expect_pool2_fee,
        expect_pool2_weight, {"from": gov})

    # add fee rewards to fee recipient
    expect_total_reward = 100000000000000000000  # 100
    ovl.transfer(fee_recipient.address, expect_total_reward, {"from": alice})

    # replenish the incentives
    tx = fee_recipient.replenishIncentives({"from": rando})

    # check block timestamp last updated
    expect_timestamp_last = chain[tx.block_number]['timestamp']
    actual_timestamp_last = fee_recipient.blockTimestampLast()
    assert expect_timestamp_last == actual_timestamp_last

    # check balance of fee amount of rewards sent from fee recipient
    # to staker
    expect_balance_fee_recipient = 0
    actual_balance_fee_recipient = ovl.balanceOf(fee_recipient.address)
    assert expect_balance_fee_recipient == actual_balance_fee_recipient

    expect_balance_staker = expect_total_reward
    actual_balance_staker = ovl.balanceOf(staker.address)
    assert expect_balance_staker == actual_balance_staker

    # check incentive added to staker
    expect_incentive_lead_time = fee_recipient.incentiveLeadTime()
    expect_incentive_duration = fee_recipient.incentiveDuration()

    # calculate the incentive keys
    expect_reward_token = ovl.address
    expect_start_time = expect_timestamp_last + expect_incentive_lead_time
    expect_end_time = expect_start_time + expect_incentive_duration
    expect_min_width = 1774440  # for 30bps fee
    expect_refundee = fee_recipient.address

    # TODO: fix compute_incentive_id
    expect_pool1_key = (expect_reward_token, pool_daiweth_30bps.address,
                        expect_start_time, expect_end_time, expect_min_width,
                        expect_refundee)
    expect_pool1_incentive_id = fee_recipient.getStakerIncentiveId(
        expect_pool1_key)

    # TODO: fix compute_incentive_id
    expect_pool2_key = (expect_reward_token, pool_uniweth_30bps.address,
                        expect_start_time, expect_end_time, expect_min_width,
                        expect_refundee)
    expect_pool2_incentive_id = fee_recipient.getStakerIncentiveId(
        expect_pool2_key)

    # calculate share of rewards each pool receives
    expect_pool1_reward_fraction = Decimal(
        expect_pool1_weight) / Decimal(expect_total_weight)
    expect_pool1_reward = int(
        Decimal(expect_total_reward) * expect_pool1_reward_fraction)

    expect_pool2_reward_fraction = Decimal(
        expect_pool2_weight) / Decimal(expect_total_weight)
    expect_pool2_reward = int(
        Decimal(expect_total_reward) * expect_pool2_reward_fraction)

    # check incentive created on staker with expected reward
    (actual_pool1_reward, _, _) = staker.incentives(expect_pool1_incentive_id)
    (actual_pool2_reward, _, _) = staker.incentives(expect_pool2_incentive_id)

    # TODO: fix
    assert expect_pool1_reward == actual_pool1_reward
    assert expect_pool2_reward == actual_pool2_reward

    # check event emitted
    assert 'IncentivesReplenished' in tx.events
    expect_event = OrderedDict({
        "user": rando.address,
        "rewards": [0, expect_pool1_reward, expect_pool2_reward],
        "startTime": expect_start_time,
        "endTime": expect_end_time,
    })
    actual_event = tx.events['IncentivesReplenished']
    assert expect_event == actual_event


def test_replenish_incentives_reverts_when_total_weight_zero(
        fee_recipient, rando):
    with reverts("OVLV1: !incentives"):
        fee_recipient.replenishIncentives({"from": rando})


def test_replenish_incentives_reverts_when_total_reward_zero(
        fee_recipient, pool_daiweth_30bps, rando, gov):
    # pool 1 incentive attributes
    expect_pool1_token0 = pool_daiweth_30bps.token0()
    expect_pool1_token1 = pool_daiweth_30bps.token1()
    expect_pool1_fee = pool_daiweth_30bps.fee()
    expect_pool1_weight = 1000000000000000000  # 1

    # add incentives
    fee_recipient.addIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight, {"from": gov})

    with reverts("OVLV1: reward == 0"):
        fee_recipient.replenishIncentives({"from": rando})


def test_replenish_incentives_reverts_when_less_than_min_duration(
        fee_recipient, pool_daiweth_30bps, rando, alice, ovl, gov):
    # pool 1 incentive attributes
    expect_pool1_token0 = pool_daiweth_30bps.token0()
    expect_pool1_token1 = pool_daiweth_30bps.token1()
    expect_pool1_fee = pool_daiweth_30bps.fee()
    expect_pool1_weight = 1000000000000000000  # 1

    # add incentives
    fee_recipient.addIncentive(
        expect_pool1_token0, expect_pool1_token1, expect_pool1_fee,
        expect_pool1_weight, {"from": gov})

    # add fee rewards to fee recipient
    expect_total_reward = 100000000000000000000  # 100
    ovl.transfer(fee_recipient.address, expect_total_reward, {"from": alice})

    # replenish first then check can't do it again for min duration
    fee_recipient.replenishIncentives({"from": rando})

    # add fee rewards to fee recipient
    expect_total_reward = 200000000000000000000  # 200
    ovl.transfer(fee_recipient.address, expect_total_reward, {"from": alice})

    # check won't replenish
    with reverts("OVLV1: duration<min"):
        fee_recipient.replenishIncentives({"from": rando})

    # check does replenish if enough time has passed
    dt = fee_recipient.minReplenishDuration()
    chain.mine(timedelta=dt+1)
    fee_recipient.replenishIncentives({"from": rando})

# TODO: test_replenish_many_incentives
