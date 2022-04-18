// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Roller.sol";

import "./OverlayV1BaseState.sol";
import "./OverlayV1OIState.sol";
import "./OverlayV1PriceState.sol";

abstract contract OverlayV1PositionState is
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
            uint96 notional,
            uint96 debt,
            uint48 entryToMidRatio,
            bool isLong,
            bool liquidated,
            uint256 oiShares
        ) = market.positions(key);

        // assemble the position info struct
        position_ = Position.Info({
            notional: notional,
            debt: debt,
            entryToMidRatio: entryToMidRatio,
            isLong: isLong,
            liquidated: liquidated,
            oiShares: oiShares
        });
    }

    /// @dev current debt owed by individual position
    function _debt(Position.Info memory position) internal view returns (uint256 debt_) {
        // assume entire position value such that fraction = ONE
        uint256 fraction = FixedPoint.ONE;

        // return the debt
        debt_ = position.debtCurrent(fraction);
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
        // notionalInitial, debtCurrent, oiInitial, oiCurrent
        uint256 q = position.notionalInitial(fraction);
        uint256 d = position.debtCurrent(fraction);
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

    /// @notice Gets the position from the Overlay market associated with
    /// @notice the given feed for the given position owner and position id
    function position(
        address feed,
        address owner,
        uint256 id
    ) external view returns (Position.Info memory position_) {
        IOverlayV1Market market = _getMarket(feed);
        position_ = _getPosition(market, owner, id);
    }

    /// @notice Gets the current debt of the position on the Overlay
    /// @notice market associated with the given feed address for the given
    /// @notice position owner, id
    /// @return debt_ as the current debt taken on by the position
    function debt(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 debt_) {
        IOverlayV1Market market = _getMarket(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        debt_ = _debt(position);
    }

    /// @notice Gets the current cost of the position on the Overlay
    /// @notice market associated with the given feed address for the given
    /// @notice position owner, id
    /// @return cost_ as the cost to build the position
    function cost(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 cost_) {
        IOverlayV1Market market = _getMarket(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        cost_ = _cost(position);
    }

    /// @notice Gets the current open interest of the position on the Overlay
    /// @notice market associated with the given feed address for the given
    /// @notice position owner, id
    /// @return oi_ as the current open interest occupied by the position
    function oi(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 oi_) {
        IOverlayV1Market market = _getMarket(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        oi_ = _oi(market, position);
    }

    /// @notice Gets the current collateral backing the position on the
    /// @notice Overlay market associated with the given feed address
    /// @notice for the given position owner, id
    /// @dev N(t) = Q * (OI(t) / OI(0)) - D; where Q = notional at build,
    /// @dev OI(t) = current open interest, OI(0) = open interest at build,
    /// @dev D = debt at build
    /// @return collateral_ as the current collateral backing the position
    function collateral(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 collateral_) {
        IOverlayV1Market market = _getMarket(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        collateral_ = _collateral(market, position);
    }

    /// @notice Gets the current value of the position on the Overlay market
    /// @notice associated with the given feed address for the given
    /// @notice position owner, id
    /// @return value_ as the current value of the position
    function value(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 value_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        value_ = _value(market, data, position);
    }

    /// @notice Gets the current notional of the position on the Overlay market
    /// @notice associated with the given feed address for the given
    /// @notice position owner, id (accounts for PnL)
    /// @return notional_ as the current notional of the position
    function notional(
        address feed,
        address owner,
        uint256 id
    ) external view returns (uint256 notional_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);
        notional_ = _notional(market, data, position);
    }

    // TODO: pos views: liquidatable returns (bool is, uint256 liqFee), tradingFee
    // TODO: getAccountLiquidity() equivalent from Comptroller (PnL + value)
}
