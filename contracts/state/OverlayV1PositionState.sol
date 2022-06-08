// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";
import "@overlay/v1-core/contracts/libraries/Risk.sol";

import "../interfaces/state/IOverlayV1PositionState.sol";

import "./OverlayV1BaseState.sol";
import "./OverlayV1OIState.sol";
import "./OverlayV1PriceState.sol";

abstract contract OverlayV1PositionState is
    IOverlayV1PositionState,
    OverlayV1BaseState,
    OverlayV1PriceState,
    OverlayV1OIState
{
    using FixedPoint for uint256;
    using Position for Position.Info;

    /// @notice Gets the position from the given market for the
    /// @notice position owner and position id
    function _getPosition(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) internal view returns (Position.Info memory position_) {
        bytes32 key = keccak256(abi.encodePacked(owner, id));
        (
            uint96 notionalInitial,
            uint96 debtInitial,
            int24 midTick,
            int24 entryTick,
            bool isLong,
            bool liquidated,
            uint240 oiShares,
            uint16 fractionRemaining
        ) = market.positions(key);

        // assemble the position info struct
        position_ = Position.Info({
            notionalInitial: notionalInitial,
            debtInitial: debtInitial,
            midTick: midTick,
            entryTick: entryTick,
            isLong: isLong,
            liquidated: liquidated,
            oiShares: oiShares,
            fractionRemaining: fractionRemaining
        });
    }

    /// @dev current debt owed by individual position
    function _debt(Position.Info memory position) internal view returns (uint256 debt_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // return the debt
        debt_ = Position.debtInitial(position, fraction);
    }

    /// @dev current cost basis of individual position
    function _cost(Position.Info memory position) internal view returns (uint256 cost_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // return the cost
        cost_ = position.cost(fraction);
    }

    /// @dev current oi occupied by individual position
    function _oi(IOverlayV1Market market, Position.Info memory position)
        internal
        view
        returns (uint256 oi_)
    {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // get the attributes needed to calculate position oi:
        // oiLong/Short, oiLongShares/oiShortShares
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // return the current oi
        oi_ = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);
    }

    /// @dev current collateral backing the individual position
    function _collateral(IOverlayV1Market market, Position.Info memory position)
        internal
        view
        returns (uint256 collateral_)
    {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // get attributes needed to calculate current collateral amount:
        // notionalInitial, debtInitial, oiInitial, oiCurrent
        uint256 q = Position.notionalInitial(position, fraction);
        uint256 d = Position.debtInitial(position, fraction);
        uint256 oiInitial = position.oiInitial(fraction);

        // calculate oiCurrent from aggregate oi values
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // position's current oi factoring in funding
        uint256 oiCurrent = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);

        // return the collateral
        collateral_ = q.mulUp(oiCurrent).divUp(oiInitial).subFloor(d);
    }

    /// @dev current value of the individual position
    function _value(
        IOverlayV1Market market,
        Oracle.Data memory data,
        Position.Info memory position
    ) internal view returns (uint256 value_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // get the attributes needed to calculate position value:
        // oiLong/Short, oiLongShares/oiShortShares, price, capPayoff
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // position's current oi factoring in funding
        uint256 oi = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);

        // current price is price position would receive if unwound
        // longs get the bid on unwind, shorts get the ask
        uint256 currentPrice = position.isLong
            ? _bid(market, data, _fractionOfCapOi(market, data, oi))
            : _ask(market, data, _fractionOfCapOi(market, data, oi));

        // get cap payoff from risk params
        uint256 capPayoff = market.params(uint256(Risk.Parameters.CapPayoff));

        // return current value
        value_ = position.value(
            fraction,
            oiTotalOnSide,
            oiTotalSharesOnSide,
            currentPrice,
            capPayoff
        );
    }

    /// @dev current notional (including PnL) of the individual position
    function _notional(
        IOverlayV1Market market,
        Oracle.Data memory data,
        Position.Info memory position
    ) internal view returns (uint256 notional_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // get the attributes needed to calculate position notional:
        // oiLong/Short, oiLongShares/oiShortShares, price, capPayoff
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // position's current oi factoring in funding
        uint256 oi = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);

        // current price is price position would receive if unwound
        // longs get the bid on unwind, shorts get the ask
        uint256 currentPrice = position.isLong
            ? _bid(market, data, _fractionOfCapOi(market, data, oi))
            : _ask(market, data, _fractionOfCapOi(market, data, oi));

        // get cap payoff from risk params
        uint256 capPayoff = market.params(uint256(Risk.Parameters.CapPayoff));

        // return current notional with PnL
        notional_ = position.notionalWithPnl(
            fraction,
            oiTotalOnSide,
            oiTotalSharesOnSide,
            currentPrice,
            capPayoff
        );
    }

    /// @dev current value of the individual position used on liquidations
    /// @dev currentPrice == midPrice on liquidations to be manipulation
    /// @dev resistant against price slippage manipulators
    /// @dev will always be greater than _value()
    function _valueForLiquidations(
        IOverlayV1Market market,
        Oracle.Data memory data,
        Position.Info memory position
    ) internal view returns (uint256 value_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // get the attributes needed to calculate position value:
        // oiLong/Short, oiLongShares/oiShortShares, price, capPayoff
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // position's current oi factoring in funding
        uint256 oi = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);

        // current price is the price position receives upon liquidation
        // which is the mid price (manipulation resistant)
        uint256 currentPrice = _mid(data);

        // get cap payoff from risk params
        uint256 capPayoff = market.params(uint256(Risk.Parameters.CapPayoff));

        // return current value
        value_ = position.value(
            fraction,
            oiTotalOnSide,
            oiTotalSharesOnSide,
            currentPrice,
            capPayoff
        );
    }

    /// @dev current liquidation state of an individual position
    function _liquidatable(
        IOverlayV1Market market,
        Oracle.Data memory data,
        Position.Info memory position
    ) internal view returns (bool liquidatable_) {
        // get the attributes needed to calculate position notional:
        // oiLong/Short, oiLongShares/oiShortShares, price, capPayoff
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong
            ? market.oiLongShares()
            : market.oiShortShares();

        // current price is the price position receives upon liquidation
        // which is the mid price (manipulation resistant)
        uint256 currentPrice = _mid(data);

        // get liquidation fee rate from risk params
        uint256 liquidationFeeRate = market.params(uint256(Risk.Parameters.LiquidationFeeRate));

        // get whether liquidatable
        liquidatable_ = position.liquidatable(
            oiTotalOnSide,
            oiTotalSharesOnSide,
            currentPrice,
            market.params(uint256(Risk.Parameters.CapPayoff)),
            market.params(uint256(Risk.Parameters.MaintenanceMarginFraction)),
            liquidationFeeRate
        );
    }

    /// @dev current liquidation fee rewarded to liquidator of position
    function _liquidationFee(
        IOverlayV1Market market,
        Oracle.Data memory data,
        Position.Info memory position
    ) internal view returns (uint256 liquidationFee_) {
        bool liquidatable = _liquidatable(market, data, position);
        if (liquidatable) {
            uint256 liquidationFeeRate = market.params(
                uint256(Risk.Parameters.LiquidationFeeRate)
            );
            uint256 value = _valueForLiquidations(market, data, position);
            liquidationFee_ = value.mulDown(liquidationFeeRate);
        }
    }

    /// @dev maintenance margin required to keep position open
    function _maintenanceMargin(IOverlayV1Market market, Position.Info memory position)
        internal
        view
        returns (uint256 maintenanceMargin_)
    {
        uint256 maintenanceMarginFraction = market.params(
            uint256(Risk.Parameters.MaintenanceMarginFraction)
        );
        uint256 q = Position.notionalInitial(position, FixedPoint.ONE);
        maintenanceMargin_ = q.mulUp(maintenanceMarginFraction);
    }

    /// @notice Gets the position from the Overlay market or the given
    /// @notice position owner and position id
    function position(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (Position.Info memory position_) {
        position_ = _getPosition(market, owner, id);
    }

    /// @notice Gets the current debt of the position on the Overlay
    /// @notice market for the given position owner, id
    /// @return debt_ as the current debt taken on by the position
    function debt(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 debt_) {
        Position.Info memory position = _getPosition(market, owner, id);
        debt_ = _debt(position);
    }

    /// @notice Gets the current cost of the position on the Overlay
    /// @notice market for the given position owner, id
    /// @return cost_ as the cost to build the position
    function cost(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 cost_) {
        Position.Info memory position = _getPosition(market, owner, id);
        cost_ = _cost(position);
    }

    /// @notice Gets the current open interest of the position on the Overlay
    /// @notice market for the given position owner, id
    /// @return oi_ as the current open interest occupied by the position
    function oi(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 oi_) {
        Position.Info memory position = _getPosition(market, owner, id);
        oi_ = _oi(market, position);
    }

    /// @notice Gets the current collateral backing the position on the
    /// @notice Overlay market for the given position owner, id
    /// @dev N(t) = Q * (OI(t) / OI(0)) - D; where Q = notional at build,
    /// @dev OI(t) = current open interest, OI(0) = open interest at build,
    /// @dev D = debt at build
    /// @return collateral_ as the current collateral backing the position
    function collateral(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 collateral_) {
        Position.Info memory position = _getPosition(market, owner, id);
        collateral_ = _collateral(market, position);
    }

    /// @notice Gets the current value of the position on the Overlay market
    /// @notice for the given position owner, id
    /// @return value_ as the current value of the position
    function value(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 value_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        value_ = _value(market, data, position);
    }

    /// @notice Gets the current notional of the position on the Overlay market
    /// @notice for the given position owner, id (accounts for PnL)
    /// @return notional_ as the current notional of the position
    function notional(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 notional_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        notional_ = _notional(market, data, position);
    }

    /// @notice Gets the trading fee charged to unwind the position on the
    /// @notice Overlay market for the given position owner, id
    /// @dev tradingFee = notional * tradingFeeRate
    /// @return tradingFee_ as the current trading fee charged
    function tradingFee(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 tradingFee_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        uint256 notional = _notional(market, data, position);

        // get the trading fee rate from risk params
        uint256 tradingFeeRate = market.params(uint256(Risk.Parameters.TradingFeeRate));
        tradingFee_ = notional.mulUp(tradingFeeRate);
    }

    /// @notice Gets whether the position is currently liquidatable on the Overlay
    /// @notice market for the given position owner, id
    /// @return liquidatable_ as whether the position is liquidatable
    function liquidatable(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (bool liquidatable_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        liquidatable_ = _liquidatable(market, data, position);
    }

    /// @notice Gets the liquidation fee rewarded to the liquidator if
    /// @notice position currently liquidatable on the Overlay market
    /// @notice for the given position owner, id
    /// @dev liquidationFee_ == 0 if not liquidatable
    /// @return liquidationFee_ as the current liquidation fee reward
    function liquidationFee(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 liquidationFee_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        liquidationFee_ = _liquidationFee(market, data, position);
    }

    /// @notice Gets the maintenance margin required to keep the position
    /// @notice open on the Overlay market for the given position owner, id
    /// @return maintenanceMargin_ as the maintenance margin
    function maintenanceMargin(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 maintenanceMargin_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        maintenanceMargin_ = _maintenanceMargin(market, position);
    }

    /// @notice Gets the current position remaining margin to eat through
    /// @notice before liquidation occurs on the Overlay market
    /// @notice for the given position owner, id
    /// @dev excess_ > 0: returns excess margin before liquidation
    /// @dev excess_ < 0, returns margin lost due to delayed liquidation
    /// @return excess_ as the current value less maintenance and liq fees
    function marginExcessBeforeLiquidation(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (int256 excess_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);

        // liquidation uses mid price
        uint256 value = _valueForLiquidations(market, data, position);
        uint256 maintenanceMargin = _maintenanceMargin(market, position);
        uint256 liquidationFee = _liquidationFee(market, data, position);
        excess_ = int256(value) - int256(maintenanceMargin) - int256(liquidationFee);
    }

    /// @notice Gets the current liquidation price of the position on the
    /// @notice Overlay market for the given position owner, id
    /// @return liquidationPrice_ as the current liquidation price
    function liquidationPrice(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) external view returns (uint256 liquidationPrice_) {
        address feed = market.feed();
        Position.Info memory position = _getPosition(market, owner, id);

        // get position attributes independent of funding
        uint256 entryPrice = position.entryPrice();
        uint256 liquidationFeeRate = market.params(uint256(Risk.Parameters.LiquidationFeeRate));
        uint256 maintenanceMargin = _maintenanceMargin(market, position);

        // get position attributes dependent on funding
        uint256 oi = _oi(market, position);
        uint256 collateral = _collateral(market, position);
        require(oi > 0, "OVLV1: oi == 0");

        // get price delta from entry price: dp = | liqPrice - entryPrice |
        uint256 dp = collateral
            .subFloor(maintenanceMargin.divUp(FixedPoint.ONE - liquidationFeeRate))
            .divUp(oi);
        liquidationPrice_ = position.isLong ? entryPrice.subFloor(dp) : entryPrice + dp;
    }
}
