// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

contract Events {
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Deposit(address indexed account, uint256 amount);
    event Withdrawal(address indexed account, uint256 amount);
    event Log(string message);
    event LogBytes(bytes data);

    function emitTransfer(address from, address to, uint256 value) external {
        emit Transfer(from, to, value);
    }

    function emitApproval(address owner, address spender, uint256 value) external {
        emit Approval(owner, spender, value);
    }

    function emitDeposit(address account, uint256 amount) external {
        emit Deposit(account, amount);
    }

    function emitWithdrawal(address account, uint256 amount) external {
        emit Withdrawal(account, amount);
    }

    function emitLog(string calldata message) external {
        emit Log(message);
    }

    function emitLogBytes(bytes calldata data) external {
        emit LogBytes(data);
    }

    function emitMultiple(address account, uint256 amount) external {
        emit Deposit(account, amount);
        emit Transfer(address(0), account, amount);
        emit Log("Multiple events emitted");
    }
}
