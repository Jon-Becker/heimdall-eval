// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract NestedMappings {
    mapping(address => mapping(address => uint256)) public allowances;

    function allowance(address owner, address spender) public view returns (uint256) {
        return allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) public {
        allowances[msg.sender][spender] = amount;
    }
}
