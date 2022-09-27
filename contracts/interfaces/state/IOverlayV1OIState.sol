// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Market.sol";

import "./IOverlayV1BaseState.sol";
import "./IOverlayV1PriceState.sol";

interface IOverlayV1OIState is IOverlayV1BaseState, IOverlayV1PriceState {
    // aggregate open interest values on market
    function ois(IOverlayV1Market market)
        external
        view
        returns (uint256 oiLong_, uint256 oiShort_);

    // cap on aggregate open interest on market
    function capOi(IOverlayV1Market market) external view returns (uint256 capOi_);

    // fraction of cap on aggregate open interest given oi amount
    function fractionOfCapOi(IOverlayV1Market market, uint256 oi)
        external
        view
        returns (uint256 fractionOfCapOi_);

    // funding rate on market
    function fundingRate(IOverlayV1Market market) external view returns (int256 fundingRate_);

    // circuit breaker level on market
    function circuitBreakerLevel(IOverlayV1Market market)
        external
        view
        returns (uint256 circuitBreakerLevel_);

    // rolling minted amount on market
    function minted(IOverlayV1Market market) external view returns (int256 minted_);
}
