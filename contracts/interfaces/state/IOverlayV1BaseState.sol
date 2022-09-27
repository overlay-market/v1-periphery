// SPDX-License-Identifier: MIT
pragma solidity 0.8.10;

import "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Market.sol";
import "@overlay-protocol/v1-core/contracts/libraries/Oracle.sol";

interface IOverlayV1BaseState {
    // immutables
    function factory() external view returns (IOverlayV1Factory);

    // market associated with given feed
    function market(address feed) external view returns (IOverlayV1Market market_);

    // latest oracle data associated with given feed
    function data(address feed) external view returns (Oracle.Data memory data_);
}
