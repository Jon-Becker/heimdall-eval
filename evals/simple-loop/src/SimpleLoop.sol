// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract SimpleLoop {
    uint256 public number;

    function loop(uint256 loops) public {
        for (uint256 i = 0; i < loops; i++) {
            number++;
        }
    }
}
