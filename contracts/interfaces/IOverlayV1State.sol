// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "./state/IOverlayV1BaseState.sol";
import "./state/IOverlayV1PriceState.sol";
import "./state/IOverlayV1OIState.sol";
import "./state/IOverlayV1PositionState.sol";

interface IOverlayV1State is
    IOverlayV1BaseState,
    IOverlayV1PriceState,
    IOverlayV1OIState,
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

    function state(address feed) external view returns (MarketState memory state_);
}
