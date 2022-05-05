// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";

import "./IOverlayV1BaseState.sol";
import "./IOverlayV1OIState.sol";
import "./IOverlayV1PriceState.sol";

interface IOverlayV1EstimateState is IOverlayV1BaseState, IOverlayV1PriceState, IOverlayV1OIState {
    // estimated debt of position on the market
    function debtEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 debt_);

    // estimated cost basis of position on the market
    function costEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 cost_);

    // estimated open interest of position on the market
    function oiEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 oi_);

    // estimated maintenance margin requirement for position on market
    function maintenanceMarginEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 maintenanceMargin_);

    // estimated liquidation price for position on market
    function liquidationPriceEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 liquidationPrice_);
}
