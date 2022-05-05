// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";
import "@overlay/v1-core/contracts/libraries/Risk.sol";

import "../interfaces/state/IOverlayV1EstimateState.sol";

import "./OverlayV1BaseState.sol";
import "./OverlayV1OIState.sol";
import "./OverlayV1PriceState.sol";

abstract contract OverlayV1EstimateState is
    IOverlayV1EstimateState,
    OverlayV1BaseState,
    OverlayV1PriceState,
    OverlayV1OIState
{
    using FixedPoint for uint256;
    using Position for Position.Info;

    /// @notice Gets the position that would be built on the given market
    /// @notice for the given (collateral, leverage, isLong) attributes
    // TODO: test
    function _estimatePosition(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) internal view returns (Position.Info memory position_) {
        // notional, debt, oi
        uint256 notional = collateral.mulUp(leverage);
        uint256 debt = notional - collateral;
        uint256 oi = _oiFromNotional(data, notional);
        uint256 fractionOfCapOi = _fractionOfCapOi(market, data, oi);

        // prices
        uint256 midPrice = _mid(data);
        uint256 price = isLong
            ? _ask(market, data, fractionOfCapOi)
            : _bid(market, data, fractionOfCapOi);
        position_ = Position.Info({
            notional: uint96(notional),
            debt: uint96(debt),
            isLong: isLong,
            entryToMidRatio: Position.calcEntryToMidRatio(price, midPrice),
            liquidated: false,
            oiShares: oi
        });
    }

    function _debtEstimate(Position.Info memory position) internal view returns (uint256 debt_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // debt estimate is simply initial debt of position
        debt_ = position.debtCurrent(fraction);
    }

    function _costEstimate(Position.Info memory position) internal view returns (uint256 cost_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // cost estimate is simply initial cost of position
        cost_ = position.cost(fraction);
    }

    function _oiEstimate(Position.Info memory position) internal view returns (uint256 oi_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // oi estimate is simply initial oi of position
        oi_ = position.oiInitial(fraction);
    }

    function _maintenanceMarginEstimate(IOverlayV1Market market, Position.Info memory position)
        internal
        view
        returns (uint256 maintenanceMargin_)
    {
        uint256 maintenanceMarginFraction = market.params(
            uint256(Risk.Parameters.MaintenanceMarginFraction)
        );
        uint256 q = position.notionalInitial(FixedPoint.ONE);
        maintenanceMargin_ = q.mulUp(maintenanceMarginFraction);
    }

    function _liquidationPriceEstimate(IOverlayV1Market market, Position.Info memory position)
        internal
        view
        returns (uint256 liquidationPrice_)
    {
        // get position attributes independent of funding
        uint256 entryPrice = position.entryPrice();
        uint256 liquidationFeeRate = market.params(uint256(Risk.Parameters.LiquidationFeeRate));
        uint256 maintenanceMargin = _maintenanceMarginEstimate(market, position);

        // get position attributes
        // NOTE: cost is same as initial collateral
        uint256 oi = _oiEstimate(position);
        uint256 collateral = _costEstimate(position);
        require(oi > 0, "OVLV1: oi == 0");

        // get price delta from entry price: dp = | liqPrice - entryPrice |
        uint256 dp = collateral
            .subFloor(maintenanceMargin.divUp(FixedPoint.ONE - liquidationFeeRate))
            .divUp(oi);
        liquidationPrice_ = position.isLong ? entryPrice.subFloor(dp) : entryPrice + dp;
    }

    /// @notice Gets the estimated debt of the position to be built
    /// @notice on the Overlay market for the given (collateral, leverage,
    /// @notice isLong) attributes
    // TODO: test
    function debtEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 debt_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _estimatePosition(
            market,
            data,
            collateral,
            leverage,
            isLong
        );
        debt_ = _debtEstimate(position);
    }

    /// @notice Gets the estimated cost of the position to be built
    /// @notice on the Overlay market for the given (collateral, leverage,
    /// @notice isLong) attributes
    // TODO: test
    function costEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 cost_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _estimatePosition(
            market,
            data,
            collateral,
            leverage,
            isLong
        );
        cost_ = _costEstimate(position);
    }

    /// @notice Gets the estimated open interest of the position to be built
    /// @notice on the Overlay market for the given (collateral, leverage,
    /// @notice isLong) attributes
    // TODO: test
    function oiEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 oi_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _estimatePosition(
            market,
            data,
            collateral,
            leverage,
            isLong
        );
        oi_ = _oiEstimate(position);
    }

    /// @notice Gets the estimated maintenance margin of the position to be built
    /// @notice on the Overlay market for the given (collateral, leverage, isLong)
    /// @notice attributes
    // TODO: test
    function maintenanceMarginEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 maintenanceMargin_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _estimatePosition(
            market,
            data,
            collateral,
            leverage,
            isLong
        );
        maintenanceMargin_ = _maintenanceMarginEstimate(market, position);
    }

    /// @notice Gets the estimated liquidation price of the position to be built
    /// @notice on the Overlay market for the given (collateral, leverage, isLong)
    /// @notice attributes
    // TODO: test
    function liquidationPriceEstimate(
        IOverlayV1Market market,
        uint256 collateral,
        uint256 leverage,
        bool isLong
    ) external view returns (uint256 liquidationPrice_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _estimatePosition(
            market,
            data,
            collateral,
            leverage,
            isLong
        );
        liquidationPrice_ = _liquidationPriceEstimate(market, position);
    }
}