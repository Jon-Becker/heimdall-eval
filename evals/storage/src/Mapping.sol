// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Mapping {
    mapping(address => uint256) public balances;
    mapping(uint256 => address) public owners;
    mapping(address => bool) public registered;

    function setBalance(address account, uint256 amount) public {
        balances[account] = amount;
    }

    function setOwner(uint256 tokenId, address owner) public {
        owners[tokenId] = owner;
    }

    function register(address account) public {
        registered[account] = true;
    }

    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }
}
