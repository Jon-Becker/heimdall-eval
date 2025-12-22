/// @title            Decompiled Contract
/// @author           Jonathan Becker <jonathan@jbecker.dev>
/// @custom:version   heimdall-rs v0.9.2+nightly.41fda31
///
/// @notice           This contract was decompiled using the heimdall-rs decompiler.
///                     It was generated directly by tracing the EVM opcodes from this contract.
///                     As a result, it may not compile or even be valid yul code.
///                     Despite this, it should be obvious what each function does. Overall
///                     logic should have been preserved throughout decompiling.
///
/// @custom:github    You can find the open-source decompiler here:
///                       https://heimdall.rs

object "DecompiledContract" {
    object "runtime" {
        code {
            
            function selector() -> s {
                s := div(calldataload(0), 0x100000000000000000000000000000000000000000000000000000000)
            }
            
            function castToAddress(x) -> a {
                a := and(x, 0xffffffffffffffffffffffffffffffffffffffff)
            }
            
            switch selector()
            
            /*
            * @custom:signature    loop(uint256 arg0) public view
            * @param                arg0 ["uint256", "bytes32", "int256"]
            */
            case 0x0b7d796e {
                if iszero(slt(sub(add(0x04, sub(calldatasize(), 0x04)), 0x04), 0x20)) {
                    if eq(calldataload(0x04), calldataload(0x04)) { revert(0, 0); } else {
                        if iszero(lt(0, calldataload(0x04))) {
                            if iszero(gt(sload(0), add(sload(0), 0x01))) { revert(0, 0); } else {
                                mstore(0, 0x4e487b7100000000000000000000000000000000000000000000000000000000)
                                mstore(0x04, 0x11)
                            }
                        }
                    }
                }
            }
            
            /*
            * @custom:signature    number() public view returns (uint256)
            */
            case 0x8381f58a {
                mstore(0x80, sload(0))
                return(mload(0x40), sub(add(mload(0x40), 0x20), mload(0x40)))
            }
            default { revert(0, 0) }
        }
    }
}