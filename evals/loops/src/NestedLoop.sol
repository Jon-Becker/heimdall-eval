// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract NestedLoop {
    uint256 public number;

    function loop(uint256 loops) public {
        for (uint256 i = 0; i < loops; i++) {
            for (uint256 j = 0; j < loops; j++) {
                number += 1;
            }
        }
    }
}
