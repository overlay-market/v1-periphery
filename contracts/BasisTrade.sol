// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;
pragma abicoder v2;

import '@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol';
import '@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol';

contract BasisTrade {
    ISwapRouter public immutable swapRouter;

    /// TODO: DAI needs to be changed to OVL everywhere
    address public DAI;
    address public WETH9;

    uint24 public constant poolFee = 3000;

    constructor(ISwapRouter _swapRouter, address _DAI, address _WETH9) {
        swapRouter = _swapRouter;
        DAI = _DAI;
        WETH9 = _WETH9;
    }

    function swapExactInputSingle(uint256 amountIn) internal returns (uint256 amountOut) {

        TransferHelper.safeTransferFrom(DAI, msg.sender, address(this), amountIn);

        TransferHelper.safeApprove(DAI, address(swapRouter), amountIn);

        ISwapRouter.ExactInputSingleParams memory params =
            ISwapRouter.ExactInputSingleParams({
                tokenIn: DAI,
                tokenOut: WETH9,
                fee: poolFee,
                recipient: msg.sender,
                deadline: block.timestamp,
                amountIn: amountIn,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });

        amountOut = swapRouter.exactInputSingle(params);
    }

    function swapExactOutputSingle(uint256 amountOut, uint256 amountInMaximum) internal returns (uint256 amountIn) {

        TransferHelper.safeTransferFrom(DAI, msg.sender, address(this), amountInMaximum);

        TransferHelper.safeApprove(DAI, address(swapRouter), amountInMaximum);

        ISwapRouter.ExactOutputSingleParams memory params =
            ISwapRouter.ExactOutputSingleParams({
                tokenIn: DAI,
                tokenOut: WETH9,
                fee: poolFee,
                recipient: msg.sender,
                deadline: block.timestamp,
                amountOut: amountOut,
                amountInMaximum: amountInMaximum,
                sqrtPriceLimitX96: 0
            });

        amountIn = swapRouter.exactOutputSingle(params);

        if (amountIn < amountInMaximum) {
            TransferHelper.safeApprove(DAI, address(swapRouter), 0);
            TransferHelper.safeTransfer(DAI, msg.sender, amountInMaximum - amountIn);
        }
    }
}