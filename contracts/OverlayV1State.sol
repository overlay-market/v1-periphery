// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@openzeppelin/contracts/utils/math/Math.sol";

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/interfaces/feeds/IOverlayV1Feed.sol";

import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Position.sol";
import "@overlay/v1-core/contracts/libraries/Risk.sol";
import "@overlay/v1-core/contracts/libraries/Roller.sol";

/// @title A market state contract to view the current state of
/// @title an Overlay market
// TODO: separate out into oi, price, position contracts w internal views
// TODO: then have OverlayV1State inherit and expose as external (?)
contract OverlayV1State {
    using FixedPoint for uint256;
    using Position for Position.Info;
    using Roller for Roller.Snapshot;

    // internal constants
    uint256 internal constant ONE = 1e18; // 18 decimal places

    // immutables
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

    /// @notice Gets the Overlay market address for the given feed
    /// @dev reverts if market doesn't exist
    // TODO: test
    function market(address feed) external view returns (IOverlayV1Market market_) {
        market_ = _getMarket(feed);
    }

    /// @notice Gets the oracle data from the given feed
    function _getOracleData(address feed) private view returns (Oracle.Data memory data_) {
        data_ = IOverlayV1Feed(feed).latest();
    }

    /// @notice Gets the oracle data from the given feed
    // TODO: test
    function data(address feed) external view returns (Oracle.Data memory data_) {
        data_ = _getOracleData(feed);
    }

    /// @notice Gets the position from the given market for the
    /// @notice position owner and position id
    function _getPosition(
        IOverlayV1Market market,
        address owner,
        uint256 id
    ) private view returns (Position.Info memory position_) {
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

    /// @notice Computes the number of contracts (open interest) for the given
    /// @notice amount of notional in OVL at the current mid from Oracle data
    /// @dev OI = Q / MP; where Q = notional, MP = mid price, OI = open interest
    /// @dev Q = N * L; where N = collateral, L = leverage
    function _oiFromNotional(Oracle.Data memory data, uint256 notional)
        private
        view
        returns (uint256 oi_)
    {
        uint256 midPrice = _mid(data);
        require(midPrice > 0, "OVLV1:mid==0");
        oi_ = notional.divDown(midPrice);
    }

    function _ois(IOverlayV1Market market)
        private
        view
        returns (uint256 oiLong_, uint256 oiShort_)
    {
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

    /// @notice Gets the current open interest values on the Overlay market
    /// @notice associated with the given feed address accounting for funding
    /// @return oiLong_ as the current open interest long
    /// @return oiShort_ as the current open interest short
    function ois(address feed) external view returns (uint256 oiLong_, uint256 oiShort_) {
        IOverlayV1Market market = _getMarket(feed);
        (oiLong_, oiShort_) = _ois(market);
    }

    function _capOi(IOverlayV1Market market, Oracle.Data memory data)
        private
        view
        returns (uint256 capOi_)
    {
        // get cap notional from risk params
        uint256 capNotional = market.params(uint256(Risk.Parameters.CapNotional));

        // adjust for bounds on cap oi from front + back-running attacks
        capNotional = market.capNotionalAdjustedForBounds(data, capNotional);

        // convert to a cap on number of contracts (open interest)
        capOi_ = _oiFromNotional(data, capNotional);
    }

    /// @notice Gets the current cap on open interest on the Overlay market
    /// @notice associated with the given feed address accounting for
    /// @notice front and back-running bounds
    /// @return capOi_ as the current open interest cap
    function capOi(address feed) external view returns (uint256 capOi_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        capOi_ = _capOi(market, data);
    }

    /// @dev fractionOfCapOi = oi / capOi as FixedPoint
    /// @dev handles capOi == 0 edge case by returning type(uint256).max
    function _fractionOfCapOi(IOverlayV1Market market, Oracle.Data memory data, uint256 oi) private view returns (uint256) {
        // simply oi / capOi
        uint256 cap = _capOi(market, data);
        if (cap == 0) {
            // handle the edge case
            return type(uint256).max;
        }
        return oi.divDown(cap);
    }

    /// @notice Gets the fraction of the current open interest cap the
    /// @notice given oi contracts represents on the Overlay market
    /// @notice associated with the given feed address
    /// @dev fractionOfCapOi = oi / capOi is FixedPoint
    /// @return fractionOfCapOi_ as fraction of open interest cap given oi is
    function fractionOfCapOi(address feed, uint256 oi) external view returns (uint256 fractionOfCapOi_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        fractionOfCapOi_ = _fractionOfCapOi(market, data, oi);
    }

    /// @notice Gets the current funding rate on the Overlay market
    /// @notice associated with the given feed address
    /// @dev f = 2 * k * ( oiLong - oiShort ) / (oiLong + oiShort)
    /// @dev such that long > short then positive
    /// @return fundingRate_ as the current funding rate
    function fundingRate(address feed) external view returns (int256 fundingRate_) {
        IOverlayV1Market market = _getMarket(feed);
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // determine overweight vs underweight side
        bool isLongOverweight = oiLong > oiShort;
        uint256 oiOverweight = isLongOverweight ? oiLong : oiShort;
        uint256 oiUnderweight = isLongOverweight ? oiShort : oiLong;

        // determine total oi and imbalance in oi
        uint256 oiTotal = oiOverweight + oiUnderweight;
        uint256 oiImbalance = oiOverweight - oiUnderweight;
        if (oiTotal == 0 || oiImbalance == 0) {
            return int256(0);
        }

        // Get the k risk param for the market and then calculate funding rate
        uint256 k = market.params(uint256(Risk.Parameters.K));
        uint256 rate = oiImbalance.divDown(oiTotal).mulDown(2 * k);

        // return mag + sign for funding rate
        fundingRate_ = isLongOverweight ? int256(rate) : -int256(rate);
    }

    /// @notice Gets the current level of the circuit breaker for the
    /// @notice open interest cap on the Overlay market associated with
    /// @notice the given feed address
    /// @dev circuit breaker level is reported as fraction of capOi in FixedPoint
    /// @return circuitBreakerLevel_ as the current circuit breaker level
    function circuitBreakerLevel(address feed)
        external
        view
        returns (uint256 circuitBreakerLevel_)
    {
        IOverlayV1Market market = _getMarket(feed);

        // set cap to ONE as reporting level in terms of % of capOi
        // = market.capNotionalAdjustedForCircuitBreaker(cap) / cap
        circuitBreakerLevel_ = market.capNotionalAdjustedForCircuitBreaker(ONE);
    }

    /// @notice Gets the current rolling amount minted (+) or burned (-)
    /// @notice by the Overlay market associated with the given feed address
    /// @dev minted_ > 0 means more OVL has been minted than burned recently
    /// @return minted_ as the current rolling amount minted
    function minted(address feed) external view returns (int256 minted_) {
        // cache market
        IOverlayV1Market market = _getMarket(feed);

        // assemble the rolling amount minted snapshot
        (uint32 timestamp, uint32 window, int192 accumulator) = market.snapshotMinted();
        Roller.Snapshot memory snapshot = Roller.Snapshot({
            timestamp: timestamp,
            window: window,
            accumulator: accumulator
        });

        // Get the circuit breaker window risk param for the market
        // and set value to zero to prep for transform
        uint256 circuitBreakerWindow = market.params(
            uint256(Risk.Parameters.CircuitBreakerWindow)
        );
        int256 value = int256(0);

        // calculate the decay in rolling amount minted since last snapshot
        snapshot = snapshot.transform(block.timestamp, circuitBreakerWindow, value);
        minted_ = int256(snapshot.cumulative());
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

    function _volumeBid(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 volume_) {
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

    function _bid(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 bid_) {
        // get the rolling volume on the bid
        uint256 volume = _volumeBid(market, data, fractionOfCapOi);

        // get the bid price for market
        bid_ = market.bid(data, volume);
    }

    function _volumeAsk(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 volume_) {
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

    function _ask(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 fractionOfCapOi
    ) private view returns (uint256 ask_) {
        // get the rolling volume on the ask
        uint256 volume = _volumeAsk(market, data, fractionOfCapOi);

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

    // TODO: pos views: value, pnl, notionalWithPnl, collateral, liquidatable
    // TODO: getAccountLiquidity() equivalent from Comptroller (PnL + value)


    /// @notice Gets the current open interest of the position on the Overlay
    /// @notice market associated with the given feed address for the given
    /// @notice position owner, id
    /// @return oi_ as the current open interest occupied by the position
    function oi(address feed, address owner, uint256 id) external view returns (uint256 oi_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);

        // assume entire position value such that fraction = ONE
        uint256 fraction = ONE;

        // get the attributes needed to calculate position oi:
        // oiLong/Short, oiLongShares/oiShortShares
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong ? market.oiLongShares() : market.oiShortShares();

        // return the current oi
        oi_ = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);
    }

    /// @notice Gets the current value of the position on the Overlay market
    /// @notice associated with the given feed address for the given
    /// @notice position owner, id
    /// @return value_ as the current value of the position
    function value(address feed, address owner, uint256 id) external view returns (uint256 value_) {
        IOverlayV1Market market = _getMarket(feed);
        Oracle.Data memory data = _getOracleData(feed);
        Position.Info memory position = _getPosition(market, owner, id);

        // assume entire position value such that fraction = ONE
        uint256 fraction = ONE;

        // get the attributes needed to calculate position value:
        // oiLong/Short, oiLongShares/oiShortShares, price, capPayoff
        (uint256 oiLong, uint256 oiShort) = _ois(market);

        // aggregate oi values on market
        uint256 oiTotalOnSide = position.isLong ? oiLong : oiShort;
        uint256 oiTotalSharesOnSide = position.isLong ? market.oiLongShares() : market.oiShortShares();

        // position's current oi factoring in funding
        uint256 oi = position.oiCurrent(fraction, oiTotalOnSide, oiTotalSharesOnSide);

        // current price is price position would receive if unwound
        // longs get the bid on unwind, shorts get the ask
        uint256 volume = _fractionOfCapOi(market, data, oi);
        uint256 currentPrice = position.isLong ? _bid(market, data, volume) : _ask(market, data, volume);

        // get cap payoff from risk params
        uint256 capPayoff = market.params(uint256(Risk.Parameters.CapPayoff));

        // return current value
        value_ = position.value(fraction, oiTotalOnSide, oiTotalSharesOnSide, currentPrice, capPayoff);
    }
}