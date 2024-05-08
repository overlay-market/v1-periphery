// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Script, console2} from "forge-std/Script.sol";
import {IOverlayV1Factory} from "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import {OverlayV1State} from "contracts/OverlayV1State.sol";

// 1. Set required environment variables: ETHERSCAN_API_KEY, DEPLOYER_PK, RPC.
// 2. Run with:
// $ source .env
// $ forge script scripts/state/Deploy.s.sol:DeployScript --rpc-url $RPC --verify -vvvv --broadcast

contract DeployScript is Script {
    // TODO: update values as needed
    address constant FACTORY = 0x8cCD181113c7Ae40f31D5e8178a98A1A60B55c4C;

    function run() external {
        uint256 DEPLOYER_PK = vm.envUint("DEPLOYER_PK");

        vm.startBroadcast(DEPLOYER_PK);

        // <!---- START DEPLOYMENT ---->

        OverlayV1State state = new OverlayV1State(IOverlayV1Factory(FACTORY));

        // <!-- END DEPLOYMENT -->

        vm.stopBroadcast();

        console2.log("OverlayV1State deployed at:", address(state));
    }
}
