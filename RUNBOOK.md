# Build Runbook

This runbook explains how to build all GeoSQL deliverables from source.

## Prerequisites

- Python 3.8+
- `pip`

## 1) Build Python package (wheel + sdist)

From repo root:

```bash
pip install build
python3 -m build
```

Artifacts:

- `dist/geosql-<version>-py3-none-any.whl`
- `dist/geosql-<version>.tar.gz`

## 2) Build Skills CLI package (`geosql.skill`)

From repo root:

```bash
python3 scripts/build_skill_package.py
```

Artifact:

- `geosql.skill`

The package is generated from canonical sources only:

- `geosql/SKILL.md`
- `geosql/references/*`

## 3) Smoke test local CLI

```bash
pip install -e .
python3 -m geosql --help
geosql --help
```

## 4) Smoke test installer paths

Explicit installs:

```bash
geosql install claude
geosql install codex
geosql install copilot
geosql install opencode
geosql install vibe
geosql install all
```

Expected paths:

- `~/.claude/skills/geosql/SKILL.md`
- `~/.codex/skills/geosql/SKILL.md`
- `~/.copilot/skills/geosql/SKILL.md`
- `~/.config/opencode/skills/geosql/SKILL.md`
- `${VIBE_HOME:-~/.vibe}/skills/geosql/SKILL.md`

After each successful command, verify the optional Dekart step matches the current state:

- No `dekart` on `PATH`: the short arrow-key menu explains the map-in-the-loop benefit, defaults to the recommended install option, and shows the exact pip and init commands before consent.
- `dekart` installed but `dekart tools --json` is not ready: GeoSQL skips pip and offers only `dekart init`.
- `dekart` installed inside an isolated GeoSQL environment: GeoSQL skips pip and, with consent, exposes a launcher beside the reachable `geosql` command before init.
- `dekart tools --json` succeeds: GeoSQL reports both tools ready without prompting.
- Non-interactive input/output: GeoSQL never runs pip or init and prints repeatable setup commands.
- `geosql install all`: the Dekart check and optional prompt appear once, after all skill copies succeed.

The Cloud setup path selected by `dekart init` does not require Docker. Declining or cancelling the optional step must return success because the GeoSQL skill is already installed.

Run the installer regression tests:

```bash
python3 -m unittest tests.test_cli -v
```

### Disposable Docker-in-Docker shell

For a clean interactive machine with Python, Claude Code, a nested Docker daemon, the repository mounted at `/workspace`, and host port 8080 forwarded:

```bash
make shell-docker-claude
```

The target uses a privileged Docker-in-Docker container so nested containers and their data disappear when the shell exits. **Disposable describes data cleanup, not security isolation:** `--privileged` can compromise a native Linux Docker host, and inherited Claude credentials are available to processes in the container. Run this target only with trusted repository code, or run Docker itself inside a disposable VM when you need a real host boundary.

The local repository is the only read/write mount, so source changes persist. The interactive shell matches the invoking host UID/GID to avoid root-owned checkout files on Linux. The outer host publish for port 8080 is loopback-only. The nested `-p 8080:8080` listener is still reachable from trusted peer containers on the local Docker bridge, so do not use it for untrusted services. The local test image and Docker build cache remain after exit, but container state, Claude login created inside it, nested images, and nested containers are removed. The target inherits `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` when either is exported; otherwise run `/login` inside Claude. macOS Keychain login cannot be mounted into the Linux container.

Inside the shell:

```bash
python -m pip install -e .
geosql install claude
docker run --rm -d --name dekart -p 8080:8080 dekartxyz/dekart
claude
```

If host port 8080 is already occupied, Docker refuses to start the disposable shell without leaving a container behind.

## 5) Verify repository contains no legacy naming

```bash
rg -n "giskill|gis-skill" .
```

Expected result: no matches.

## 6) Configure pre-push release hook (main branch)

Install hooks path:

```bash
./scripts/install_hooks.sh
```

The `pre-push` hook runs only on `main` and performs:

1. Run syntax checks, the full unit/E2E test suite, the CLI smoke check, and the skill-package build.
2. Rebuild `geosql.skill` and commit if changed.
3. Bump minor version in `pyproject.toml` and commit (separate commit).
4. Build package and publish to PyPI.
5. Exit with non-zero so you run `git push` again and include the new commits.

Optional environment variable:

```bash
export PYPI_API_TOKEN='pypi-...'
```

If `PYPI_API_TOKEN` is not set, hook falls back to your local Twine auth
(`~/.pypirc`, keyring, or interactive prompt).

Recommended push flow on `main`:

```bash
git push         # hook runs, creates commits, publishes, exits non-zero intentionally
git push         # push new local commits
```

## 7) Run Claude in isolated Dekart shell (no `bq`/`snow`)

From repo root:

```bash
make shell-dekart-claude
claude --dangerously-skip-permissions
```

Inside Claude:

1. If prompted with `Not logged in`, run `/login` first.
2. Select model via `/model` (pick `Opus 4.7` from available models).

Do not hardcode model id in this flow because model names/availability can vary by account and release.

If your local Claude build uses different bypass flag names, check:

```bash
claude --help | rg -i "model|permission|bypass|danger"
```

Then run the equivalent bypass-permissions flag supported by your version.

Use bypass mode only in trusted local repositories.

Run one Dekart eval case non-interactively from the isolated shell:

```bash
python3 evals/run.py \
  --case london-boroughs-dekart-bigquery \
  --model opus \
  --thinking-level medium
```

## 8) Run GitHub Copilot in isolated Dekart shell (no `bq`/`snow`)

From repo root:

```bash
make shell-dekart-copilot
```

Inside the shell:

```bash
command -v copilot
command -v dekart
command -v bq || true
command -v snow || true
python -m geosql install copilot
test -f ~/.copilot/skills/geosql/SKILL.md
test -f ~/.copilot/skills/geosql/references/map-styling.md
```

Then start Copilot and verify it recognizes the GeoSQL skill with a prompt like:

```text
/geosql Show EV charger density along major roads and render a map
```
