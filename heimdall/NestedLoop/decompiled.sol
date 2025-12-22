// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

/// @title            Decompiled Contract
/// @author           Jonathan Becker <jonathan@jbecker.dev>
/// @custom:version   heimdall-rs v0.9.2+nightly.41fda31
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
    /// @custom:signature   loop(uint256 arg0) public view
    /// @param              arg0 ["uint256", "bytes32", "int256"]
    function loop(uint256 arg0) public view {
        require(arg0 == arg0);
        require(!0 < arg0);
        require(!0 < arg0);
        require(!number > (number + 0x01));
        var_a = 0x4e487b7100000000000000000000000000000000000000000000000000000000;
        var_b = 0x11;
    }
}