.PHONY: run run-all eval eval-all

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

# Catch-all to prevent "Nothing to be done" for target arguments
%:
	@:
