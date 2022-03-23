// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@uniswap/v3-core/contracts/interfaces/IERC20Minimal.sol";
import "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import "./interfaces/overlay/v1-core/IOverlayV1Token.sol";
import "./interfaces/uniswap/v3-staker/IUniswapV3Staker.sol";
import "./libraries/uniswap/v3-core/TickMath.sol";

contract OverlayV1FeeRepository {
    IOverlayV1Token public immutable ovl; // overlay token

    // staker attributes
    IUniswapV3Staker public immutable staker; // uniswap v3 staker
    IUniswapV3Pool public immutable pool; // uniswap v3 pool
    uint256 public immutable minReplenishDuration; // min time between replenish calls

    // new incentive attributes
    uint256 public immutable incentiveLeadTime; // lead time for incentive start
    uint256 public immutable incentiveDuration; // duration of incentive when replenished

    uint256 public blockTimestampLast;

    constructor(
        IOverlayV1Token _ovl,
        IUniswapV3Staker _staker,
        IUniswapV3Pool _pool,
        uint256 _minReplenishDuration,
        uint256 _incentiveLeadTime,
        uint256 _incentiveDuration
    ) {
        ovl = _ovl;
        staker = _staker;
        pool = _pool;

        // TODO: requires on these values
        minReplenishDuration = _minReplenishDuration;
        incentiveLeadTime = _incentiveLeadTime;
        incentiveDuration = _incentiveDuration;
    }

    /// @notice Returns min width required for a max range
    /// @notice liquidity mining program based on pool properties
    function _minWidthMaxRange(IUniswapV3Pool _pool) private returns (int24 minWidth_) {
        int24 tickSpacing = _pool.tickSpacing();
        int24 maxTick = TickMath.MAX_TICK - TickMath.MAX_TICK % tickSpacing;
        int24 minTick = -maxTick;
        minWidth_ = maxTick - minTick;
    }

    /// @notice Creates a new liquidity mining incentive using all
    /// @notice trading fees currently housed in this contract
    function replenish() external {
        uint256 blockTimestamp = block.timestamp;
        require(blockTimestamp > blockTimestampLast + minReplenishDuration, "OVLV1: duration<min");

        // needed attributes of incentive key
        uint256 startTime = blockTimestamp + incentiveLeadTime;
        uint256 endTime = startTime + incentiveDuration;
        int24 minWidth = _minWidthMaxRange(pool);  // max range

        // reward to be given out should be current balance of fees
        uint256 reward = ovl.balanceOf(address(this));

        // assemble incentive key and create a new incentive
        IUniswapV3Staker.IncentiveKey memory key = IUniswapV3Staker.IncentiveKey({
            rewardToken: IERC20Minimal(address(ovl)),
            pool: pool,
            startTime: startTime,
            endTime: endTime,
            minWidth: minWidth,
            refundee: address(this)
        });
        staker.createIncentive(key, reward);

        // set the last timestamp
        blockTimestampLast = blockTimestamp;
    }

    // TODO: ...
    // function transfer() onlyGov {}
}
