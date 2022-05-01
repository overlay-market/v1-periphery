// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";

import "./IOverlayV1BaseState.sol";
import "./IOverlayV1OIState.sol";
import "./IOverlayV1PriceState.sol";

interface IOverlayV1PositionState is IOverlayV1BaseState, IOverlayV1PriceState, IOverlayV1OIState {
    // position on the market
    function position(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (Position.Info memory position_);

    // debt of position on the market
    function debt(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 debt_);

    // cost basis of position on the market
    function cost(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 cost_);

    // open interest of position on the market
    function oi(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 oi_);

    // collateral backing position on the market
    function collateral(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 collateral_);

    // value of position on the market
    function value(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 value_);

    // notional of position on the market
    function notional(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 notional_);

    // trading fee charged to unwind position on the market
    function tradingFee(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 tradingFee_);

    // whether position is liquidatable on the market
    function liquidatable(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (bool liquidatable_);

    // liquidation fee rewarded to liquidator for position on market
    function liquidationFee(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 liquidationFee_);

    // maintenance margin requirement for position on market
    function maintenanceMargin(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 maintenanceMargin_);

    // remaining margin before liquidation for position on market
    function marginExcessBeforeLiquidation(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (int256 excess_);

    // liquidation price for position on market
    function liquidationPrice(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 liquidationPrice_);
}
