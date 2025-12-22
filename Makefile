.PHONY: run run-all

# Support both `make run <target>` and `make run TARGET=<target>`
TARGET := $(if $(TARGET),$(TARGET),$(word 2,$(MAKECMDGOALS)))

run:
ifeq ($(TARGET),)
	@echo "Available targets:"
	@ls -d */ 2>/dev/null | sed 's/\///' | grep -v heimdall || echo "  (none found)"
	@echo ""
	@echo "Usage: make run <target>"
else
	cd ./$(TARGET) && forge build
	@mkdir -p ./heimdall/$(TARGET)
	@for json in ./$(TARGET)/out/*/*.json; do \
		name=$$(basename "$$json" .json); \
		bytecode=$$(jq -r '.deployedBytecode.object // .deployedBytecode // empty' "$$json" 2>/dev/null); \
		if [ -n "$$bytecode" ] && [ "$$bytecode" != "null" ] && [ "$$bytecode" != "0x" ]; then \
			echo "Processing $$name..."; \
			heimdall decompile "$$bytecode" -d -vvv -o ./heimdall/$(TARGET)/$$name --include-sol || true; \
			heimdall decompile "$$bytecode" -d -vvv -o ./heimdall/$(TARGET)/$$name --include-yul || true; \
			heimdall cfg "$$bytecode" -d -vvv -o ./heimdall/$(TARGET)/$$name || true; \
		fi; \
	done
endif

run-all:
	@for dir in $$(ls -d */ 2>/dev/null | sed 's/\///' | grep -v heimdall); do \
		echo "=== Running $$dir ==="; \
		$(MAKE) run TARGET=$$dir; \
	done

# Catch-all to prevent "Nothing to be done" for target arguments
%:
	@:
