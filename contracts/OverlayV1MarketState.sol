// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@openzeppelin/contracts/utils/math/Math.sol";

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/interfaces/feeds/IOverlayV1Feed.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Roller.sol";

contract OverlayV1MarketState {
    using FixedPoint for uint256;
    using Roller for Roller.Snapshot;

    IOverlayV1Factory public immutable factory;

    constructor(IOverlayV1Factory _factory) {
        factory = _factory;
    }

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    function _getMarket(address feed) private view returns (IOverlayV1Market market_) {
        address marketAddress = factory.getMarket(feed);
        require(marketAddress != address(0), "OVLV1:!market");
        market_ = IOverlayV1Market(marketAddress);
    }

    /// @notice Gets the oracle data from the given feed
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

        // time elapsed since funding last paid
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

    // TODO: capOi

    /// @notice Gets the current bid, ask, and mid price values on the
    /// @notice Overlay market associated with the given feed address
    /// @notice accounting for recent volume
    /// @return bid_ as the current bid price
    /// @return ask_ as the current ask price
    /// @return mid_ as the current mid price from feed
    function prices(address feed)
        external
        view
        returns (
            uint256 bid_,
            uint256 ask_,
            uint256 mid_
        )
    {
        // cache market and feed data
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);

        // use the bid, ask prices assuming zero oi being traded
        // for current prices
        bid_ = _bid(market, data, 0);
        ask_ = _ask(market, data, 0);

        // mid excludes volume (manipulation resistant)
        mid_ = _mid(data);
    }

    function _bid(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 bid_) {
        // assemble the rolling volume snapshot
        (uint32 timestamp, uint32 window, int192 accumulator) = market.snapshotVolumeBid();
        Roller.Snapshot memory snapshot = Roller.Snapshot({
            timestamp: timestamp,
            window: window,
            accumulator: accumulator
        });
        int256 value = int256(fractionOfCapOi);

        // calculate the decay in rolling volume since last snapshot
        snapshot = snapshot.transform(block.timestamp, data.microWindow, value);
        uint256 volume = uint256(snapshot.cumulative());

        // get the bid price for market
        bid_ = market.bid(data, volume);
    }

    function _ask(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 ask_) {
        // assemble the rolling volume snapshot
        (uint32 timestamp, uint32 window, int192 accumulator) = market.snapshotVolumeAsk();
        Roller.Snapshot memory snapshot = Roller.Snapshot({
            timestamp: timestamp,
            window: window,
            accumulator: accumulator
        });
        int256 value = int256(fractionOfCapOi);

        // calculate the decay in rolling volume since last snapshot
        snapshot = snapshot.transform(block.timestamp, data.microWindow, value);
        uint256 volume = uint256(snapshot.cumulative());

        // get the ask price for market
        ask_ = market.ask(data, volume);
    }

    function _mid(Oracle.Data memory data) private view returns (uint256 mid_) {
        mid_ = Math.average(data.priceOverMicroWindow, data.priceOverMacroWindow);
    }

    /// @notice Gets the bid price trader will receive on the Overlay market
    /// @notice associated with the given feed address given fraction of
    /// @notice cap on open interest trade represents
    /// @dev fractionOfCapOi (i.e. oi / capOi) is FixedPoint
    /// @return bid_ as the received bid price
    function bid(address feed, uint256 fractionOfCapOi) external view returns (uint256 bid_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        bid_ = _bid(market, data, fractionOfCapOi);
    }

    /// @notice Gets the ask price trader will receive on the Overlay market
    /// @notice associated with the given feed address given fraction of
    /// @notice cap on open interest trade represents
    /// @dev fractionOfCapOi (i.e. oi / capOi) is FixedPoint
    /// @return ask_ as the received ask price
    function ask(address feed, uint256 fractionOfCapOi) external view returns (uint256 ask_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        ask_ = _ask(market, data, fractionOfCapOi);
    }

    /// @notice Gets the mid price from feed used for liquidations
    /// @notice on the Overlay market associated with the given feed address
    /// @return mid_ as the received mid price
    function mid(address feed) external view returns (uint256 mid_) {
        Oracle.Data memory data = _getOracleData(feed);
        mid_ = _mid(data);
    }

    // TODO: function slippage

    // TODO: volumes, liquidatable positions, caps, mints/burns
    // TODO: getAccountLiquidity() equivalent from Comptroller (PnL + value)
    // TODO: pos views: value, pnl, notionalWithPnl, collateral ...
}
