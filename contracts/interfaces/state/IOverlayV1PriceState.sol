// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "./IOverlayV1BaseState.sol";

interface IOverlayV1PriceState is IOverlayV1BaseState {
    // bid on the market associated with the feed given new volume from fractionOfCapOi
    function bid(address feed, uint256 fractionOfCapOi) external view returns (uint256 bid_);

    // ask on the market associated with the feed given new volume from fractionOfCapOi
    function ask(address feed, uint256 fractionOfCapOi) external view returns (uint256 ask_);

    // mid on the market associated with the feed
    function mid(address feed) external view returns (uint256 mid_);

    // volume on the bid of the market associated with the feed given
    // new volume from fractionOfCapOi
    function volumeBid(address feed, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeBid_);

    // volume on the ask of the market associated with the feed given
    // new volume from fractionOfCapOi
    function volumeAsk(address feed, uint256 fractionOfCapOi)
        external
        view
        returns (uint256 volumeAsk_);

    // bid, ask, mid prices of the market associated with the feed
    function prices(address feed)
        external
        view
        returns (
            uint256 bid_,
            uint256 ask_,
            uint256 mid_
        );

    // bid, ask volumes of the market associated with the feed
    function volumes(address feed) external view returns (uint256 volumeBid_, uint256 volumeAsk_);
}
