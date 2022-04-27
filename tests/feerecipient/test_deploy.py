from brownie import OverlayV1FeeRecipient, reverts


def test_deploy_fee_recipient(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_lead = 86400
    incentive_duration = 31536000

    fee_recipient = rando.deploy(
        OverlayV1FeeRecipient, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration)

    # check immutables set
    assert fee_recipient.ovl() == ovl
    assert fee_recipient.staker() == staker
    assert fee_recipient.minReplenishDuration() == min_replenish_duration
    assert fee_recipient.incentiveLeadTime() == incentive_lead
    assert fee_recipient.incentiveDuration() == incentive_duration

    # check an empty incentive added to incentives array
    expect = (
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        0,
        0
    )
    actual = fee_recipient.incentives(0)
    assert expect == actual

    # check only one empty added
    with reverts():
        fee_recipient.incentives(1)


def test_deploy_reverts_when_incentive_lead_time_gt_max(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_duration = 31536000

    # check reverts if greater than max
    incentive_lead = staker.maxIncentiveStartLeadTime() + 1
    with reverts("OVLV1: incentiveLeadTime>max"):
        rando.deploy(
            OverlayV1FeeRecipient, ovl, staker, min_replenish_duration,
            incentive_lead, incentive_duration)

    # check deploys if equal to max
    incentive_lead = staker.maxIncentiveStartLeadTime()
    rando.deploy(
        OverlayV1FeeRecipient, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration)


def test_deploy_reverts_when_incentive_duration_gt_max(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_lead = 86400

    # check reverts if greater than max
    incentive_duration = staker.maxIncentiveDuration() + 1
    with reverts("OVLV1: incentiveDuration>max"):
        rando.deploy(
            OverlayV1FeeRecipient, ovl, staker, min_replenish_duration,
            incentive_lead, incentive_duration)

    # check deploys if equal to max
    incentive_duration = staker.maxIncentiveDuration()
    rando.deploy(
        OverlayV1FeeRecipient, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration)
