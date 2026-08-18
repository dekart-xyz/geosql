---
name: geosql
description: Build cost-safe Geospatial SQL for BigQuery, Snowflake, Wherobots and Postgres and/or render results on an interactive Dekart map.
user-invocable: true
---

# GeoSQL

## Tools/CLI

This skill uses the following CLIs:
- `dekart` for running BigQuery, Snowflake, Wherobots and Postgres SQLs and rendering maps
- `bq` to run BigQuery SQL when `dekart` BigQuery integration is not available.
- `snow` to run Snowflake SQL when `dekart` Snowflake integration is not available.
- Wherobots and Postgres have no local CLI fallback; they are dekart-only in this skill.

Before using CLIs, verify availability if it was not done before:

```bash
for c in bq snow dekart; do command -v $c >/dev/null && echo $c=ok || echo $c=missing; done
```

If no CLI is available, suggest installing the dekart CLI: `pip install dekart && dekart init`. `dekart init` is an interactive command that must be run by the user.

The user has 3 options in `dekart init`:
- cloud.dekart.xyz (Dekart-hosted control plane, easier setup)
- localhost (`docker run -p 8080:8080 dekartxyz/dekart`, more secure, requires Docker)
- self-hosted

Help the user pick the best installation option for their needs.

If `dekart` is available, check available connectors:

```bash
dekart call --name list_connections --args '{}' --json
```

If dekart available but not init, ask user to `dekart init`


## Dialect References

Use the matching reference for per-database SQL, CLI examples, and engine-specific caveats:

- BigQuery: `references/bigquery.md`
- Snowflake: `references/snowflake.md`
- Postgres / PostGIS: `references/postgres.md`
- Wherobots / Sedona: `references/wherobots.md`

## Required Workflow

Follow these steps in order. Do NOT write a final query until steps 1-3 are complete.
Combine each step with examples in matching dialect reference.

### Step 1: Discover schema

Discover available data objects before writing any query: start with database/share availability (where applicable), then confirm schemas, tables, and columns. Always verify exact object names and column types from the warehouse metadata; do not assume from general knowledge.

When multiple tables match the entity, sample each candidate for attribute density and prefer the richer source. Richer attributes enable stronger visual encoding in Step 5 and a stronger map validation case.

### Step 2: Resolve the target area

When the user asks about a named area (city, district, country), query `division_area` first to discover how it is actually stored (subtype, class, naming conventions). Do not assume from general knowledge.

Use the dialect reference for target-area SQL and fallbacks. Extract the exact bbox constants from the result. Use the full precision values returned by the query, do not round or truncate them.

### Step 3: Draft the query

- Use hardcoded bbox from step 2 as a scan gate (fast partition pruning).
- Add `ST_INTERSECTS` against the real geometry from `division_area` for geographic correctness. bbox alone is rectangular and overshoots.
- Both are required for named-area queries. Never omit `ST_INTERSECTS`.
- Select only required columns; avoid `SELECT *`.
- Add `LIMIT` for exploration.

**bbox overlap filter direction.** The scan gate must use the OVERLAP pattern, not containment. The feature's bbox must overlap the target area:

```
-- CORRECT (overlap): feature extends into our area
AND bbox.xmax >= <area_xmin>   -- feature's right edge is east of area's left
AND bbox.xmin <= <area_xmax>   -- feature's left edge is west of area's right
AND bbox.ymax >= <area_ymin>   -- feature's top edge is above area's bottom
AND bbox.ymin <= <area_ymax>   -- feature's bottom edge is below area's top

-- WRONG (containment): do NOT use this
AND bbox.xmin >= <area_xmin>   -- WRONG
AND bbox.xmax <= <area_xmax>   -- WRONG
```

Use the dialect reference for draft query examples and engine-specific syntax. For map output, select a geometry column aliased exactly as lowercase `geometry`.

**cast 64-bit integer fields to 32-bit int or double.** Any numeric column bound to a Kepler visual channel (color, stroke width, size, height) must NOT be a 64-bit integer.

### Step 4: Validate (mandatory)

Do NOT present the query to the user without validating it first.

1. Cost / safety gate.
   * BigQuery: dry run to check estimated bytes. If using `dekart`, the mandatory `dekart call --name update_query` prepare step is also the dry-run gate; read `dry_run.valid` and `dry_run.estimated_bytes_processed` from that response before running `dekart run-query`.
     If using `bq` CLI, run the query with `bq query --use_legacy_sql=false --dry_run --format=json '<SQL>'` and parse the JSON output for `totalBytesProcessed`.
   * If dry run fails: read the bq error output. Common causes: string vs int type mismatch, missing backtick escaping, reserved keyword collision.
   * If estimated bytes exceed budget: do NOT execute. Instead, rewrite the query to be cheaper (tighter bbox, more filters, lower H3 resolution, etc) and validate again.
2. Validate row count: execute `COUNT(*)` (or equivalent) to confirm count is reasonable. If count is zero, debug before presenting.
3. Validate geometry magnitude when possible:
   - If output includes polygonal `GEOGRAPHY`, compute total area (for example `SUM(ST_AREA(geometry))`) and return units in square meters (and optionally km²).
   - If output includes line `GEOGRAPHY`, compute total length (for example `SUM(ST_LENGTH(geometry))`) and return units in meters (and optionally km).
   - If output includes `geometry`, measurements are CRS units. For EPSG:4326 geometry, do not report meters; transform/cast first or label the result as CRS units.
   - If geometry is point-only or no geometry is selected, explicitly state area/length validation is not applicable.
4. Sanity-check whether row count and area/length are reasonable for the place and feature type (use domain knowledge). If numbers look implausible, debug before presenting.
5. If validation fails debug before presenting. Check bbox direction, value truncation, filter logic, and column types.


Iterate. Fix issues in small steps. Do not run broad or full extraction queries unless explicitly requested. All validation must be done in SQL.


### Step 5: Map Data

Maps catch what rows cannot: misplaced points, duplicates, coverage gaps.

If user has `dekart` with configured warehouse connection, create and validate map by default.

If `dekart` is not installed, init or has no connectors but `bq` or `snow` CLIs available, then answer first (SQL + results + cost), then propose creating a map as "Next step" section with 2-3 explaining map benefits for this specific question.

Do not claim visual insights until the styled snapshot is rendered and inspected; never dress row-derived facts as map observations.

Make sure maps are beautifully styled and communicate a clear insight. Always add a map title, dataset name, and layer names, and optionally include a README when the user asks for insight.

If dekart CLI is missing, ask the user to `pip install dekart && dekart init` and wait until the user confirms with `ready`, `done`, or `ok`. If unauthed, ask to run `dekart init`.


## Running Queries with `bq` CLI

Use `bq` CLI directly. Always use standard SQL and enforce a budget. Full command examples and guardrails: `references/bigquery.md`.

## Running Queries with `snow` CLI

Use `snow sql` directly for Snowflake data and keep queries bounded. Full command examples and guardrails: `references/snowflake.md`.


## Map Flow with `dekart` CLI

Use this when dekart CLI is available.

- If dekart has no warehouse connectors configured, use it to upload CSV results from `bq` or `snow` and create a map that way.
- Otherwise use Dekart connectors to run queries.

### Artifact model

The CLI stores map artifacts in this hierarchy:
- `report`: top-level map container.
- `dataset`: one data layer slot inside a report, may contain a SQL query or uploaded file.
- `file`: uploaded data artifact attached to a dataset.
- `query`: SQL attached to a dataset/connection and executed asynchronously.
- `job`: execution instance for a query (`dekart run-query` handles run -> wait -> fetch after the query has already been prepared).

Important IDs:
- `create_report` returns the canonical `report_id` at `result.report.id`, `result.report_id`, or `result.id`
- `create_dataset` returns the dataset id at `result.id`.
- `dekart run-query --json` returns `dataset_id`, `query_id`, `job_id`, terminal status, and `result_file`.
- `report_url` fields returned directly by MCP tools may miss host name; resolve the user-facing URL with `dekart report-url --report-id <report_id> --json`.
- In Kepler `map_config`, every layer `config.dataId`, filter `dataId`, and tooltip key must use the report `dataset_id`, not `query_id`, `file_id`, source table name, or dataset label.

For real SQL, inline JSON is fragile because SQL often contains quotes and newlines. Save SQL to a file, then pass it to `update_query` through an args JSON file before running `dekart run-query`. The args file must be a JSON object with the prepared query id and SQL text, for example:

```json
{
  "query_id": "<query_id>",
  "query_text": "<full SQL text>"
}
```

Control plane depends on execution mode:
- Query mode (connectors available): create `report` and dataset, create/update the query explicitly, then run `dekart run-query` for run -> wait -> fetch rows.
- File-upload mode (no connectors): create `report` -> create `dataset` -> create `file`, then upload CSV and complete multipart flow.

### Mode selection (required)

Choose exactly one flow after gate/confirmation:

1. Query mode:
   - Use when `list_connections` shows at least one usable warehouse connector.
   - Execution path: create one report + datasets with `dekart call`, prepare each dataset query with `create_dataset`, `create_query` + `update_query`, then run `dekart run-query --query-id <query_id> --out-dir <dir> --wait --json`.
2. File-upload mode:
   - Use when no usable connector is available.
   - Execution path: `report -> dataset -> file -> upload-file`.

Do not run both flows for the same task unless user explicitly asks.

### File-upload mode (no connectors)

1. Use CLI help for current command behavior: `dekart --help`, `dekart tools --help`, `dekart call --help`, `dekart upload-file --help`.
2. Gate: enter this flow ONLY after the analytical answer is delivered AND the user confirms the map step with `ready`, `done`, or `ok`. If user declines or is silent, stop; do not export CSV, do not create reports.
3. Once gated-in, export result rows to CSV with explicit row controls. `--max_rows` is mandatory because BigQuery CLI defaults to 100 rows when omitted.
   - CSV export must keep stderr separate from CSV bytes.
   - Never use `2>&1` when output is redirected to `.csv`.
   - BigQuery:
     `bq query ... --format=csv --max_rows=50000 'SELECT ...' | dekart upload-file --stdin --file-id <file_id> --name result.csv --mime-type text/csv`
   - Snowflake:
     `snow sql --format CSV --silent --query "<SQL with LIMIT 50000>" | dekart upload-file --stdin --file-id <file_id> --name result.csv --mime-type text/csv`
4. Discover MCP tools and schemas from `dekart tools`.
5. Resolve required tool names from schema, not hardcoded names:
   - report creation tool: creates a report container
   - dataset creation tool: requires `report_id` and returns the dataset id as `result.id`
   - file creation tool: requires `dataset_id`
6. Execute control plane in this exact order: report -> dataset -> file.
7. Upload CSV with `dekart upload-file` and use returned `complete` payload/status.
   - BigQuery:
     `bq query ... --format=csv --max_rows=50000 'SELECT ...' | dekart upload-file --stdin --file-id <file_id> --name result.csv --mime-type text/csv`
   - Snowflake:
     `snow sql --format CSV --silent --query "<SQL with LIMIT 50000>" | dekart upload-file --stdin --file-id <file_id> --name result.csv --mime-type text/csv`
   - File-based fallback:
     `dekart upload-file --file /tmp/result.csv --file-id <file_id>`
8. Treat upload as successful only when completion status is `completed`.
9. Validate map output with snapshot after successful upload:
   - run CLI snapshot command for the target report:
     `dekart snapshot --report-id <report_id> --out /tmp/<report_id>-snapshot.png`
   - inspect the saved local PNG output from that command; do not use direct PNG URLs/links
   - verify snapshot render reflects expected area/content before finalizing
10. Return resulting IDs, absolute `report_url`, and image (when available) in final response.


### Query mode (connectors available)

1. Use CLI help for current command behavior: `dekart --help`, `dekart run-query --help`, `dekart snapshot --help`.
2. Gate: use this flow by default when Dekart is installed and `list_connections` shows at least one usable connector; do not use this flow when Dekart is missing or no usable connector exists.
3. Once gated-in, confirm available connections:
   - `dekart call --name list_connections --args '{}' --json`
   - pick a usable connection for the target warehouse/entity.
4. Resolve required tool names from schema, not hardcoded names:
   - report creation tool: creates a report container
   - dataset creation tool: requires `report_id` and returns the dataset id as `result.id`
   - query creation tool: requires `dataset_id`
5. Execute control plane in this exact order: report -> dataset -> query -> run query.
   - `dekart call --name create_report --args '{}' --json` -> capture `report_id` from `result.report.id`, `result.report_id`, or `result.id`.
   - `dekart call --name create_dataset --args '{"report_id":"<report_id>"}' --json` -> capture `dataset_id` from `result.id`, `result.dataset_id`, or `result.dataset.id`. Note that datasets are single slot, re-running query owerwrites prevoise data.
  – Save SQL to a file. SQL must include geospatial output aliased exactly as lowercase `"geometry"` for the final map query.
6. Run all discovery, validation, preview, and assertion queries:
   - Create or reuse one scratch query:
     `dekart call --name create_query --args '{"dataset_id":"<scratch_dataset_id>","connection_id":"<id>"}' --json`
   - Prepare it with the SQL file through `update_query`; for BigQuery, this response is the dry-run cost gate:
     `dekart call --name update_query --args-file /tmp/update-query-args.json --json`
     The args file must contain `{"query_id":"<scratch_query_id>","query_text":"<full SQL text>"}`.
   - Only after `dry_run.valid` is true and cost is acceptable, execute and fetch:
     `dekart run-query --query-id <scratch_query_id> --out-dir <dir> --wait --json`
   - Read `result_file` from the JSON response; do not guess `.csv` or `.parquet`.
   - Preview rows with `dekart preview <result_file> --limit 20`; inspect columns/types with `dekart preview <result_file> --schema`.
   - `run-query --json` returns `dataset_id`, `query_id`, `job_id`, terminal status, and `result_file`.
   - Treat a zero exit plus a non-empty `result_file` as successful fetch.
   - If the command reports `empty result (metadata/SHOW statement?)`, rewrite discovery SQL to return rows.
   - Do not hand-roll a poller or use temporary scripts for run/wait/fetch.
   - If you need diagnostic job status from `dekart call`, the canonical tool payload status path is `result.query_job.job_status`.
7. Run the final map query against its **dedicated map-layer dataset**:
   - Create the map-layer query:
     `dekart call --name create_query --args '{"dataset_id":"<map_layer_dataset_id>","connection_id":"<id>"}' --json`
   - Prepare it with `update_query` from the final SQL file and apply the BigQuery dry-run gate when applicable.
     The args file must contain `{"query_id":"<map_layer_query_id>","query_text":"<full SQL text>"}`.
   - Execute and fetch:
     `dekart run-query --query-id <map_layer_query_id> --out-dir <dir> --wait --json`
   - One dedicated dataset per layer. Create a new report only when the user explicitly asks for more than one map/report.
   - The map-layer query is write-once: after it runs, never `update_query` or `run-query` it again. Run any later validation (area, length, counts, previews) on the scratch query from step 6 — re-running the map-layer query overwrites the layer with the new result and blanks the map.
8. Validate map output with snapshot after successful job completion and row fetch:
   - run: `dekart snapshot --report-id <report_id> --out /tmp/<report_id>-snapshot.png`
   - if the snapshot is too zoomed out, centered poorly, or the user asks to zoom/pan, rerun with transient viewport params instead of editing saved map state: `dekart snapshot --report-id <report_id> --out /tmp/<report_id>-snapshot.png --zoom <zoom> --lat <latitude> --lon <longitude>`; derive lat/lon from target area or bbox center, use `--lat` and `--lon` together, and preserve the same params on retry
   - inspect saved local PNG output; do not use direct PNG URLs/links
   - verify snapshot reflects expected area/content before finalizing
9. Return resulting IDs, absolute `report_url`, and image (when available) in final response:
   - `report_id`, `dataset_id`, `query_id`, `job_id`, terminal status, and `report_url`.

### Failure handling
* Do not run `dekart init`, `dekart config` on your own. Ask user to re-run `dekart init` if needed.
* If create-report or create-dataset returns 404 it likely issue with token or auth. Ask user to re-run `dekart init` and confirm before retrying.
* Snapshot validation is mandatory, but diagnose in order: first verify map config bindings, columns, and view; if those are correct and the PNG is blank or missing WebGL features, treat it as a snapshot renderer issue and verify the interactive report.
* anti-loop rules for Dekart connector run/fetch commands:
   - Never pipe long-running `dekart` commands through `| tail` or `| head`; those buffers can hide progress until EOF and look idle.
   - Do not run Dekart connector run/fetch commands as background tasks watched by Monitor on a tailed file.
   - Prefer `dekart run-query --wait`, which blocks and returns directly.
* If remote snapshot fails with timeout (for example HTTP 504 / `snapshot timeout`), ask the user to enable local snapshots:
  `dekart snapshot-local install`
  Then retry snapshot with `dekart snapshot --report-id <report_id>`.
* Datasets auto-style by default. Kepler would apply a default styling if no config is provided for dataset provided.
* If snapshot shows only basemap (no features), debug binding first:
  - confirm `layer.config.dataId` points to the report dataset id
  - confirm tooltip `fieldsToShow` keys and filter `dataId` values also use the report dataset id
  - confirm bound column names match exported dataset headers exactly (case-sensitive). Note: snowflake export columns names are uppercase by default.
  – conform dataset data is not owerwrite by a later query.
* Never present `report_path` as a Map URL or user-facing link or manually user facing report URL.
* Resolve the final Map URL with `dekart report-url --report-id <report_id> --json`; do not treat MCP `report_url` or `report_path` fields as canonical.
* Never call create-report multiple times just to get URL fields.
* Never call Dekart HTTP, config files, or anything outside the documented dekart CLI.



## Styling the Map

After upload, review the map snapshot and tune the layer. These rules override Claude's default styling instincts. Full reference: `references/map-styling.md`.

Non-obvious rules:

1. Pick the layer for the question, not the data shape. Point for positions, H3/hexbin for normalized density, Arc for OD pairs, Line for paths, 3D Polygon for vertical magnitude.
2. Prefer high density. Points radius `0.5-4` px, lines stroke `0.5-1.5` px, polygon borders `0.5-1` px hairline. Do not clamp `LIMIT` below 50k unless cost forces it.
3. Do not show the same thing twice. A tuned Point layer already shows density, so skip the Heatmap on top. Skip outline-color when fill encodes the same value.
4. Encode with multiple channels. Color for the primary variable, radius or stroke width for magnitude, height for a second numerical dimension. Opacity is for overlap, not data.
5. Palette by data type. Sequential (Viridis, Sunset) for magnitude, Diverging (RdBu) for signed / midpoint data, Qualitative (Set2, Tableau10) for up to 8 categories. Never rainbow / jet.
6. Match basemap to density. Dark basemap for point clouds and flows, light basemap for choropleths and print.
7. Layer order bottom-up: basemap, polygon fills, lines, points, labels. Selected features always on top.
8. Lock the initial view to the zoom where the insight is visible. Do not save a world-view for a city-scale insight.

When uncertain about a specific pixel value or palette, read `references/map-styling.md`.

## H3 Aggregation

Use H3 when the user requests spatial aggregation, heatmaps, density, or cell-based rollups.

Confirm the function exists before using it. Use the dialect reference for engine-specific H3 functions.

Cost rules:
1. Apply `WHERE` + hardcoded bbox first, then compute H3.
2. Return `h3` + aggregate metrics before adding boundaries.
3. Use `COUNT(*)` previews before geometry-heavy `ST_H3_BOUNDARY` output.
4. Default resolution `7`-`9` for city scale.
5. If over budget, lower resolution or narrow filters before retrying.

## Failure Handling

- `bq query` unavailable or auth fails: return exact fix commands only, no auto-install.
- `snow sql` unavailable or auth fails: ask user to install/configure `snow`, then retry using `snow sql`.
- Snowflake Overture shares missing (`SHOW DATABASES LIKE 'OVERTURE_MAPS__%'` returns no rows): ask user to install Overture data from Snowflake Marketplace, then continue.
- Postgres: no local CLI fallback. If the dekart Postgres connector is missing or auth fails, ask the user to configure it via `dekart init`; do not attempt a CLI workaround.
- PostGIS not enabled (`geometry_columns` errors): ask the user to run `CREATE EXTENSION postgis;`, then continue.
- Wherobots: no local CLI fallback. If the dekart Wherobots connector is missing or auth fails, ask the user to configure it via `dekart init`; do not attempt a CLI workaround.
- Over budget: do not execute, return cheaper variant.
- Invalid query: return corrected SQL and rerun validation (`update_query` dry-run for BigQuery, `COUNT(*)`/bounded preview for Snowflake, tightly bounded `COUNT(*)`/preview execution through Dekart connector mode for Wherobots).
- Never install software automatically. Report prerequisite commands for the user to run.
