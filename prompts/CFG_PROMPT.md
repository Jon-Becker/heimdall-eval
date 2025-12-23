<cfg_evaluation>
	<task>
Evaluate how completely the extracted CFG captures control flow paths from the original Solidity source. Analyze the CFG (in DOT format) extracted from EVM bytecode and compare it against the original Solidity source code. Determine if the CFG captures all logical control flow paths present in the source.
</task>
	<scoring_criteria>
		<what_matters>
			<item>All conditional branches from the source (if/else, ternary operators) are represented</item>
			<item>All loop structures (for, while, do-while) have proper entry, body, and exit paths</item>
			<item>All function entry and exit points are captured</item>
			<item>Revert/require/assert paths are represented</item>
			<item>External call paths and their potential failure branches</item>
			<item>Switch-like patterns (multiple if-else chains) are fully captured</item>
		</what_matters>
		<what_does_not_reduce_score>
			<item>Compiler-added paths (overflow checks, underflow checks, array bounds checks)</item>
			<item>Optimizer-generated branches</item>
			<item>Internal compiler dispatch logic</item>
			<item>Stack management paths</item>
			<item>Memory expansion checks</item>
			<item>Gas stipend checks</item>
			<item>Reentrancy guard paths added by compiler</item>
			<item>Any "extra" paths not in source - the CFG goal is COMPLETENESS</item>
		</what_does_not_reduce_score>
		<scoring_guidelines>
			<score_range min="100" max="100">All source control flow paths are represented in the CFG</score_range>
			<score_range min="80" max="99">Minor paths missing (e.g., one edge case branch)</score_range>
			<score_range min="60" max="79">Some logical branches missing but main flow intact</score_range>
			<score_range min="40" max="59">Significant control flow missing (loops or major conditionals)</score_range>
			<score_range min="0" max="39">CFG fails to capture fundamental program structure</score_range>
		</scoring_guidelines>
	</scoring_criteria>
	<important_notes>
		<note>The CFG is extracted from compiled bytecode, so it will contain paths the compiler added</note>
		<note>Extra paths from the compiler are expected and acceptable - do NOT score down for these</note>
		<note>Only score down for missing paths that exist in the original source logic</note>
		<note>Node labels may be cryptic (hex addresses, opcodes) - focus on graph structure, not labels</note>
	</important_notes>
	<examples>
		<example>
			<scenario>Original has a simple if/else, CFG shows the branch plus compiler overflow checks</scenario>
			<score>100</score>
			<reasoning>The logical if/else branch is captured. Extra overflow check paths are compiler-added and do not reduce the score.</reasoning>
		</example>
		<example>
			<scenario>Original has a for loop, CFG shows loop entry, condition check, body, increment, and exit</scenario>
			<score>100</score>
			<reasoning>All loop control flow elements are present.</reasoning>
		</example>
		<example>
			<scenario>Original has try/catch, CFG only shows the try path, missing catch branches</scenario>
			<score>60</score>
			<reasoning>Missing error handling paths is a significant omission.</reasoning>
		</example>
		<example>
			<scenario>Original has nested if statements with 4 branches, CFG only shows 2 branches</scenario>
			<score>50</score>
			<reasoning>Half of the conditional logic is missing from the CFG.</reasoning>
		</example>
	</examples>
	<output_instructions>
		<instruction>Write the evaluation result directly to the specified output file as JSON</instruction>
		<instruction>The extra_paths field is informational only and should NOT affect the score</instruction>
		<format>
{
  "score": 0-100,
  "summary": "brief assessment of CFG completeness",
  "missing_paths": ["description of missing path from source logic"],
  "extra_paths": ["compiler-added path, for reference only, does not affect score"],
  "observations": ["noteworthy finding about the CFG"]
}
</format>
	</output_instructions>
</cfg_evaluation>
