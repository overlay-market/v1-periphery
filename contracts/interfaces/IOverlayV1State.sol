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
{}
