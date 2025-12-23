// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

/// @title            Decompiled Contract
/// @author           Jonathan Becker <jonathan@jbecker.dev>
/// @custom:version   heimdall-rs v0.9.2
///
/// @notice           This contract was decompiled using the heimdall-rs decompiler.
///                     It was generated directly by tracing the EVM opcodes from this contract.
///                     As a result, it may not compile or even be valid solidity code.
///                     Despite this, it should be obvious what each function does. Overall
///                     logic should have been preserved throughout decompiling.
///
/// @custom:github    You can find the open-source decompiler here:
///                       https://heimdall.rs

contract DecompiledContract {
    uint256 public number;
    
    
    /// @custom:selector    0x0b7d796e
    /// @custom:signature   loop(uint256 arg0) public payable
    /// @param              arg0 ["uint256", "bytes32", "int256"]
    function loop(uint256 arg0) public payable {
        for (uint256 i = 0; (i < arg0); i++) {
            for (uint256 j = 0; (j < arg0); j++) {
                number = number + 0x01;
            }
        }
    }
}