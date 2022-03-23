// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/interfaces/feeds/IOverlayV1Feed.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";

contract OverlayV1MarketState {
    IOverlayV1Factory public immutable factory;

    constructor(IOverlayV1Factory _factory) {
        factory = _factory;
    }

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    function _getMarket(address feed) private view returns (IOverlayV1Market market_) {
        address marketAddress = factory.getMarket(feed);
        require(marketAddress != address(0), "OVLV1: !market");
        market_ = IOverlayV1Market(marketAddress);
    }

    /// @notice Gets
    function _getOracleData(address feed) private view returns (Oracle.Data memory data_) {
        data_ = IOverlayV1Feed(feed).latest();
    }

    /// @notice Gets the current open interest values on the Overlay market
    /// @notice associated with the given feed address accounting for funding
    /// @return oiLong_ as the current open interest long
    /// @return oiShort_ as the current open interest short
    function oi(address feed) external view returns (uint256 oiLong_, uint256 oiShort_) {
        IOverlayV1Market market = _getMarket(feed);

        // oiLong/Short values before funding adjustments
        oiLong_ = market.oiLong();
        oiShort_ = market.oiShort();

        // time since funding last paid
        // if > 0, adjust for funding
        uint256 timeElapsed = block.timestamp - market.timestampUpdateLast();
        if (timeElapsed > 0) {
            // determine overweight vs underweight side
            bool isLongOverweight = oiLong_ > oiShort_;
            uint256 oiOverweight = isLongOverweight ? oiLong_ : oiShort_;
            uint256 oiUnderweight = isLongOverweight ? oiShort_ : oiLong_;

            // adjust for funding
            (oiOverweight, oiUnderweight) = market.oiAfterFunding(
                oiOverweight,
                oiUnderweight,
                timeElapsed
            );

            // values after funding adjustment
            oiLong_ = isLongOverweight ? oiOverweight : oiUnderweight;
            oiShort_ = isLongOverweight ? oiUnderweight : oiOverweight;
        }
    }

    // TODO: prices, volumes, liquidatable positions, caps, mints/burns
}
