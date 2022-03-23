// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";

contract OverlayV1MarketState {

    IOverlayV1Factory public immutable factory;

    constructor(IOverlayV1Factory _factory) {
        factory = _factory;
    }

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    function _getMarket(address feed) private view returns (address market_) {
        market_ = factory.getMarket(feed);
        require(market_ != address(0), "OVLV1: !market");
    }
}
