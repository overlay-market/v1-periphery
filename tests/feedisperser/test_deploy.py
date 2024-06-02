from brownie import OverlayV1FeeDisperser, reverts


def test_deploy_fee_disperser(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_lead = 86400
    incentive_duration = 31536000
    fee_burn_rate = 100000000000000000  # 0.1

    fee_disperser = rando.deploy(
        OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration, fee_burn_rate)

    # check immutables set
    assert fee_disperser.ovl() == ovl
    assert fee_disperser.staker() == staker
    assert fee_disperser.minReplenishDuration() == min_replenish_duration
    assert fee_disperser.incentiveLeadTime() == incentive_lead
    assert fee_disperser.incentiveDuration() == incentive_duration
    assert fee_disperser.feeBurnRate() == fee_burn_rate

    # check an empty incentive added to incentives array
    expect = (
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        0,
        0
    )
    actual = fee_disperser.incentives(0)
    assert expect == actual

    # check only one empty added
    with reverts():
        fee_disperser.incentives(1)


def test_deploy_reverts_when_incentive_lead_time_gt_max(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_duration = 31536000
    fee_burn_rate = 0

    # check reverts if greater than max
    incentive_lead = staker.maxIncentiveStartLeadTime() + 1
    with reverts("OVLV1: incentiveLeadTime>max"):
        rando.deploy(
            OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
            incentive_lead, incentive_duration, fee_burn_rate)

    # check deploys if equal to max
    incentive_lead = staker.maxIncentiveStartLeadTime()
    rando.deploy(
        OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration, fee_burn_rate)


def test_deploy_reverts_when_incentive_duration_gt_max(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_lead = 86400
    fee_burn_rate = 0

    # check reverts if greater than max
    incentive_duration = staker.maxIncentiveDuration() + 1
    with reverts("OVLV1: incentiveDuration>max"):
        rando.deploy(
            OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
            incentive_lead, incentive_duration, fee_burn_rate)

    # check deploys if equal to max
    incentive_duration = staker.maxIncentiveDuration()
    rando.deploy(
        OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration, fee_burn_rate)


def test_deploy_reverts_when_fee_burn_rate_gt_max(ovl, staker, rando):
    min_replenish_duration = 2592000
    incentive_duration = 31536000
    incentive_lead = 86400
    fee_burn_rate = 1000000000000000000

    # check reverts if greater than max
    fee_burn_rate = 1000000000000000001
    with reverts("OVLV1: feeBurnRate>max"):
        rando.deploy(
            OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
            incentive_lead, incentive_duration, fee_burn_rate)

    # check deploys if equal to max
    fee_burn_rate = 1000000000000000000
    rando.deploy(
        OverlayV1FeeDisperser, ovl, staker, min_replenish_duration,
        incentive_lead, incentive_duration, fee_burn_rate)
