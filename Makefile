.PHONY: help shell-dekart-claude shell-bq-claude shell-no-warehouses _shell-claude-base

help:
	@echo "Targets:"
	@echo "  make shell-dekart-claude  # isolated shell: has claude+dekart, hides bq+snow"
	@echo "  make shell-bq-claude      # isolated shell: has claude+bq, hides dekart+snow"

shell-dekart-claude:
	@$(MAKE) _shell-claude-base INCLUDE_DEKART=1 INCLUDE_BQ=0 INCLUDE_SNOW=0

shell-bq-claude:
	@$(MAKE) _shell-claude-base INCLUDE_DEKART=0 INCLUDE_BQ=1 INCLUDE_SNOW=0

_shell-claude-base:
	@set -eu; \
	REAL_HOME="$$HOME"; \
	REAL_XDG_CONFIG_HOME="$${XDG_CONFIG_HOME:-$$HOME/.config}"; \
	CLAUDE_BIN="$$(command -v claude || true)"; \
	DEKART_BIN="$$(command -v dekart || true)"; \
	BQ_BIN="$$(command -v bq || true)"; \
	SNOW_BIN="$$(command -v snow || true)"; \
	GCLOUD_BIN="$$(command -v gcloud || true)"; \
	if [ -z "$$CLAUDE_BIN" ]; then \
		echo "Need 'claude' in PATH before running this target." >&2; \
		exit 1; \
	fi; \
	if [ "$${INCLUDE_DEKART}" = "1" ] && [ -z "$$DEKART_BIN" ]; then \
		echo "Need 'dekart' in PATH for this target." >&2; \
		exit 1; \
	fi; \
	if [ "$${INCLUDE_BQ}" = "1" ] && [ -z "$$BQ_BIN" ]; then \
		echo "Need 'bq' in PATH for this target." >&2; \
		exit 1; \
	fi; \
	if [ "$${INCLUDE_BQ}" = "1" ] && [ -z "$$GCLOUD_BIN" ]; then \
		echo "Need 'gcloud' in PATH for this target (required by bq auth)." >&2; \
		exit 1; \
	fi; \
	if [ "$${INCLUDE_SNOW}" = "1" ] && [ -z "$$SNOW_BIN" ]; then \
		echo "Need 'snow' in PATH for this target." >&2; \
		exit 1; \
	fi; \
	CFG_ROOT="$$(mktemp -d)"; \
	HOME_ROOT="$$(mktemp -d)"; \
	CACHE_ROOT="$$(mktemp -d)"; \
	STATE_ROOT="$$(mktemp -d)"; \
	BIN_DIR="$$(mktemp -d)"; \
	printf '%s\n' '#!/usr/bin/env bash' \
		'set -euo pipefail' \
		'export HOME="$${CLAUDE_LOGIN_HOME:-$$HOME}"' \
		'export XDG_CONFIG_HOME="$${CLAUDE_LOGIN_XDG_CONFIG_HOME:-$${XDG_CONFIG_HOME:-$$HOME/.config}}"' \
		'export PATH="$$HOME/.local/bin:$$PATH"' \
		'exec "__CLAUDE_BIN__" "$$@"' > "$$BIN_DIR/claude"; \
	sed -i.bak "s|__CLAUDE_BIN__|$$CLAUDE_BIN|g" "$$BIN_DIR/claude"; rm -f "$$BIN_DIR/claude.bak"; \
	chmod +x "$$BIN_DIR/claude"; \
	if [ "$${INCLUDE_DEKART}" = "1" ]; then ln -s "$$DEKART_BIN" "$$BIN_DIR/dekart"; fi; \
	if [ "$${INCLUDE_BQ}" = "1" ]; then ln -s "$$BQ_BIN" "$$BIN_DIR/bq"; fi; \
	if [ "$${INCLUDE_BQ}" = "1" ]; then ln -s "$$GCLOUD_BIN" "$$BIN_DIR/gcloud"; fi; \
	if [ "$${INCLUDE_SNOW}" = "1" ]; then ln -s "$$SNOW_BIN" "$$BIN_DIR/snow"; fi; \
	for b in bash sh env cat ls mkdir rm mktemp pwd echo sed awk grep; do \
		p="$$(command -v $$b || true)"; \
		if [ -n "$$p" ]; then ln -sf "$$p" "$$BIN_DIR/$$b"; fi; \
	done; \
	cleanup() { \
		rm -rf "$$CFG_ROOT" "$$HOME_ROOT" "$$CACHE_ROOT" "$$STATE_ROOT" "$$BIN_DIR"; \
	}; \
	trap cleanup EXIT INT TERM; \
	export XDG_CONFIG_HOME="$$CFG_ROOT"; \
	export HOME="$$HOME_ROOT"; \
	export XDG_CACHE_HOME="$$CACHE_ROOT"; \
	export XDG_STATE_HOME="$$STATE_ROOT"; \
	export CLAUDE_LOGIN_HOME="$$REAL_HOME"; \
	export CLAUDE_LOGIN_XDG_CONFIG_HOME="$$REAL_XDG_CONFIG_HOME"; \
	if [ -f "$$REAL_HOME/.claude.json" ]; then \
		cp "$$REAL_HOME/.claude.json" "$$HOME/.claude.json"; \
	fi; \
	mkdir -p "$$HOME/.claude"; \
	if [ -d "$$REAL_HOME/.claude" ]; then \
		for item in "$$REAL_HOME/.claude"/.[!.]* "$$REAL_HOME/.claude"/..?* "$$REAL_HOME/.claude"/*; do \
			[ -e "$$item" ] || continue; \
			name="$$(basename "$$item")"; \
			if [ "$$name" = "skills" ]; then \
				continue; \
			fi; \
			cp -R "$$item" "$$HOME/.claude/"; \
		done; \
	fi; \
	if [ -d "$$REAL_XDG_CONFIG_HOME/claude" ]; then \
		mkdir -p "$$XDG_CONFIG_HOME/claude"; \
		for item in "$$REAL_XDG_CONFIG_HOME/claude"/.[!.]* "$$REAL_XDG_CONFIG_HOME/claude"/..?* "$$REAL_XDG_CONFIG_HOME/claude"/*; do \
			[ -e "$$item" ] || continue; \
			name="$$(basename "$$item")"; \
			if [ "$$name" = "skills" ]; then \
				continue; \
			fi; \
			cp -R "$$item" "$$XDG_CONFIG_HOME/claude/"; \
		done; \
	fi; \
	export PATH="$$BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin"; \
	WORKDIR="$$(pwd)/tmp"; \
	mkdir -p "$$WORKDIR"; \
	cd "$$WORKDIR"; \
	echo "claude --dangerously-skip-permissions" > "$$HOME/.bash_history"; \
	echo "Isolated shell started."; \
	echo "PWD=$$(pwd)"; \
	echo "XDG_CONFIG_HOME=$$XDG_CONFIG_HOME"; \
	echo "HOME=$$HOME"; \
	echo "Claude config copied (skills excluded)."; \
	echo "PATH=$$PATH"; \
	echo "claude: $$(command -v claude)"; \
	echo "dekart: $$(command -v dekart || echo missing)"; \
	echo "bq: $$(command -v bq || echo missing)"; \
	echo "gcloud: $$(command -v gcloud || echo missing)"; \
	echo "snow: $$(command -v snow || echo missing)"; \
	exec bash --noprofile --norc -ic 'history -r; exec bash --noprofile --norc -i'

# Backward-compatible alias
shell-no-warehouses: shell-dekart-claude
