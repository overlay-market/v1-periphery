// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "./IOverlayV1BaseState.sol";
import "./IOverlayV1PriceState.sol";

interface IOverlayV1OIState is IOverlayV1BaseState, IOverlayV1PriceState {
    // aggregate open interest values on market associated with feed
    function ois(address feed) external view returns (uint256 oiLong_, uint256 oiShort_);

    // cap on aggregate open interest on market associated with feed
    function capOi(address feed) external view returns (uint256 capOi_);

    // fraction of cap on aggregate open interest given oi amount
    function fractionOfCapOi(address feed, uint256 oi)
        external
        view
        returns (uint256 fractionOfCapOi_);

    // funding rate on market associated with feed
    function fundingRate(address feed) external view returns (int256 fundingRate_);

    // circuit breaker level on market associated with feed
    function circuitBreakerLevel(address feed)
        external
        view
        returns (uint256 circuitBreakerLevel_);

    // rolling minted amount on market associated with feed
    function minted(address feed) external view returns (int256 minted_);
}
