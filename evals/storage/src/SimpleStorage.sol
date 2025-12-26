// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract SimpleStorage {
    uint256 public value;
    address public owner;
    bool public initialized;

    function setValue(uint256 _value) public {
        value = _value;
    }

    function setOwner(address _owner) public {
        owner = _owner;
    }

    function initialize() public {
        initialized = true;
    }

    function reset() public {
        value = 0;
        owner = address(0);
        initialized = false;
    }
}
