// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Script, console2} from "forge-std/Script.sol";
import {IOverlayV1Factory} from "@overlay-protocol/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import {OverlayV1State} from "contracts/OverlayV1State.sol";
import {ArbSepoliaConfig} from "scripts/config/ArbSepolia.config.sol";
import {ArbMainnetConfig} from "scripts/config/ArbMainnet.config.sol";

// 1. Set required environment variables: ETHERSCAN_API_KEY, DEPLOYER_PK, RPC.
// 2. Update the config file for the network you are deploying to.
// 3. Run with:
// $ source .env
// $ forge script scripts/state/Deploy.s.sol:DeployScript --rpc-url $RPC --verify -vvvv --broadcast

contract DeployScript is Script {
    function run() external {
        uint256 DEPLOYER_PK = vm.envUint("DEPLOYER_PK");

        vm.startBroadcast(DEPLOYER_PK);

        // <!---- START DEPLOYMENT ---->

        OverlayV1State state = new OverlayV1State(IOverlayV1Factory(ArbSepoliaConfig.V1_FACTORY));

        // <!-- END DEPLOYMENT -->

        vm.stopBroadcast();

        console2.log("OverlayV1State deployed at:", address(state));
    }
}
