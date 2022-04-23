// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Token.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";

import "@uniswap/v3-core/contracts/interfaces/IERC20Minimal.sol";

import "./interfaces/uniswap/v3-staker/IUniswapV3Staker.sol";

contract OverlayV1FeeRecipient {
    using FixedPoint for uint256;

    IOverlayV1Token public immutable ovl; // overlay token

    // staker attributes
    IUniswapV3Staker public immutable staker; // uniswap v3 staker
    uint256 public immutable minReplenishDuration; // min time between replenish calls

    // new staker incentive attributes
    uint256 public immutable incentiveLeadTime; // lead time for incentive start
    uint256 public immutable incentiveDuration; // duration of incentive when replenished

    // active governance determined incentives for Uni V3 pools
    struct Incentive {
        address token0;
        address token1;
        uint24 fee;
        uint256 weight;
    }
    Incentive[] public incentives;
    uint256 public totalWeight;

    struct Span {
        uint256 startTime;
        uint256 endTime;
    }
    // registry of created incentive start and end times;
    // for a given index in incentives array above returns Span
    mapping(uint256 => Span) public spans;

    // last time incentives were replenished with rewards
    uint256 public blockTimestampLast;

    // event emitted on replenish incentive
    event IncentiveReplenished(
        uint256 indexed incentiveId,
        uint256 startTime,
        uint256 endTime,
        uint256 reward
    );

    // governor modifier for governance sensitive functions
    modifier onlyGovernor() {
        require(ovl.hasRole(GOVERNOR_ROLE, msg.sender), "OVLV1: !governor");
        _;
    }

    constructor(
        IOverlayV1Token _ovl,
        IUniswapV3Staker _staker,
        uint256 _minReplenishDuration,
        uint256 _incentiveLeadTime,
        uint256 _incentiveDuration
    ) {
        ovl = _ovl;
        staker = _staker;

        // TODO: requires on these values
        minReplenishDuration = _minReplenishDuration;
        incentiveLeadTime = _incentiveLeadTime;
        incentiveDuration = _incentiveDuration;
    }

    /// @notice Creates new liquidity mining incentives using all
    /// @notice trading fees currently housed in this contract
    function replenishIncentives() external {
        uint256 blockTimestamp = block.timestamp;
        require(blockTimestamp > blockTimestampLast + minReplenishDuration, "OVLV1: duration<min");

        // needed span attributes for start and end of new incentives
        uint256 startTime = blockTimestamp + incentiveLeadTime;
        uint256 endTime = startTime + incentiveDuration;

        // total reward to be given out should be current balance of fees
        uint256 totalReward = ovl.balanceOf(address(this));

        // for each incentive, calculate reward then replenish through staker
        // TODO: gas issue here?
        uint256 length = incentives.length;
        for (uint256 i = 0; i < length; i++) {
            Incentive memory incentive = incentives[i];
            uint256 reward = _calcReward(incentive, totalReward);
            _replenishIncentive(incentive, startTime, endTime, address(this), reward);
            emit IncentiveReplenished(i, startTime, endTime, reward);
        }

        // set the last timestamp replenished
        blockTimestampLast = blockTimestamp;
    }

    /// @notice Calculates the reward amount to allocate to the given incentive
    /// @dev mul/div down with fraction to avoid transferring more than totalReward
    function _calcReward(Incentive memory incentive, uint256 totalReward)
        private
        returns (uint256 reward_)
    {
        // div down to avoid transferring more
        uint256 fraction = incentive.weight.divDown(totalWeight);
        reward_ = totalReward.mulDown(fraction);
    }

    /// @notice Creates new liquidity mining incentive for given reward
    /// @notice over max range
    function _replenishIncentive(
        Incentive memory incentive,
        uint256 startTime,
        uint256 endTime,
        address refundee,
        uint256 reward
    ) private {
        staker.createIncentiveWithMaxRange(
            IERC20Minimal(address(ovl)),
            startTime,
            endTime,
            refundee,
            reward,
            incentive.token0,
            incentive.token1,
            incentive.fee
        );
    }

    // TODO: governance sensitive functions for liquidity mining incentives
    // TODO: MUST UPDATE TOTAL WEIGHT VARIABLE
    // TODO: addIncentive() onlyGovernor
    // TODO: updateIncentive() onlyGovernor => updates weight on incentive
    // TODO: removeIncentive() onlyGovernor => _update() weight to zero
}
