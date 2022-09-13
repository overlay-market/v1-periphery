pragma solidity ^0.8.10;

import "forge-std/Script.sol";
import "@overlay/v1-core/contracts/interfaces/IOverlayV1Factory.sol";
import "../contracts/OverlayV1State.sol";

contract DeployState is Script {

  function run () external {

    address WALLET = vm.envAddress("WALLET");
    address FACTORY = vm.envAddress("OVL_V1_FACTORY");
    vm.startBroadcast(WALLET);

    OverlayV1State state = new OverlayV1State(IOverlayV1Factory(FACTORY));

    vm.stopBroadcast();

  }
}
