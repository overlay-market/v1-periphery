// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay/v1-core/contracts/libraries/FixedPoint.sol";
import "@overlay/v1-core/contracts/libraries/Oracle.sol";
import "@overlay/v1-core/contracts/libraries/Risk.sol";
import "@overlay/v1-core/contracts/libraries/Roller.sol";

import "../interfaces/state/IOverlayV1OIState.sol";

import "./OverlayV1BaseState.sol";
import "./OverlayV1PriceState.sol";

abstract contract OverlayV1OIState is IOverlayV1OIState, OverlayV1BaseState, OverlayV1PriceState {
    using FixedPoint for uint256;
    using Roller for Roller.Snapshot;

    /// @notice Computes the number of contracts (open interest) for the given
    /// @notice amount of notional in OVL at the current mid from Oracle data
    /// @dev OI = Q / MP; where Q = notional, MP = mid price, OI = open interest
    /// @dev Q = N * L; where N = collateral, L = leverage
    function _oiFromNotional(Oracle.Data memory data, uint256 notional)
        internal
        view
        returns (uint256 oi_)
    {
        uint256 midPrice = _mid(data);
        require(midPrice > 0, "OVLV1:mid==0");
        oi_ = notional.divDown(midPrice);
    }

    function _ois(IOverlayV1Market market)
        internal
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

    function _capOi(IOverlayV1Market market, Oracle.Data memory data)
        internal
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

    /// @dev fractionOfCapOi = oi / capOi as FixedPoint
    /// @dev handles capOi == 0 edge case by returning type(uint256).max
    function _fractionOfCapOi(
        IOverlayV1Market market,
        Oracle.Data memory data,
        uint256 oi
    ) internal view returns (uint256) {
        // simply oi / capOi
        uint256 cap = _capOi(market, data);
        if (cap == 0) {
            // handle the edge case
            return type(uint256).max;
        }
        return oi.divDown(cap);
    }

    /// @dev f = 2 * k * ( oiLong - oiShort ) / (oiLong + oiShort)
    /// @dev such that long > short then positive
    function _fundingRate(IOverlayV1Market market) internal view returns (int256 fundingRate_) {
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

    /// @dev circuit breaker level is reported as fraction of capOi in FixedPoint
    function _circuitBreakerLevel(IOverlayV1Market market)
        internal
        view
        returns (uint256 circuitBreakerLevel_)
    {
        // set cap to ONE as reporting level in terms of % of capOi
        // = market.capNotionalAdjustedForCircuitBreaker(cap) / cap
        circuitBreakerLevel_ = market.capOiAdjustedForCircuitBreaker(FixedPoint.ONE);
    }

    /// @notice Gets the current open interest values on the Overlay market
    /// @notice accounting for funding
    /// @return oiLong_ as the current open interest long
    /// @return oiShort_ as the current open interest short
    function ois(IOverlayV1Market market)
        external
        view
        returns (uint256 oiLong_, uint256 oiShort_)
    {
        (oiLong_, oiShort_) = _ois(market);
    }

    /// @notice Gets the current cap on open interest on the Overlay market
    /// @notice accounting for front and back-running bounds
    /// @return capOi_ as the current open interest cap
    function capOi(IOverlayV1Market market) external view returns (uint256 capOi_) {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        capOi_ = _capOi(market, data);
    }

    /// @notice Gets the fraction of the current open interest cap the
    /// @notice given oi contracts represents on the Overlay market
    /// @dev fractionOfCapOi = oi / capOi is FixedPoint
    /// @return fractionOfCapOi_ as fraction of open interest cap given oi is
    function fractionOfCapOi(IOverlayV1Market market, uint256 oi)
        external
        view
        returns (uint256 fractionOfCapOi_)
    {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);
        fractionOfCapOi_ = _fractionOfCapOi(market, data, oi);
    }

    /// @notice Gets the current funding rate on the Overlay market
    /// @dev f = 2 * k * ( oiLong - oiShort ) / (oiLong + oiShort)
    /// @dev such that long > short then positive
    /// @return fundingRate_ as the current funding rate
    function fundingRate(IOverlayV1Market market) external view returns (int256 fundingRate_) {
        fundingRate_ = _fundingRate(market);
    }

    /// @notice Gets the current level of the circuit breaker for the
    /// @notice open interest cap on the Overlay market
    /// @dev circuit breaker level is reported as fraction of capOi in FixedPoint
    /// @return circuitBreakerLevel_ as the current circuit breaker level
    function circuitBreakerLevel(IOverlayV1Market market)
        external
        view
        returns (uint256 circuitBreakerLevel_)
    {
        circuitBreakerLevel_ = _circuitBreakerLevel(market);
    }

    /// @notice Gets the current rolling amount minted (+) or burned (-)
    /// @notice by the Overlay market
    /// @dev minted_ > 0 means more OVL has been minted than burned recently
    /// @return minted_ as the current rolling amount minted
    function minted(IOverlayV1Market market) external view returns (int256 minted_) {
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
}
