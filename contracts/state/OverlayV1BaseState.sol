// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/interfaces/feeds/IOverlayV1Feed.sol";

import "@overlay/v1-core/contracts/libraries/Oracle.sol";

import "../interfaces/state/IOverlayV1BaseState.sol";

abstract contract OverlayV1BaseState is IOverlayV1BaseState {
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

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    function market(address feed) external view returns (IOverlayV1Market market_) {
        market_ = _getMarket(feed);
    }

    /// @notice Gets the oracle data from the given feed
    function data(address feed) external view returns (Oracle.Data memory data_) {
        data_ = _getOracleData(feed);
    }
}
