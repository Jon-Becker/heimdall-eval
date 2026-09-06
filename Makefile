.PHONY: run run-all eval eval-all add report test

# Support both `make run <target>` and `make run TARGET=<target>`
TARGET := $(if $(TARGET),$(TARGET),$(word 2,$(MAKECMDGOALS)))

# Export DEV for scripts
export DEV

# HTML evaluation report inputs/outputs (override on the command line)
BASELINE ?= heimdall/baseline
CANDIDATE ?= heimdall
REPORT ?= heimdall/report.html

run:
ifeq ($(TARGET),)
	@./scripts/run.sh
else
	@./scripts/run.sh $(TARGET)
endif

run-all:
	@./scripts/run.sh --all

eval:
ifeq ($(TARGET),)
	@./scripts/eval.sh
else
	@./scripts/eval.sh $(TARGET)
endif

eval-all:
	@./scripts/eval.sh --all

report:
	@python3 scripts/report.py --baseline $(BASELINE) --candidate $(CANDIDATE) --output $(REPORT)

test:
	@python3 -m unittest discover -s scripts -p 'test_*.py'

add:
ifeq ($(TARGET),)
	@echo "Usage: make add <eval-name>"
	@exit 1
else
	@mkdir -p evals/$(TARGET)
	@cd evals/$(TARGET) && forge init --no-git
	@rm -rf evals/$(TARGET)/.git
	@rm -rf evals/$(TARGET)/script
	@rm -rf evals/$(TARGET)/test
	@rm -rf evals/$(TARGET)/src/Counter.sol
	@echo "Created new eval: evals/$(TARGET)"
endif

# Catch-all to prevent "Nothing to be done" for target arguments
%:
	@:
