# Calling Dekart tools: MCP or the `dekart` CLI

Two ways to call a tool. Decide once per task:

1. **MCP tools** listed in the session (`list_connections`, `run_query`, `create_report_snapshot`, ...): call them directly. No shell commands for Dekart, no `dekart init`.
2. **`dekart` CLI**: `dekart call --name <tool> --args '<json>' --json` for every tool. Four actions are commands of their own: `dekart run-query`, `dekart snapshot`, `dekart upload-file`, `dekart report-url`; `dekart preview` reads a downloaded result. `dekart tools` lists tools and schemas; `dekart <command> --help` gives current flags. Check availability once:

   ```bash
   for c in bq snow dekart; do command -v $c >/dev/null && echo $c=ok || echo $c=missing; done
   ```

Responses have the same shape both ways: a JSON object whose `result` holds the data, so every `result.` path in this skill applies to both.

## Running a query

`run_query` with `query_id` runs the prepared query, waits, and returns `job_id` and the result.

- MCP: the result is inline, `row_count`, `schema`, up to `limit` rows (default 50, at most 1000 rows or 1 MB, `truncated` when cut), no file. `schema_only` returns columns only. After about 45 s it may answer that the job is still running: call `check_job_status`, then `run_query` with `query_id` and that `job_id`, which reads the result without a new run. Any call without `job_id` is a new run, so never do that on the map-layer query once it ran. A DuckDB job cannot be re-read; set `limit` before running. DuckDB stops after 10 s unless `duckdb_timeout_seconds` (up to 120) is passed; simplify the SQL first.
- CLI: `dekart run-query --query-id <id> --out-dir <dir> --wait --json` downloads the result; read `result_file` from the JSON, never guess the extension. `dekart preview <result_file> --schema` or `--limit 20` to inspect it. `--wait` blocks and returns; never pipe through `| tail` or `| head`, never run as a background task, never write a poller.

Query parameters: `query_params_values` (MCP) or `--params-json` (CLI).

## Arguments with SQL or JSON documents

`query_text`, `map_config` and `widgets_config` are strings. A map or widgets document is its JSON serialized into that one string, never a nested object. MCP: build the document in your own reasoning and pass the string. CLI: write the arguments to a file with `json.dumps` and pass `--args-file <file>`; inline JSON breaks on quotes and newlines.

## Snapshots

`create_report_snapshot` with `report_id`; `zoom`, `lat`, `lon` change the view for that render only (pass `lat` and `lon` together); `include_widgets` adds charts; `height` when charts are cut off. MCP returns the PNG in the response; the CLI (`dekart snapshot`) saves it to the given file. Inspect the image; never use PNG URLs.

Timeout: MCP, retry once with `timeout_seconds` up to 120, then check the interactive report. CLI, ask the user to run `dekart snapshot-local install`, then retry.

## Uploading rows

`upload_file` with `file_id`, `name`, `mime_type`. MCP takes the rows inline (`content` or `content_base64`), capped at 2 MB and passing through your own output, so only small results (a few thousand rows) fit; for more, use query mode when Dekart has a connection for the warehouse, otherwise ask the user to upload with the CLI or say the map is a sample. CLI: `dekart upload-file --stdin` fed by a `bq` or `snow` CSV export, or `--file <path>`. Both return the completion payload; success is completion status `completed`.

## Report URL

`get_report_url` (MCP) or `dekart report-url --report-id <id> --json` (CLI). `report_url` fields of other tools may lack the host.

## Rejected map or widgets config

MCP shows only the HTTP status: call `get_map_config_schema` or `get_widgets_config_schema` and check the document against it and the reference examples. CLI names the error code; `--debug` adds `response_body.issues[]` with `path` and `actual`.

## Setup and auth

The user does setup; never run `dekart init` or `dekart config`, never install software, never create a connection (no tool exists).

- Nothing available: ask the user to connect the GeoSQL MCP Server (token from Dekart workspace settings) or run `pip install dekart && dekart init` (options: cloud.dekart.xyz, localhost via Docker, self-hosted; help them pick). Wait for `ready`, `done` or `ok`.
- CLI installed, not initialized: ask for `dekart init`.
- Token rejected (a tool answers "Create a new token in Dekart", or `create_report` / `create_dataset` return 404): MCP, the user creates a new token in Dekart workspace settings and pastes it into the extension; CLI, the user re-runs `dekart init`. Confirm, then retry.
- Connection missing: the user adds it in Dekart under Connections.
- Server too old (a tool or engine option missing): report it; the user updates the server. A CLI message `Update GeoSQL and the Dekart CLI: ...`: the user runs that command, retry once.
- Warehouse CLIs need a shell; MCP without a shell has no fallback.

Never call Dekart HTTP endpoints or read its config files.
