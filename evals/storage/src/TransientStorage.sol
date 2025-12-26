// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

contract TransientStorage {
    uint256 transient counter;
    address transient tempOwner;
    bool transient locked;

    function incrementCounter() public {
        counter = counter + 1;
    }

    function setTempOwner(address owner) public {
        tempOwner = owner;
    }

    function lock() public {
        locked = true;
    }

    function unlock() public {
        locked = false;
    }

    function getCounter() public view returns (uint256) {
        return counter;
    }

    function isLocked() public view returns (bool) {
        return locked;
    }
}
