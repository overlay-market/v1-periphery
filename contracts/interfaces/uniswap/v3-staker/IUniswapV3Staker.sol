// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity ^0.8.2;

import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

import "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import "@uniswap/v3-core/contracts/interfaces/IERC20Minimal.sol";

import "@uniswap/v3-periphery/contracts/interfaces/IMulticall.sol";

/// @title Uniswap V3 Staker Interface
/// @notice Allows staking nonfungible liquidity tokens in exchange for reward tokens
interface IUniswapV3Staker is IERC721Receiver, IMulticall {
    /// @param rewardToken The token being distributed as a reward
    /// @param pool The Uniswap V3 pool
    /// @param startTime The time when the incentive program begins
    /// @param endTime The time when rewards stop accruing
    /// @param minWidth The minimum width of a staked position
    /// @param refundee The address which receives any remaining reward tokens
    /// @param          when the incentive is ended
    struct IncentiveKey {
        IERC20Minimal rewardToken;
        IUniswapV3Pool pool;
        uint256 startTime;
        uint256 endTime;
        int24 minWidth;
        address refundee;
    }

    /// @notice Creates a new liquidity mining incentive program
    /// @param key Details of the incentive to create
    /// @param reward The amount of reward tokens to be distributed
    function createIncentive(IncentiveKey memory key, uint256 reward) external;

    /// @notice Convenience function to create incentive setting minWidth param to max tick range
    /// @param reward The amount of reward tokens to be distributed
    function createIncentiveWithMaxRange(
        IERC20Minimal rewardToken,
        uint256 startTime,
        uint256 endTime,
        address refundee,
        uint256 reward,
        address token0,
        address token1,
        uint24 fee
    ) external;
}
