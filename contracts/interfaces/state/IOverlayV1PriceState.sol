// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay/v1-core/contracts/interfaces/IOverlayV1Market.sol";

import "./IOverlayV1BaseState.sol";

interface IOverlayV1PriceState is IOverlayV1BaseState {
    // bid on the market given new volume from fractionOfCapOi
    function bid(IOverlayV1Market market, uint256 fractionOfCapOi) external view returns (uint256 bid_);

    // ask on the market given new volume from fractionOfCapOi
    function ask(IOverlayV1Market market, uint256 fractionOfCapOi) external view returns (uint256 ask_);

    // mid on the market
    function mid(IOverlayV1Market market) external view returns (uint256 mid_);

    // volume on the bid of the market given new volume from fractionOfCapOi
    function volumeBid(IOverlayV1Market market, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeBid_);

    // volume on the ask of the market given new volume from fractionOfCapOi
    function volumeAsk(IOverlayV1Market market, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeAsk_);

    // bid, ask, mid prices of the market
    function prices(IOverlayV1Market market)
        external
        view
        returns (
            uint256 bid_,
            uint256 ask_,
            uint256 mid_
        );

    // bid, ask volumes of the market
    function volumes(IOverlayV1Market market) external view returns (uint256 volumeBid_, uint256 volumeAsk_);
}
