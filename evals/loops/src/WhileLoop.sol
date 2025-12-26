// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract WhileLoop {
    uint256 public number;

    function loop(uint256 loops) public {
        uint256 i = 0;
        while (i < loops) {
            number = number + 1;
            i = i + 1;
        }
    }
}
