# heimdall-eval

![splash preview](./preview.png?raw=true)

Structured evaluation framework for [heimdall-rs](https://github.com/jon-becker/heimdall-rs)'s decompilation and CFG generation using an LLM judge via [OpenRouter](https://openrouter.ai).

## Overview

heimdall-eval provides a structured approach to evaluating and benchmarking Heimdall's decompilation accuracy and CFG generation quality. It uses an LLM judge to compare decompiled output against original Solidity source code, scoring based on logical preservation rather than syntactic similarity.

The evaluation framework assesses:
- Decompilation accuracy (arithmetic, control flow, storage operations, external calls)
- Control flow graph completeness and correctness

## Project Structure

```
heimdall-eval/
├── evals/           # Solidity test cases (Foundry projects)
│   ├── loops/       # Can contain multiple contracts
│   ├── nested-mappings/
│   ├── seaport/         # Seaport 1.1 marketplace
│   ├── uniswap-v2/      # Uniswap V2 USDC/WETH pair
│   ├── uniswap-v3-swaprouter/
│   ├── usdt/
│   └── weth9/
├── heimdall/        # Decompiled outputs and evaluation results
│   ├── <Contract>/  # Output per contract
│   └── evals.json   # Aggregated scores
├── prompts/         # LLM evaluation prompts
├── scripts/         # Build and evaluation scripts (incl. the OpenRouter judge)
└── Makefile
```

## Usage

### Prerequisites

- [Heimdall](https://github.com/jon-becker/heimdall-rs) installed and available in PATH
- [Foundry](https://getfoundry.sh/) for compiling Solidity test cases
- `jq` for aggregating scores
- Python 3.9+ (standard library only, no third-party packages required)
- An [OpenRouter](https://openrouter.ai) API key exported as `OPENROUTER_API_KEY`

### Configuration

The judge is configured entirely through environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | _(required)_ | OpenRouter API key. Read from the environment only; it is never written to disk or logged. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Base URL of the OpenAI-compatible API. |
| `EVAL_MODEL` | `anthropic/claude-sonnet-4.5` | OpenRouter model slug used as the judge. |
| `EVAL_TEMPERATURE` | `0` | Sampling temperature, sent to OpenRouter as a numeric JSON value. Whether it is honored is provider and model dependent; some models ignore or clamp it. |
| `EVAL_TIMEOUT` | `300` | Per-request timeout, in seconds. |
| `EVAL_MAX_RETRIES` | `3` | Retries for transient failures only (HTTP 408, 409, 429, 5xx, and network errors). |
| `EVAL_RETRY_BACKOFF` | `2` | Base backoff in seconds; doubles on each retry. |
| `PYTHON` | `python3` | Python interpreter used to run the judge. |

```bash
export OPENROUTER_API_KEY=...
make eval-all
```

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

Run the judge's unit tests:
```bash
make test
```

### Results

Evaluation scores are written to `heimdall/evals.json`:
```json
{
  "SimpleLoop": { "cfg": 100, "decompilation": 25 },
  "NestedLoop": { "cfg": 100, "decompilation": 25 },
  "WhileLoop": { "cfg": 100, "decompilation": 25 },
  "WETH9": { "cfg": 100, "decompilation": 65 }
}
```

### HTML Report

`scripts/report.py` renders a small static report comparing two decompilation runs.
It uses only the Python standard library (3.9+), embeds its own styles, and loads nothing at
runtime, so the report can be published or attached as an artifact as-is.

Each run directory is a `heimdall/` output directory:

```
<run>/<Contract>/decompiled.sol   decompiled source (absent if heimdall produced none)
<run>/<Contract>/eval.json        judge result: { "score", "summary", "differences" }
<run>/<Contract>/error.txt        error text, written when the run failed
```

The requested report file is a minimal index: it names the two versions being compared and
links to each evaluation. A sibling directory named after the report file (for example,
`report/` beside `report.html`) contains one self-contained detail page per contract. Each detail
page includes the status, baseline and candidate LLM judgements, both sources, and a unified diff.
Unchanged contracts are kept and render an explicit "identical" diff state. By default, the
report includes only contracts with an LLM result (`eval.json`) in at least one run; this avoids
listing decompilation-only artifacts. Pass `--include-unevaluated` to `scripts/report.py` to
include every generated artifact. When regenerating a report, obsolete detail pages are removed.

```bash
make report BASELINE=heimdall/baseline CANDIDATE=heimdall REPORT=heimdall/report.html
```

Or directly:

```bash
python3 scripts/report.py \
  --baseline heimdall/baseline \
  --candidate heimdall \
  --output heimdall/report.html
```

Run the report unit tests with:

```bash
make test
```

## Adding Test Cases

1. Create a new Foundry project in `evals/<name>/`
2. Add Solidity source files to `evals/<name>/src/` (supports multiple contracts per eval)
3. Run `make eval <name>` to generate and evaluate decompiled output

Each eval can contain multiple contracts. For example, the `loops` eval contains `SimpleLoop.sol`, `NestedLoop.sol`, and `WhileLoop.sol`, which are all evaluated together.

## Mainnet Contract Evals

The protocol evals use verified mainnet source and compiler settings. Their `.clone.meta`
files record the evaluated deployment:

| Eval | Contract | Mainnet address |
| --- | --- | --- |
| `usdt` | TetherToken (USDT) | `0xdAC17F958D2ee523a2206206994597C13D831ec7` |
| `uniswap-v2` | UniswapV2Pair (USDC/WETH) | `0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc` |
| `uniswap-v3-swaprouter` | SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` |
| `seaport` | Seaport 1.1 | `0x00000000006c3852cbEf3e08E8dF289169EdE581` |

`SwapRouter.sol` and `Seaport.sol` are flattened entry sources so the LLM judge receives
the complete implementation; their imported source trees remain alongside them for Foundry.

## Contributing

If you'd like to contribute test cases or improve the evaluation prompts, please open a pull-request with your changes.

## Issues

If you've found an issue or have a question, please open an issue [here](https://github.com/jon-becker/heimdall-eval/issues).

## Credits

heimdall-eval is maintained by [Jonathan Becker](https://jbecker.dev) as part of the [Heimdall](https://github.com/jon-becker/heimdall-rs) project.
