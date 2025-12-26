// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract NestedMapping {
    mapping(address => mapping(address => uint256)) public allowances;
    mapping(uint256 => mapping(uint256 => bool)) public grid;
    mapping(address => mapping(uint256 => mapping(address => uint256))) public deepNested;

    function setAllowance(address owner, address spender, uint256 amount) public {
        allowances[owner][spender] = amount;
    }

    function setGrid(uint256 x, uint256 y, bool value) public {
        grid[x][y] = value;
    }

    function setDeepNested(address a, uint256 b, address c, uint256 value) public {
        deepNested[a][b][c] = value;
    }

    function getAllowance(address owner, address spender) public view returns (uint256) {
        return allowances[owner][spender];
    }
}
