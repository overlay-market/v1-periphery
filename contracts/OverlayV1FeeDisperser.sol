// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Token.sol";
import "@overlay-protocol/v1-core/contracts/libraries/FixedPoint.sol";

import "@uniswap/v3-core/contracts/interfaces/IERC20Minimal.sol";
import "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

import "./interfaces/uniswap/v3-staker/IUniswapV3Staker.sol";
import "./libraries/uniswap/v3-staker/IncentiveId.sol";

contract OverlayV1FeeDisperser {
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

    // registry of incentive idxs for given (token0, token1, fee) pair
    mapping(address => mapping(address => mapping(uint24 => uint256))) public incentiveIdxs;

    // last time incentives were replenished with liquidity mining rewards
    uint256 public blockTimestampLast;

    // events emitted on replenish, add, update incentive
    event IncentivesReplenished(
        address indexed user,
        uint256[] rewards,
        uint256 startTime,
        uint256 endTime
    );
    event IncentiveAdded(address indexed user, uint256 indexed id, uint256 weight);
    event IncentiveUpdated(address indexed user, uint256 indexed id, uint256 weight);

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
        minReplenishDuration = _minReplenishDuration;

        // check less than max values staker will allow
        require(
            _incentiveLeadTime <= staker.maxIncentiveStartLeadTime(),
            "OVLV1: incentiveLeadTime>max"
        );
        incentiveLeadTime = _incentiveLeadTime;

        require(
            _incentiveDuration <= staker.maxIncentiveDuration(),
            "OVLV1: incentiveDuration>max"
        );
        incentiveDuration = _incentiveDuration;

        // initialize first incentive array entry as empty
        // to save some gas on incentiveIdxs storage
        incentives.push();
    }

    /// @notice Creates new liquidity mining incentives using all
    /// @notice trading fees currently housed in this contract
    function replenishIncentives() external {
        require(
            block.timestamp > blockTimestampLast + minReplenishDuration,
            "OVLV1: duration<min"
        );

        // get the total incentive weights
        uint256 _totalWeight = totalWeight;
        require(_totalWeight > 0, "OVLV1: !incentives");

        // total reward to be given out should be current balance of fees
        uint256 totalReward = ovl.balanceOf(address(this));
        require(totalReward > 0, "OVLV1: reward == 0");

        // needed timespan attributes for start and end of new incentives
        uint256 startTime = block.timestamp + incentiveLeadTime;
        uint256 endTime = startTime + incentiveDuration;

        // approve staker to transfer totalReward from staker
        ovl.approve(address(staker), totalReward);

        // for each incentive, calculate reward then replenish through staker
        // NOTE: start loop at index 1 since 0 index of incentives is empty
        uint256 length = incentives.length;
        uint256[] memory rewards = new uint256[](length);
        for (uint256 i = 1; i < length; i++) {
            Incentive memory incentive = incentives[i];
            uint256 reward = calcIncentiveReward(incentive, totalReward, _totalWeight);

            // only replenish if there's a reward to give the incentive
            if (reward > 0) {
                // replenish the incentive through staker
                _replenishIncentive(incentive, startTime, endTime, address(this), reward);

                // set reward in rewards arrays for event below
                rewards[i] = reward;
            }
        }

        // emit event to track so liquidity miners
        // can stake existing deposits on staker
        emit IncentivesReplenished(msg.sender, rewards, startTime, endTime);

        // update the last timestamp replenished
        blockTimestampLast = block.timestamp;
    }

    /// @notice Calculates the reward amount to allocate to the given incentive
    /// @dev mul/div down with fraction to avoid transferring more than totalReward
    function calcIncentiveReward(
        Incentive memory incentive,
        uint256 rewardTotal,
        uint256 weightTotal
    ) public pure returns (uint256 reward_) {
        // div down to avoid transferring more
        uint256 fraction = incentive.weight.divDown(weightTotal);
        reward_ = rewardTotal.mulDown(fraction);
    }

    /// @notice Creates new liquidity mining incentive for given reward
    /// @notice over max range
    // TODO: fix for changes to staker
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
    /// @return is_ where pair is incentivized
    function isIncentive(
        address token0,
        address token1,
        uint24 fee
    ) public view returns (bool is_) {
        is_ = (incentiveIdxs[token0][token1][fee] > 0);
    }

    /// @notice Convenience view function to get incentive index in incentives
    /// @return idx_ index in incentives array
    function getIncentiveIndex(
        address token0,
        address token1,
        uint24 fee
    ) public view returns (uint256 idx_) {
        idx_ = incentiveIdxs[token0][token1][fee];
        require(idx_ > 0, "OVLV1: !incentive");
    }

    /// @notice Convenience view function to get incentive id in staker
    /// @return id_ ID as key in staker.incentives
    function getStakerIncentiveId(IUniswapV3Staker.IncentiveKey memory key)
        public
        view
        returns (bytes32 id_)
    {
        id_ = IncentiveId.compute(key);
    }

    /// @notice Allows governor to add incentive for new liquidity mining pool
    function addIncentive(
        address token0,
        address token1,
        uint24 fee,
        uint256 weight
    ) external onlyGovernor {
        // check weight > 0
        require(weight > 0, "OVLV1: incentive weight == 0");

        // check incentive does not already exist
        require(!isIncentive(token0, token1, fee), "OVLV1: incentive exists");

        // check actually a Uni V3 pool
        IUniswapV3Factory uniV3Factory = staker.factory();
        require(uniV3Factory.getPool(token0, token1, fee) != address(0), "OVLV1: !UniswapV3Pool");

        // add new incentive
        incentives.push(Incentive({token0: token0, token1: token1, fee: fee, weight: weight}));

        // update the total weight for all incentives
        totalWeight += weight;

        // store incentive index
        // store for (token0, token1) and (token1, token0) to save gas on checks
        // SEE: https://github.com/Uniswap/v3-core/blob/main/contracts/UniswapV3Factory.sol#L48
        uint256 idx = incentives.length - 1;
        incentiveIdxs[token0][token1][fee] = idx;
        incentiveIdxs[token1][token0][fee] = idx;

        // emit event to track incentive additions
        emit IncentiveAdded(msg.sender, idx, weight);
    }

    /// @notice Updates the weight on the incentive associated with the given
    /// @notice (token0, token1, fee) pair
    function updateIncentive(
        address token0,
        address token1,
        uint24 fee,
        uint256 weight
    ) external onlyGovernor {
        // get the incentive (checks incentive exists as well)
        uint256 idx = getIncentiveIndex(token0, token1, fee);
        Incentive memory incentive = incentives[idx];

        // update the total weights
        totalWeight = totalWeight - incentive.weight + weight;

        // update the weight on the specific incentive
        // and store it
        incentive.weight = weight;
        incentives[idx] = incentive;

        // emit event to track incentive updates
        emit IncentiveUpdated(msg.sender, idx, weight);
    }
}
