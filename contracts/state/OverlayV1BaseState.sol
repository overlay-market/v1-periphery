// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/interfaces/feeds/IOverlayV1Feed.sol";

import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";

abstract contract OverlayV1BaseState {
    // immutables
    IOverlayV1Factory public immutable factory;

    constructor(IOverlayV1Factory _factory) {
        factory = _factory;
    }

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    function _getMarket(address feed) internal view returns (IOverlayV1Market market_) {
        address marketAddress = factory.getMarket(feed);
        require(marketAddress != address(0), "OVLV1:!market");
        market_ = IOverlayV1Market(marketAddress);
    }

    /// @notice Gets the oracle data from the given feed
    function _getOracleData(address feed) internal view returns (Oracle.Data memory data_) {
        data_ = IOverlayV1Feed(feed).latest();
    }

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

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    // TODO: test
    function market(address feed) external view returns (IOverlayV1Market market_) {
        market_ = _getMarket(feed);
    }

    /// @notice Gets the oracle data from the given feed
    // TODO: test
    function data(address feed) external view returns (Oracle.Data memory data_) {
        data_ = _getOracleData(feed);
    }

    /// @notice Gets the position from the Overlay market associated with
    /// @notice the given feed for the given position owner and position id
    // TODO: test
    function position(
        address feed,
        address owner,
        uint256 id
    ) external view returns (Position.Info memory position_) {
        IOverlayV1Market market = _getMarket(feed);
        position_ = _getPosition(market, owner, id);
    }
}
