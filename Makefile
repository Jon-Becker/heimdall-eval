.PHONY: run run-all eval eval-all

# Support both `make run <target>` and `make run TARGET=<target>`
TARGET := $(if $(TARGET),$(TARGET),$(word 2,$(MAKECMDGOALS)))

# Use dev build if DEV=1 is passed (e.g., make eval-all DEV=1)
HEIMDALL := $(if $(DEV),/Users/jonathanbecker/Documents/github/heimdall-rs/target/release/heimdall,heimdall)

run:
ifeq ($(TARGET),)
	@echo "Available targets:"
	@ls -d evals/*/ 2>/dev/null | xargs -n1 basename || echo "  (none found)"
	@echo ""
	@echo "Usage: make run <target>"
else
	cd ./evals/$(TARGET) && forge build
	@for json in ./evals/$(TARGET)/out/*/*.json; do \
		name=$$(basename "$$json" .json); \
		bytecode=$$(jq -r '.deployedBytecode.object // .deployedBytecode // empty' "$$json" 2>/dev/null); \
		if [ -n "$$bytecode" ] && [ "$$bytecode" != "null" ] && [ "$$bytecode" != "0x" ]; then \
			echo "Processing $$name..."; \
			$(HEIMDALL) decompile "$$bytecode" -d -vvv -o ./heimdall/$$name --include-sol || true; \
			$(HEIMDALL) cfg "$$bytecode" -d -vvv -o ./heimdall/$$name || true; \
		fi; \
	done
endif

run-all:
	@for dir in $$(ls -d evals/*/ 2>/dev/null | xargs -n1 basename); do \
		echo "=== Running $$dir ==="; \
		$(MAKE) run TARGET=$$dir DEV=$(DEV); \
	done

eval:
ifeq ($(TARGET),)
	@echo "Usage: make eval <target>"
else
	$(MAKE) run TARGET=$(TARGET) DEV=$(DEV)
	@for sol in ./evals/$(TARGET)/src/*.sol; do \
		name=$$(basename "$$sol" .sol); \
		decompiled="./heimdall/$$name/decompiled.sol"; \
		cfg="./heimdall/$$name/cfg.dot"; \
		if [ -f "$$decompiled" ]; then \
			echo "=== Evaluating $$name (decompiled) ==="; \
			prompt="$$(cat prompts/DECOMPILATION_PROMPT.md)\n\nOriginal:\n$$(cat $$sol)\n\nDecompiled:\n$$(cat $$decompiled)"; \
			ANTHROPIC_MODEL="claude-haiku-4-5" claude --dangerously-skip-permissions --model claude-haiku-4-5 -p "$$prompt" | sed 's/^```json//; s/^```//; s/```$$//' | jq . > "./heimdall/$$name/eval.json"; \
			echo "Output written to ./heimdall/$$name/eval.json"; \
		else \
			echo "Skipping $$name: no decompiled output found"; \
		fi; \
		if [ -f "$$cfg" ]; then \
			echo "=== Evaluating $$name (CFG) ==="; \
			prompt="$$(cat prompts/CFG_PROMPT.md)\n\nOriginal Solidity:\n$$(cat $$sol)\n\nCFG (dot format):\n$$(cat $$cfg)"; \
			claude --dangerously-skip-permissions -p "$$prompt" | sed 's/^```json//; s/^```//; s/```$$//' | jq . > "./heimdall/$$name/cfg_eval.json"; \
			echo "Output written to ./heimdall/$$name/cfg_eval.json"; \
		else \
			echo "Skipping $$name CFG: no cfg.dot found"; \
		fi; \
		decompilation_score=$$(jq -r '.score // empty' "./heimdall/$$name/eval.json" 2>/dev/null); \
		cfg_score=$$(jq -r '.score // empty' "./heimdall/$$name/cfg_eval.json" 2>/dev/null); \
		if [ -n "$$decompilation_score" ] || [ -n "$$cfg_score" ]; then \
			cfg_val=$${cfg_score:-null}; \
			dec_val=$${decompilation_score:-null}; \
			if [ -f "./heimdall/evals.json" ]; then \
				jq --arg name "$$name" --argjson cfg "$$cfg_val" --argjson dec "$$dec_val" \
					'. + {($$name): {cfg: $$cfg, decompilation: $$dec}}' \
					"./heimdall/evals.json" > "./heimdall/evals.json.tmp" && mv "./heimdall/evals.json.tmp" "./heimdall/evals.json"; \
			else \
				jq -n --arg name "$$name" --argjson cfg "$$cfg_val" --argjson dec "$$dec_val" \
					'{($$name): {cfg: $$cfg, decompilation: $$dec}}' > "./heimdall/evals.json"; \
			fi; \
		fi; \
	done
	@echo "Updated ./heimdall/evals.json"
endif

eval-all:
	@for dir in $$(ls -d evals/*/ 2>/dev/null | xargs -n1 basename); do \
		echo "=== Evaluating $$dir ==="; \
		$(MAKE) eval TARGET=$$dir DEV=$(DEV); \
	done

# Catch-all to prevent "Nothing to be done" for target arguments
%:
	@:
