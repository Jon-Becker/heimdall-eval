.PHONY: run run-all eval eval-all add

# Support both `make run <target>` and `make run TARGET=<target>`
TARGET := $(if $(TARGET),$(TARGET),$(word 2,$(MAKECMDGOALS)))

# Export DEV for scripts
export DEV

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
