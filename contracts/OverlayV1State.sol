// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "./interfaces/IOverlayV1State.sol";

import "./state/OverlayV1BaseState.sol";
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
    OverlayV1PositionState
{
    constructor(IOverlayV1Factory _factory) OverlayV1BaseState(_factory) {}
}
