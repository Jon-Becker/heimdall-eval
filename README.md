# heimdall-eval

![splash preview](./preview.png?raw=true)

Structured evaluation framework for [heimdall-rs](https://github.com/jon-becker/heimdall-rs)'s decompilation and CFG generation using Claude as an LLM judge.

## Overview

heimdall-eval provides a structured approach to evaluating and benchmarking Heimdall's decompilation accuracy and CFG generation quality. It uses Claude as an LLM judge to compare decompiled output against original Solidity source code, scoring based on logical preservation rather than syntactic similarity.

The evaluation framework assesses:
- Decompilation accuracy (arithmetic, control flow, storage operations, external calls)
- Control flow graph completeness and correctness

## Project Structure

```
heimdall-eval/
├── evals/           # Solidity test cases (Foundry projects)
│   ├── nested-loop/
│   ├── simple-loop/
│   ├── weth9/
│   └── while-loop/
├── heimdall/        # Decompiled outputs and evaluation results
├── prompts/         # LLM evaluation prompts
│   ├── CFG_PROMPT.md
│   └── DECOMPILATION_PROMPT.md
└── Makefile         # Build and evaluation commands
```

## Usage

### Prerequisites

- [Heimdall](https://github.com/jon-becker/heimdall-rs) installed and available in PATH
- [Foundry](https://getfoundry.sh/) for compiling Solidity test cases
- [Claude Code](https://github.com/anthropics/claude-code) CLI for running evaluations

### Commands

Run decompilation on a specific target:
```bash
make run <target>
```

Run decompilation on all targets:
```bash
make run-all
```

Evaluate a specific target (runs decompilation + LLM evaluation):
```bash
make eval <target>
```

Evaluate all targets:
```bash
make eval-all
```

Use a development build of Heimdall:
```bash
make eval-all DEV=1
```

### Results

Evaluation scores are written to `heimdall/evals.json`:
```json
{
  "SimpleLoop": { "cfg": 85, "decompilation": 25 },
  "WhileLoop": { "cfg": 75, "decompilation": 25 },
  "NestedLoop": { "cfg": 50, "decompilation": 25 },
  "WETH9": { "cfg": 100, "decompilation": 45 }
}
```

## Adding Test Cases

1. Create a new Foundry project in `evals/<name>/`
2. Add Solidity source files to `evals/<name>/src/`
3. Run `make eval <name>` to generate and evaluate decompiled output

## Contributing

If you'd like to contribute test cases or improve the evaluation prompts, please open a pull-request with your changes.

## Issues

If you've found an issue or have a question, please open an issue [here](https://github.com/jon-becker/heimdall-eval/issues).

## Credits

heimdall-eval is maintained by [Jonathan Becker](https://jbecker.dev) as part of the [Heimdall](https://github.com/jon-becker/heimdall-rs) project.
