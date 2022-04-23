// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Token.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";

import "@uniswap/v3-core/contracts/interfaces/IERC20Minimal.sol";
import "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

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

    // governance determined Uni V3 pools to actively incentivize
    struct Incentive {
        address token0;
        address token1;
        uint24 fee;
        uint256 weight;
    }
    Incentive[] public incentives;
    uint256 public totalWeight;

    // registry of incentive ids for given (token0, token1, fee) pair
    mapping(address => mapping(address => mapping(uint24 => uint256))) public incentiveIds;

    // registry of created liquidity mining program start and end times
    struct Span {
        uint256 startTime;
        uint256 endTime;
    }
    // for a given index in incentives array above returns array of Spans
    mapping(uint256 => Span[]) public spans;

    // last time incentives were replenished with liquidity mining rewards
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

    // TODO: test
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

        // initialize first incentive array entry as empty
        // to save some gas on incentiveIds storage
        incentives.push(Incentive({
            token0: address(0),
            token1: address(0),
            fee: 0,
            weight: 0
        }));
    }

    /// @notice Creates new liquidity mining incentives using all
    /// @notice trading fees currently housed in this contract
    // TODO: test
    function replenishIncentives() external {
        uint256 blockTimestamp = block.timestamp;
        require(blockTimestamp > blockTimestampLast + minReplenishDuration, "OVLV1: duration<min");

        // needed span attributes for start and end of new incentives
        uint256 startTime = blockTimestamp + incentiveLeadTime;
        uint256 endTime = startTime + incentiveDuration;

        // total reward to be given out should be current balance of fees
        uint256 totalReward = ovl.balanceOf(address(this));

        // for each incentive, calculate reward then replenish through staker
        // NOTE: start loop at index 1 since 0 is empty
        // TODO: gas issue here?
        // TODO: check any issues with totalWeight == 0 when no incentives
        uint256 length = incentives.length;
        for (uint256 i=1; i < length; i++) {
            Incentive memory incentive = incentives[i];
            uint256 reward = calcReward(incentive, totalReward);

            // only replenish if there's a reward to give the incentive
            if (reward > 0) {
                // replenish the incentive through staker
                _replenishIncentive(incentive, startTime, endTime, address(this), reward);

                // store the time span over which incentive will last
                // for reference in registry
                // TODO: is this really necessary?
                spans[i].push(Span({startTime: startTime, endTime: endTime}));

                // emit event to track so liquidity miners
                // can stake existing deposit on staker
                emit IncentiveReplenished(i, startTime, endTime, reward);
            }
        }

        // set the last timestamp replenished
        blockTimestampLast = blockTimestamp;
    }

    /// @notice Calculates the reward amount to allocate to the given incentive
    /// @dev mul/div down with fraction to avoid transferring more than totalReward
    // TODO: test
    // TODO: check any issues with totalWeight == 0 when no incentives
    function calcReward(Incentive memory incentive, uint256 totalReward)
        public
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

    /// @notice whether given (token0, token1, fee) pair is being incentivized
    // TODO: test
    function isIncentive(address token0, address token1, uint24 fee) public view returns (bool is_) {
        is_ = (incentiveIds[token0][token1][fee] > 0);
    }

    /// @notice Convenience view function
    // TODO: test
    function getIncentiveIndex(address token0, address token1, uint24 fee) public view returns (uint256 idx_) {
        idx_ = incentiveIds[token0][token1][fee];
        require(idx_ > 0, "OVLV1: !incentive");
    }

    /// @notice Allows governor to add incentive for new liquidity mining pool
    // TODO: test
    function addIncentive(address token0, address token1, uint24 fee, uint256 weight) external onlyGovernor {
        // check weight > 0
        require(weight > 0, "OVLV1: incentive weight == 0");

        // check incentive does not already exist
        require(!isIncentive(token0, token1, fee), "OVLV1: incentive exists");

        // check actually a Uni V3 pool
        IUniswapV3Factory uniV3Factory = staker.factory();
        require(uniV3Factory.getPool(token0, token1, fee) != address(0), "OVLV1: !UniV3Pool");

        // add new incentive
        incentives.push(Incentive({
            token0: token0,
            token1: token1,
            fee: fee,
            weight: weight
        }));

        // update the total weight for all incentives
        totalWeight += weight;

        // store incentive id
        // store for (token0, token1) and (token1, token0) to save gas on checks
        // SEE: https://github.com/Uniswap/v3-core/blob/main/contracts/UniswapV3Factory.sol#L48
        uint256 id = incentives.length;
        incentiveIds[token0][token1][fee] = id;
        incentiveIds[token1][token0][fee] = id;

        // TODO: emit event
    }

    /// @notice Updates the weight on the incentive associated with the given
    /// @notice (token0, token1, fee) pair
    // TODO: test
    function updateIncentive(address token0, address token1, uint24 fee, uint256 weight) external onlyGovernor {
        // check incentive exists
        require(isIncentive(token0, token1, fee), "OVLV1: !incentive");

        // get the incentive
        uint256 idx = getIncentiveIndex(token0, token1, fee);
        Incentive memory incentive = incentives[idx];

        // update the total weights
        totalWeight = totalWeight - incentive.weight + weight;

        // update the weight on the specific incentive
        // and store it
        incentive.weight = weight;
        incentives[idx] = incentive;

        // TODO: emit event
    }
}
