// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@openzeppelin/contracts/utils/math/Math.sol";

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Roller.sol";

import "../interfaces/state/IOverlayV1PriceState.sol";

import "./OverlayV1BaseState.sol";

abstract contract OverlayV1PriceState is IOverlayV1PriceState, OverlayV1BaseState {
    using Roller for Roller.Snapshot;

    function _bid(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) internal view returns (uint256 bid_) {
        // get the rolling volume on the bid
        uint256 volume = _volumeBid(market, data, fractionOfCapOi);

        // get the bid price for market
        bid_ = market.bid(data, volume);
    }

    function _ask(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) internal view returns (uint256 ask_) {
        // get the rolling volume on the ask
        uint256 volume = _volumeAsk(market, data, fractionOfCapOi);

        // get the ask price for market
        ask_ = market.ask(data, volume);
    }

    function _mid(Oracle.Data memory data) internal view returns (uint256 mid_) {
        mid_ = Math.average(data.priceOverMicroWindow, data.priceOverMacroWindow);
    }

    function _volumeBid(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) internal view returns (uint256 volume_) {
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
        volume_ = uint256(snapshot.cumulative());
    }

    function _volumeAsk(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) internal view returns (uint256 volume_) {
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
        volume_ = uint256(snapshot.cumulative());
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

    /// @notice Gets the rolling volume on the bid after the trader places
    /// @notice trade on the Overlay market associated with the given feed
    /// @notice address given fraction of cap on open interest trade represents
    /// @dev fractionOfCapOi (i.e. oi / capOi) is FixedPoint
    /// @return volumeBid_ as the volume on the bid
    function volumeBid(address feed, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeBid_)
    {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        volumeBid_ = _volumeBid(market, data, fractionOfCapOi);
    }

    /// @notice Gets the rolling volume on the ask after the trader places
    /// @notice trade on the Overlay market associated with the given feed
    /// @notice address given fraction of cap on open interest trade represents
    /// @dev fractionOfCapOi (i.e. oi / capOi) is FixedPoint
    /// @return volumeAsk_ as the volume on the ask
    function volumeAsk(address feed, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeAsk_)
    {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        volumeAsk_ = _volumeAsk(market, data, fractionOfCapOi);
    }

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

    /// @notice Gets the current rolling volume on the bid and ask sides
    /// @notice of the Overlay market associated with the given feed address
    /// @return volumeBid_ as the current rolling volume on the bid
    /// @return volumeAsk_ as the current rolling volume on the ask
    function volumes(address feed) external view returns (uint256 volumeBid_, uint256 volumeAsk_) {
        // cache market and feed data
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);

        // use the bid, ask rolling volumes assuming zero oi being traded
        // for current volumes
        volumeBid_ = _volumeBid(market, data, 0);
        volumeAsk_ = _volumeAsk(market, data, 0);
    }
}
