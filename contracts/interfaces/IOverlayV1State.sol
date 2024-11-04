// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Market.sol";

import "./state/IOverlayV1BaseState.sol";
import "./state/IOverlayV1PriceState.sol";
import "./state/IOverlayV1OIState.sol";
import "./state/IOverlayV1PositionState.sol";
import "./state/IOverlayV1EstimateState.sol";

interface IOverlayV1State is
    IOverlayV1BaseState,
    IOverlayV1PriceState,
    IOverlayV1OIState,
    IOverlayV1EstimateState,
    IOverlayV1PositionState
{
    struct MarketState {
        uint256 bid;
        uint256 ask;
        uint256 mid;
        uint256 volumeBid;
        uint256 volumeAsk;
        uint256 oiLong;
        uint256 oiShort;
        uint256 capOi;
        uint256 circuitBreakerLevel;
        int256 fundingRate;
    }

    function marketState(IOverlayV1Market market)
        external
        view
        returns (MarketState memory state_);
}
