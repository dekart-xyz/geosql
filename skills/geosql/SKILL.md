---
name: geosql
description: Build cost-safe geospatial SQL for BigQuery, DuckDB, Snowflake, Wherobots, and Postgres and/or render results on an interactive Dekart map.
user-invocable: true
---

# GeoSQL

## Tools

Dekart runs BigQuery, DuckDB, Snowflake, Wherobots and Postgres SQL and renders maps. This skill names its tools (`list_connections`, `create_report`, `update_query`, `run_query`, `create_report_snapshot`, ...). Two ways to call them; decide once per task:

1. Dekart MCP tools in this session (GeoSQL MCP Server): call them directly, no shell commands for Dekart.
2. Otherwise the `dekart` CLI: `dekart call --name <tool> --args '<json>' --json`, plus its own commands for run, snapshot, upload and report URL.

Read `references/dekart-access.md` before the first Dekart call: availability check, each tool over MCP and CLI, differences (result files, uploads, timeouts, errors, setup, tokens).

Warehouse CLIs, for SQL-only answers (no map asked) or when Dekart has no connection for the warehouse; they need a shell:
- `bq` for BigQuery.
- `snow` for Snowflake.
- Wherobots and Postgres: Dekart only.
- MCP tools without a shell: no fallback; ask the user to add the connection in Dekart.

Nothing available: offer the setup options from that reference.

Then check connections with `list_connections`.


## Dialect References

Use the matching reference for per-database SQL, examples, and engine-specific caveats:

- BigQuery: `references/bigquery.md`
- DuckDB: `references/duckdb.md`
- Snowflake: `references/snowflake.md`
- Postgres / PostGIS: `references/postgres.md`
- Wherobots / Sedona: `references/wherobots.md`

Dekart references:

- Calling the tools (MCP or CLI): `references/dekart-access.md`
- Map config (`update_report_map_config`): `references/map-config.md`
- Charts (widgets): `references/widgets.md`
- Styling: `references/map-styling.md`

## Required Workflow

Follow these steps in order. Do NOT write a final query until steps 1-3 are complete.
Combine each step with examples in matching dialect reference.

### Step 1: Discover schema

Discover available data objects before writing any query: start with database/share availability (where applicable), then confirm schemas, tables, and columns. Always verify exact object names and column types from the warehouse metadata; do not assume from general knowledge.

When multiple tables match the entity, sample each candidate for attribute density and prefer the richer source. Richer attributes enable stronger visual encoding in Step 5 and a stronger map validation case.

### Step 2: Resolve the target area

When the user asks about a named area (city, district, country), query `division_area` first to discover how it is actually stored (subtype, class, naming conventions). Do not assume from general knowledge.

Use the dialect reference for target-area SQL and fallbacks. Extract the exact bbox constants from the result. Use the full precision values returned by the query, do not round or truncate them.

### Decision questions

When the prompt asks where to act (move, close, prioritise, allocate):

- Check the data before modelling it, with bounded scratch queries: volume per period against the median, missing or orphan keys, duplicates. Exclude anything only with a stated reason, and record it in the README.
- Answer for the hard case the decision must survive (a high percentile), not the average.
- Test the answer against the data's own limits: a recommendation must be feasible with what the data shows is available, and what it cannot cover is reported as its own number.
- Every threshold carries a one-line reason; every number in the answer comes from a saved query.

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
   * BigQuery: dry run to check estimated bytes. With Dekart, the mandatory `update_query` prepare step is also the dry-run gate; read `dry_run.valid` and `dry_run.estimated_bytes_processed` from that response before running the query with `run_query`.
     With the `bq` CLI, run the query with `bq query --use_legacy_sql=false --dry_run --format=json '<SQL>'` and parse the JSON output for `totalBytesProcessed`.
   * If dry run fails: read the error output. Common causes: string vs int type mismatch, missing backtick escaping, reserved keyword collision.
   * If estimated bytes exceed budget: do NOT execute. Instead, rewrite the query to be cheaper (tighter bbox, more filters, lower H3 resolution, etc) and validate again.
2. Validate row count: execute `COUNT(*)` (or equivalent) to confirm count is reasonable. If count is zero, debug before presenting.
3. Validate geometry magnitude when possible:
   - If output includes polygonal `GEOGRAPHY`, compute total area (for example `SUM(ST_AREA(geometry))`) and return units in square meters (and optionally km²).
   - If output includes line `GEOGRAPHY`, compute total length (for example `SUM(ST_LENGTH(geometry))`) and return units in meters (and optionally km).
   - If output includes `geometry`, measurements are CRS units. For EPSG:4326 geometry, do not report meters; transform/cast first or label the result as CRS units.
   - If geometry is point-only or no geometry is selected, explicitly state area/length validation is not applicable.
   - If the query computes point-to-point distances, check one pair by hand against a known distance before using them. In DuckDB, `ST_Distance_Sphere` expects latitude first, the opposite of `ST_Point` for the geometry column; a swapped order gives plausible but wrong distances (see `references/duckdb.md`).
4. Sanity-check whether row count and area/length are reasonable for the place and feature type (use domain knowledge). If numbers look implausible, debug before presenting.
5. If validation fails debug before presenting. Check bbox direction, value truncation, filter logic, and column types.


Iterate. Fix issues in small steps. Do not run broad or full extraction queries unless explicitly requested. All validation must be done in SQL.


### Step 5: Map Data

Maps catch what rows cannot: misplaced points, duplicates, coverage gaps.

If Dekart tools are available (MCP tools, or the `dekart` CLI installed and initialized), use map-in-the-loop flow by default: validate each step using map snapshot, when applicable.

If Dekart tools are not available but `bq` or `snow` is, answer first (SQL + results + cost), then propose creating a map as a "Next step" section with 2-3 map benefits for this specific question.

Do not claim visual insights until the styled snapshot is rendered and inspected; never dress row-derived facts as map observations.

Make sure maps are beautifully styled and communicate a clear insight. Always set the map title (`update_report_title`), dataset names (`update_dataset_name`) and layer labels, and add a README (`add_report_readme`) when the user asks for insight.

If Dekart is missing or its token is rejected, ask the user for the setup fix and wait until the user confirms with `ready`, `done`, or `ok`.

### Step 6: Add charts

Run when this task created a new report and its map layer (query or file-upload flow) and the widget tool is detected (detection in `references/widgets.md`). If the tool is absent, skip silently: no mention, no upsell.

Add charts by default, without asking, bound to the map-layer dataset only:

1. `number`: count of rows.
2. `number`: distinct of the map color/category field (the raw field, not the top-N group), or sum/avg of the main metric for aggregates.
3. `count-plot` on the map color field, `maxBars` 10, `sort` `value-desc` (doubles as legend and click filter). For aggregates colored by a numeric metric, use a `histogram` of that metric instead.
4. One `histogram` or time count-plot on the most relevant other numeric or month field; skip it on aggregates when item 3 already charts the only metric.

Any stat you would otherwise report in chat (totals, top categories, rates, ranges) becomes a chart; chat gives a one-line summary and the link.

On existing reports, add charts only on request, append-only. Verify with a snapshot that includes widgets (`create_report_snapshot` with `include_widgets`) and fix every error card on a `geosql-` chart before the final answer.


## Running Queries with `bq` CLI

Use `bq` CLI directly. Always use standard SQL and enforce a budget. Full command examples and guardrails: `references/bigquery.md`.

## Running Queries with `snow` CLI

Use `snow sql` directly for Snowflake data and keep queries bounded. Full command examples and guardrails: `references/snowflake.md`.


## Map Flow with Dekart

Use this when Dekart tools are available.

Write map styling with `update_report_map_config`; its `map_config` argument is a JSON string. Load `references/map-config.md` before writing or editing a map config.

### Artifact model

Dekart stores map artifacts in this hierarchy:
- `report`: top-level map container.
- `dataset`: one data layer slot inside a report, may contain a SQL query or uploaded file.
- `file`: uploaded data artifact attached to a dataset.
- `query`: SQL attached to a dataset/connection and executed asynchronously.
- `job`: execution instance for a query (`run_query` handles run -> wait -> fetch after the query has already been prepared).

Important IDs:
- `create_report` returns the canonical `report_id` at `result.report.id`, `result.report_id`, or `result.id`
- `create_dataset` returns the dataset id at `result.id`.
- `run_query` returns `job_id` and the result (`row_count`, `schema` and rows over MCP; `dataset_id`, `query_id`, status and `result_file` over the CLI).
- `report_url` fields returned directly by tools may miss host name; resolve the user-facing URL with `get_report_url`.
- Every layer `config.dataId`, filter `dataId`, and tooltip key in `map_config`, and every widget `dataId` in `widgets_config`, must use the report `dataset_id`, not `query_id`, `file_id`, source table name, or dataset label. Dataset ids are at `result.datasets[].id` in `get_report_properties`.

SQL goes to `update_query` as the `query_text` argument, full text, before the query runs:

```json
{
  "query_id": "<query_id>",
  "query_text": "<full SQL text>"
}
```

Over the CLI, save the SQL to a file and build this object into an `--args-file`; inline JSON is fragile because SQL contains quotes and newlines.

### Mode selection (required)

Choose exactly one flow based on whether SQL still needs to run:

1. File-upload mode: use when supplied or locally produced rows are already the final map layer. Execution path: `report -> dataset -> file -> upload_file`.
2. Query mode: use a connector for a warehouse source or DuckDB for same-report transformations and joins. Execution path: prepare datasets and queries, then run them with `run_query`.

Do not create both a raw-file map layer and a derived query layer unless the user explicitly asks. Query mode may upload a source file before running DuckDB.

### File-upload mode (final rows)

1. Check the current tool arguments and options before the first call (tool list over MCP; `dekart tools --schema <tool> --json` and `dekart run-query|snapshot|upload-file|report-url --help` over the CLI).
2. Gate: enter this flow ONLY after the analytical answer is delivered AND the user confirms the map step with `ready`, `done`, or `ok`. If user declines or is silent, stop; do not export CSV, do not create reports.
3. Once gated-in, get the result rows as CSV with explicit row controls. `--max_rows` is mandatory because BigQuery CLI defaults to 100 rows when omitted.
   - CSV export must keep stderr separate from CSV bytes.
   - Never use `2>&1` when output is redirected to `.csv`.
   - BigQuery: `bq query --use_legacy_sql=false --format=csv --max_rows=50000 'SELECT ...'`
   - Snowflake: `snow sql --format CSV --silent --query "<SQL with LIMIT 50000>"`
   - Over MCP the rows go inline into `upload_file`, which fits small results only (a few thousand rows). For larger results use query mode when Dekart has a connection for the warehouse; otherwise ask the user to upload with the `dekart` CLI, or say the map is limited to a sample.
4. Execute control plane in this exact order: `create_report` -> `create_dataset` (requires `report_id`, returns the dataset id as `result.id`) -> `create_file` (requires `dataset_id`).
5. Upload the CSV with `upload_file`.
6. Treat upload as successful only when completion status is `completed`.
7. Validate map output with a snapshot after successful upload:
   - `create_report_snapshot` for the target report
   - inspect the PNG it produces (in the response over MCP, the saved file over the CLI); do not use direct PNG URLs/links
   - verify snapshot render reflects expected area/content before finalizing
8. Add charts per Step 6, when it applies.
9. Return resulting IDs, absolute `report_url`, and image (when available) in final response.


### Query mode

For DuckDB, follow `references/duckdb.md`; its same-report source and query instructions replace the generic report and `connection_id` examples below.

1. Check the current tool arguments and options before the first call (tool list over MCP; `dekart tools --schema <tool> --json` and `dekart run-query|snapshot|report-url --help` over the CLI).
2. When a connector is involved, confirm available connections:
   - `list_connections` (no arguments)
   - pick a usable connection for the target warehouse/entity.
3. Execute control plane in this exact order: report -> dataset -> query -> run query.
   - `create_report` with `{}` -> capture `report_id` from `result.report.id`, `result.report_id`, or `result.id`.
   - `create_dataset` with `{"report_id":"<report_id>"}` -> capture `dataset_id` from `result.id`, `result.dataset_id`, or `result.dataset.id`. Note that datasets are single slot, re-running query owerwrites prevoise data.
   - Write the SQL. It must include geospatial output aliased exactly as lowercase `"geometry"` for the final map query.
4. Run all discovery, validation, preview, and assertion queries:
   - Create or reuse one scratch query:
     `create_query` with `{"dataset_id":"<scratch_dataset_id>","connection_id":"<id>"}`
   - Prepare it with `update_query` and `{"query_id":"<scratch_query_id>","query_text":"<full SQL text>"}`; for BigQuery, this response is the dry-run cost gate.
   - Only after `dry_run.valid` is true and cost is acceptable, execute and fetch with `run_query` and `{"query_id":"<scratch_query_id>"}`.
   - Read the result: rows and `schema` from the response over MCP; `result_file` then `dekart preview` over the CLI. Preview 20 rows; inspect columns and types.
   - `run_query` returns `job_id` and the result (`row_count`, `schema`, rows over MCP; `dataset_id`, `query_id`, status and `result_file` over the CLI).
   - If a metadata or SHOW statement returns no rows (`row_count` 0 over MCP, `empty result (metadata/SHOW statement?)` over the CLI), rewrite discovery SQL to return rows.
   - `run_query` waits for the job itself (over MCP about 45 s, then the "still running" handling). Do not hand-roll a poller or use temporary scripts for run/wait/fetch.
   - If you need diagnostic job status from `check_job_status`, the canonical tool payload status path is `result.query_job.job_status`.
5. Run the final map query against its **dedicated map-layer dataset**:
   - Create the map-layer query:
     `create_query` with `{"dataset_id":"<map_layer_dataset_id>","connection_id":"<id>"}`
   - Prepare it with `update_query` and `{"query_id":"<map_layer_query_id>","query_text":"<full SQL text>"}`; apply the BigQuery dry-run gate when applicable.
   - Execute and fetch with `run_query` and `{"query_id":"<map_layer_query_id>"}`.
   - One dedicated dataset per layer. Create a new report only when the user explicitly asks for more than one map/report.
   - The map-layer query is write-once: after it runs, never `update_query` or `run_query` it again. Run any later validation (area, length, counts, previews) on the scratch query from step 4 — re-running the map-layer query overwrites the layer with the new result and blanks the map.
6. Validate map output with a snapshot after successful job completion and row fetch:
   - `create_report_snapshot` with `{"report_id":"<report_id>"}`
   - if the snapshot is too zoomed out, centered poorly, or the user asks to zoom/pan, rerun with the transient view arguments instead of editing saved map state: `zoom`, `lat`, `lon`; derive lat/lon from target area or bbox center, pass `lat` and `lon` together, and preserve the same arguments on retry
   - inspect the PNG (response over MCP, saved file over the CLI); do not use direct PNG URLs/links
   - verify snapshot reflects expected area/content before finalizing
7. Add charts per Step 6, when it applies.
8. Return resulting IDs, absolute `report_url`, and image (when available) in final response:
   - `report_id`, `dataset_id`, `query_id`, `job_id`, terminal status (when available), and `report_url`.

### Failure handling
* Setup, token and connection problems are fixed by the user. Never run `dekart init` or `dekart config` on your own.
* If `create_report` or `create_dataset` returns 404 it is likely a token or auth issue. Ask the user for the token fix and confirm before retrying.
* Snapshot validation is mandatory, but diagnose in order: first verify map config bindings, columns, and view; if those are correct and the PNG is blank or missing WebGL features, treat it as a snapshot renderer issue and verify the interactive report.
* anti-loop rules for run/fetch: `run_query` waits for the job; never `| tail`, `| head` or background tasks on CLI commands.
* If a snapshot fails with a timeout (for example HTTP 504 / `snapshot timeout`), follow the timeout entry and retry the snapshot.
* Datasets auto-style by default. Kepler would apply a default styling if no config is provided for dataset provided.
* If snapshot shows only basemap (no features), debug binding first:
  - confirm `layer.config.dataId` points to the report dataset id
  - confirm tooltip `fieldsToShow` keys and filter `dataId` values also use the report dataset id
  - confirm bound column names match exported dataset headers exactly (case-sensitive). Note: snowflake export columns names are uppercase by default.
  – conform dataset data is not owerwrite by a later query.
* Never present `report_path` as a Map URL or user-facing link or manually user facing report URL.
* Resolve the final Map URL with `get_report_url`; do not treat `report_url` or `report_path` fields of other tools as canonical.
* Never call create-report multiple times just to get URL fields.
* Never call Dekart HTTP, config files, or anything outside the documented tools and `dekart` CLI.



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

When uncertain about a specific pixel value or palette, read the styling reference.

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
- Postgres: no local CLI fallback. If the Dekart Postgres connection is missing or auth fails, ask the user to add it in Dekart; do not attempt a CLI workaround.
- PostGIS not enabled (`geometry_columns` errors): ask the user to run `CREATE EXTENSION postgis;`, then continue.
- Wherobots: no local CLI fallback. If the Dekart Wherobots connection is missing or auth fails, ask the user to add it in Dekart; do not attempt a CLI workaround.
- Over budget: do not execute, return cheaper variant.
- Invalid query: return corrected SQL and rerun validation (`update_query` dry-run for BigQuery, `COUNT(*)`/bounded preview for Snowflake, tightly bounded `COUNT(*)`/preview execution through a Dekart connection for Wherobots).
- Never install software automatically. Report prerequisite commands for the user to run.
