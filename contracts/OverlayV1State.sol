// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "./interfaces/IOverlayV1State.sol";

import "./state/OverlayV1BaseState.sol";
import "./state/OverlayV1EstimateState.sol";
import "./state/OverlayV1OIState.sol";
import "./state/OverlayV1PositionState.sol";
import "./state/OverlayV1PriceState.sol";

/// @title A market state contract to view the current state of
/// @title an Overlay market
contract OverlayV1State is
    IOverlayV1State,
    OverlayV1BaseState,
    OverlayV1PriceState,
    OverlayV1OIState,
    OverlayV1EstimateState,
    OverlayV1PositionState
{
    constructor(IOverlayV1Factory _factory) OverlayV1BaseState(_factory) {}

    /// @notice Gets relevant market info to aggregate calls into a
    /// @notice single function
    /// @dev WARNING: makes many calls to market
    /// @return state_ as the current aggregate market state
    function marketState(IOverlayV1Market market)
        external
        view
        returns (MarketState memory state_)
    {
        address feed = market.feed();
        Oracle.Data memory data = _getOracleData(feed);

        (uint256 oiLong, uint256 oiShort) = _ois(market);
        state_ = MarketState({
            bid: _bid(market, data, 0),
            ask: _ask(market, data, 0),
            mid: _mid(data),
            volumeBid: _volumeBid(market, data, 0),
            volumeAsk: _volumeAsk(market, data, 0),
            oiLong: oiLong,
            oiShort: oiShort,
            capOi: _capOi(market, data),
            circuitBreakerLevel: _circuitBreakerLevel(market),
            fundingRate: _fundingRate(market)
        });
    }
}
