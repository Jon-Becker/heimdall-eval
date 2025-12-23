<decompilation_evaluation>
	<task>
Evaluate how well the decompiled output preserves the functional logic of the original Solidity source. Compare the original Solidity source against the decompiled output from EVM bytecode. Determine if the decompiled code accurately represents the same logical operations, control flow, and state changes.
</task>
	<scoring_criteria>
		<what_matters>
			<item>Arithmetic and logical operations are preserved</item>
			<item>Control flow structure matches (conditionals, loops, branches)</item>
			<item>Storage read/write operations correspond to original state variables</item>
			<item>External calls are preserved (target, calldata structure, return handling)</item>
			<item>Event emissions are captured (even if parameter names differ)</item>
			<item>Modifier logic is inlined correctly</item>
			<item>Return values and revert conditions match</item>
			<item>Function visibility and mutability behavior is equivalent</item>
		</what_matters>
		<expected_losses_do_not_penalize>
			<item>Variable names (will be generic like var0, stor1, arg0)</item>
			<item>Function names (will be selector-based like func_a9059cbb)</item>
			<item>Contract names</item>
			<item>Comments and documentation</item>
			<item>Custom error names (reverts may show raw selectors)</item>
			<item>Event names (may show topic hashes)</item>
			<item>Struct and enum names</item>
			<item>Import statements</item>
			<item>License identifiers</item>
			<item>Formatting and code style</item>
			<item>NatSpec documentation</item>
		</expected_losses_do_not_penalize>
		<acceptable_syntax>
			<item>Invalid Solidity syntax is acceptable if logic is clear</item>
			<item>Pseudo-code representations of complex operations</item>
			<item>Assembly-like notation for low-level operations</item>
			<item>Inline storage slot calculations</item>
			<item>Raw selector references instead of function names</item>
		</acceptable_syntax>
		<scoring_guidelines>
			<score_range min="100" max="100">All logical operations and control flow perfectly preserved</score_range>
			<score_range min="80" max="99">Logic preserved with minor representation differences</score_range>
			<score_range min="60" max="79">Core logic present but some operations unclear or slightly off</score_range>
			<score_range min="40" max="59">Significant logic gaps or incorrect operation representation</score_range>
			<score_range min="0" max="39">Decompilation fails to capture fundamental program behavior</score_range>
		</scoring_guidelines>
	</scoring_criteria>
	<examples>
		<example>
			<original>
function transfer(address to, uint256 amount) public returns (bool) {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    balances[msg.sender] -= amount;
    balances[to] += amount;
    emit Transfer(msg.sender, to, amount);
    return true;
}
</original>
			<decompiled>
function func_a9059cbb(address arg0, uint256 arg1) public returns (bool) {
    require(stor_balances[msg.sender] >= arg1);
    stor_balances[msg.sender] = stor_balances[msg.sender] - arg1;
    stor_balances[arg0] = stor_balances[arg0] + arg1;
    emit Event_ddf252ad(msg.sender, arg0, arg1);
    return 1;
}
</decompiled>
			<score>100</score>
			<reasoning>All operations preserved: balance check, subtraction, addition, event emission, return. Name loss is expected and not penalized.</reasoning>
		</example>
		<example>
			<original>
function withdraw(uint256 amount) external {
    require(deposits[msg.sender] >= amount);
    deposits[msg.sender] -= amount;
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
}
</original>
			<decompiled>
function func_2e1a7d4d(uint256 arg0) external {
    if (stor0[msg.sender] &lt; arg0) { revert(); }
    stor0[msg.sender] -= arg0;
    call(msg.sender, arg0);
}
</decompiled>
			<score>70</score>
			<reasoning>Core logic present but missing the success check on the external call, which is a functional difference.</reasoning>
		</example>
		<example>
			<original>
function complexMath(uint256 a, uint256 b) pure returns (uint256) {
    return (a * b + a) / (b + 1);
}
</original>
			<decompiled>
function func_12345678(uint256 arg0, uint256 arg1) pure returns (uint256) {
    return (arg0 * arg1 + arg0) / (arg1 + 1);
}
</decompiled>
			<score>100</score>
			<reasoning>Mathematical operations exactly preserved despite name loss.</reasoning>
		</example>
		<example>
			<original>
function swap(uint256 amount) external {
    uint256 fee = amount * 3 / 1000;
    uint256 output = amount - fee;
    token.transfer(msg.sender, output);
}
</original>
			<decompiled>
function func_94b918de(uint256 arg0) external {
    var0 = arg0 * 3;
    var1 = var0 / 1000;
    var2 = arg0 - var1;
    extcall(stor0, 0xa9059cbb, msg.sender, var2);
}
</decompiled>
			<score>100</score>
			<reasoning>Fee calculation logic preserved exactly. External call to transfer captured with correct parameters. Variable naming loss is expected.</reasoning>
		</example>
	</examples>
	<output_instructions>
		<instruction>Write the evaluation result directly to the specified output file as JSON</instruction>
		<instruction>Only list functional differences, not cosmetic changes like naming or formatting</instruction>
		<format>
{
  "score": 0-100,
  "summary": "brief functional assessment of decompilation quality",
  "differences": ["functional difference that affects program behavior"]
}
</format>
	</output_instructions>
</decompilation_evaluation>
