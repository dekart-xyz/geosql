.PHONY: help shell-dekart-claude shell-dekart-copilot shell-bq-claude shell-docker-claude shell-no-warehouses _shell-agent-base

GEOSQL_DIND_IMAGE ?= geosql-dind-claude:local

help:
	@echo "Targets:"
	@echo "  make shell-dekart-claude  # isolated shell: has claude+dekart, hides bq+snow"
	@echo "  make shell-dekart-copilot # isolated shell: has copilot+dekart, hides bq+snow"
	@echo "  make shell-bq-claude      # isolated shell: has claude+bq, hides dekart+snow"
	@echo "  make shell-docker-claude  # privileged disposable DinD shell (trusted code only), port 8080"

shell-dekart-claude:
	@$(MAKE) _shell-agent-base AGENT=claude INCLUDE_DEKART=1 INCLUDE_BQ=0 INCLUDE_SNOW=0

shell-dekart-copilot:
	@$(MAKE) _shell-agent-base AGENT=copilot INCLUDE_DEKART=1 INCLUDE_BQ=0 INCLUDE_SNOW=0

shell-bq-claude:
	@$(MAKE) _shell-agent-base AGENT=claude INCLUDE_DEKART=0 INCLUDE_BQ=1 INCLUDE_SNOW=0

shell-docker-claude:
	@set -eu; \
	command -v docker >/dev/null 2>&1 || { echo "Need 'docker' in PATH." >&2; exit 1; }; \
	docker info >/dev/null 2>&1 || { echo "Docker is not running." >&2; exit 1; }; \
	docker buildx version >/dev/null 2>&1 || { echo "Need Docker Buildx for this target." >&2; exit 1; }; \
	echo "Building disposable GeoSQL test image $(GEOSQL_DIND_IMAGE)..."; \
	docker buildx build --load --progress=plain --file Dockerfile.test-shell --tag "$(GEOSQL_DIND_IMAGE)" .; \
	echo "WARNING: --privileged is not a security boundary; run trusted code only."; \
	echo "Starting Docker-in-Docker; only the mounted repository persists after exit."; \
	docker run --rm -it \
		--privileged \
		--publish 127.0.0.1:8080:8080 \
		--env ANTHROPIC_API_KEY \
		--env CLAUDE_CODE_OAUTH_TOKEN \
		--env GEOSQL_HOST_UID="$$(id -u)" \
		--env GEOSQL_HOST_GID="$$(id -g)" \
		--mount type=bind,source="$(CURDIR)",target=/workspace \
		--workdir /workspace \
		"$(GEOSQL_DIND_IMAGE)" \
		bash -lc 'set -eu; \
			export PATH="/opt/venv/bin:$$PATH"; \
			dockerd > /tmp/dockerd.log 2>&1 & \
			for attempt in $$(seq 1 60); do \
				docker info >/dev/null 2>&1 && break; \
				sleep 0.5; \
			done; \
			docker info >/dev/null 2>&1 || { cat /tmp/dockerd.log >&2; exit 1; }; \
			HOST_UID="$${GEOSQL_HOST_UID:-0}"; \
			HOST_GID="$${GEOSQL_HOST_GID:-0}"; \
			GROUP_NAME="$$(getent group "$$HOST_GID" | cut -d: -f1 || true)"; \
			if [ -z "$$GROUP_NAME" ]; then groupadd --gid "$$HOST_GID" geosql-test; GROUP_NAME=geosql-test; fi; \
			USER_NAME="$$(getent passwd "$$HOST_UID" | cut -d: -f1 || true)"; \
			if [ -z "$$USER_NAME" ]; then useradd --create-home --uid "$$HOST_UID" --gid "$$GROUP_NAME" geosql-test; USER_NAME=geosql-test; fi; \
			USER_HOME="$$(getent passwd "$$USER_NAME" | cut -d: -f6)"; \
			usermod --gid "$$GROUP_NAME" "$$USER_NAME"; \
			usermod --append --groups docker "$$USER_NAME"; \
			chown -R "$$HOST_UID:$$HOST_GID" /opt/venv "$$USER_HOME"; \
			echo; \
			echo "Disposable GeoSQL shell ready."; \
			echo "  Source: /workspace (mounted read/write)"; \
			echo "  User: $$USER_NAME ($$HOST_UID:$$HOST_GID)"; \
			echo "  Python: $$(python --version)"; \
			echo "  Claude: $$(claude --version)"; \
			echo "  Docker: $$(docker version --format {{.Client.Version}}/{{.Server.Version}})"; \
			echo "  Host port 8080 forwards to this container."; \
			echo; \
			echo "Try:"; \
			echo "  python -m pip install -e ."; \
			echo "  claude  # run /login unless an auth environment variable was inherited"; \
			echo "  docker run --rm -d --name dekart -p 8080:8080 dekartxyz/dekart"; \
			echo; \
			exec gosu "$$USER_NAME" env HOME="$$USER_HOME" PATH="/opt/venv/bin:$$PATH" bash --rcfile /etc/geosql-test-shell.bashrc'

_shell-agent-base:
	@set -eu; \
	REAL_HOME="$$HOME"; \
	REAL_XDG_CONFIG_HOME="$${XDG_CONFIG_HOME:-$$HOME/.config}"; \
	AGENT="$${AGENT:-claude}"; \
	AGENT_BIN="$$(command -v "$$AGENT" || true)"; \
	DEKART_BIN="$$(command -v dekart || true)"; \
	BQ_BIN="$$(command -v bq || true)"; \
	SNOW_BIN="$$(command -v snow || true)"; \
	GCLOUD_BIN="$$(command -v gcloud || true)"; \
	if [ -z "$$AGENT_BIN" ]; then \
		echo "Need '$$AGENT' in PATH before running this target." >&2; \
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
		'export HOME="$${AGENT_LOGIN_HOME:-$$HOME}"' \
		'export XDG_CONFIG_HOME="$${AGENT_LOGIN_XDG_CONFIG_HOME:-$${XDG_CONFIG_HOME:-$$HOME/.config}}"' \
		'export PATH="$$HOME/.local/bin:$$PATH"' \
		'exec "__AGENT_BIN__" "$$@"' > "$$BIN_DIR/$$AGENT"; \
	sed -i.bak "s|__AGENT_BIN__|$$AGENT_BIN|g" "$$BIN_DIR/$$AGENT"; rm -f "$$BIN_DIR/$$AGENT.bak"; \
	chmod +x "$$BIN_DIR/$$AGENT"; \
	if [ "$${INCLUDE_DEKART}" = "1" ]; then ln -s "$$DEKART_BIN" "$$BIN_DIR/dekart"; fi; \
	if [ "$${INCLUDE_BQ}" = "1" ]; then ln -s "$$BQ_BIN" "$$BIN_DIR/bq"; fi; \
	if [ "$${INCLUDE_BQ}" = "1" ]; then ln -s "$$GCLOUD_BIN" "$$BIN_DIR/gcloud"; fi; \
	if [ "$${INCLUDE_SNOW}" = "1" ]; then ln -s "$$SNOW_BIN" "$$BIN_DIR/snow"; fi; \
	for b in bash sh env cat ls mkdir rm mktemp pwd echo sed awk grep python3 python; do \
		p="$$(command -v $$b || true)"; \
		if [ -n "$$p" ]; then ln -sf "$$p" "$$BIN_DIR/$$b"; fi; \
	done; \
	if [ ! -e "$$BIN_DIR/python" ] && [ -e "$$BIN_DIR/python3" ]; then \
		ln -sf "$$BIN_DIR/python3" "$$BIN_DIR/python"; \
	fi; \
	cleanup() { \
		rm -rf "$$CFG_ROOT" "$$HOME_ROOT" "$$CACHE_ROOT" "$$STATE_ROOT" "$$BIN_DIR"; \
	}; \
	trap cleanup EXIT INT TERM; \
	export XDG_CONFIG_HOME="$$CFG_ROOT"; \
	export HOME="$$HOME_ROOT"; \
	export XDG_CACHE_HOME="$$CACHE_ROOT"; \
	export XDG_STATE_HOME="$$STATE_ROOT"; \
	export AGENT_LOGIN_HOME="$$REAL_HOME"; \
	export AGENT_LOGIN_XDG_CONFIG_HOME="$$REAL_XDG_CONFIG_HOME"; \
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
	mkdir -p "$$HOME/.copilot"; \
	if [ -d "$$REAL_HOME/.copilot" ]; then \
		for item in "$$REAL_HOME/.copilot"/.[!.]* "$$REAL_HOME/.copilot"/..?* "$$REAL_HOME/.copilot"/*; do \
			[ -e "$$item" ] || continue; \
			name="$$(basename "$$item")"; \
			if [ "$$name" = "skills" ]; then \
				continue; \
			fi; \
			cp -R "$$item" "$$HOME/.copilot/"; \
		done; \
	fi; \
	if [ -d "$$REAL_XDG_CONFIG_HOME/copilot" ]; then \
		mkdir -p "$$XDG_CONFIG_HOME/copilot"; \
		for item in "$$REAL_XDG_CONFIG_HOME/copilot"/.[!.]* "$$REAL_XDG_CONFIG_HOME/copilot"/..?* "$$REAL_XDG_CONFIG_HOME/copilot"/*; do \
			[ -e "$$item" ] || continue; \
			name="$$(basename "$$item")"; \
			if [ "$$name" = "skills" ]; then \
				continue; \
			fi; \
			cp -R "$$item" "$$XDG_CONFIG_HOME/copilot/"; \
		done; \
	fi; \
	export PATH="$$BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin"; \
	WORKDIR="$$(pwd)/tmp"; \
	mkdir -p "$$WORKDIR"; \
	cd "$$WORKDIR"; \
	if [ "$$AGENT" = "claude" ]; then \
		echo "claude --dangerously-skip-permissions" > "$$HOME/.bash_history"; \
	elif [ "$$AGENT" = "copilot" ]; then \
		echo "copilot --yolo" > "$$HOME/.bash_history"; \
	else \
		echo "$$AGENT" > "$$HOME/.bash_history"; \
	fi; \
	echo "Isolated shell started."; \
	echo "PWD=$$(pwd)"; \
	echo "XDG_CONFIG_HOME=$$XDG_CONFIG_HOME"; \
	echo "HOME=$$HOME"; \
	echo "$$AGENT config copied (skills excluded)."; \
	echo "PATH=$$PATH"; \
	echo "$$AGENT: $$(command -v "$$AGENT")"; \
	echo "dekart: $$(command -v dekart || echo missing)"; \
	echo "bq: $$(command -v bq || echo missing)"; \
	echo "gcloud: $$(command -v gcloud || echo missing)"; \
	echo "snow: $$(command -v snow || echo missing)"; \
	exec bash --noprofile --norc -ic 'history -r; exec bash --noprofile --norc -i'

# Backward-compatible alias
shell-no-warehouses: shell-dekart-claude
