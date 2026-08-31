# DuckDB Reference

Use DuckDB to transform or join uploaded files and connector-query results already represented as datasets in one Dekart report. Keep every source, scratch, and output dataset in that report; reuse the source report instead of creating a separate output report.

## Prerequisites

1. Identify the Python interpreter that owns `command -v dekart`; do not assume `python` or `python3` is the same environment. Run `<dekart-python> -c 'import sys; from importlib.metadata import version; print(sys.version.split()[0], version("dekart"))'`. If Python is older than 3.9, stop and ask the user to install Dekart under Python 3.9 or newer. If the Dekart CLI is older than 0.16.0, stop and ask the user to run `<dekart-python> -m pip install --upgrade 'dekart>=0.16.0'`.
2. Run `dekart tools --schema create_query --json` and `dekart tools --schema run_query --json`. Continue only when `create_query` exposes `QUERY_EXECUTION_ENGINE_DUCKDB` and `run_query` exposes `accept_duckdb_execution`; otherwise keep using connector queries when possible and suggest updating both the CLI and server. If `run-query` still rejects DuckDB, report both versions and ask the user to use their latest releases.

## Extensions

Dekart prepares `spatial`, `parquet`, `json`, and the community `h3` extension
before report SQL runs. The browser uses bundled signed WebAssembly extensions;
the CLI installs signed extensions requested by the server and reuses DuckDB's
cache. The first CLI DuckDB run may therefore require access to DuckDB's core
and community extension repositories.

The official documentation follows the latest DuckDB release. Before using a
less common function or overload, confirm it with a bounded scratch query that
invokes that exact operation on literal inputs, for example:

```sql
SELECT
  h3_latlng_to_cell_string(52.5, 13.4, 8) AS h3,
  json_valid('{"source":"probe"}') AS json_available;
```

Do not query `duckdb_functions()` from report SQL; Dekart intentionally limits
which table functions queries may call.

Complete API references:

- H3 community extension: <https://duckdb.org/community_extensions/extensions/h3>
- JSON overview: <https://duckdb.org/docs/current/data/json/overview>
- JSON processing: <https://duckdb.org/docs/current/data/json/json_functions>
- JSON creation: <https://duckdb.org/docs/current/data/json/creating_json>
- JSON loading: <https://duckdb.org/docs/current/data/json/loading_json>

## Discover Schema And Area

For a source without Overture's `division_area` or `bbox` structure, this section overrides Steps 1-3 in the main skill. Inspect local CSV or Parquet columns with `dekart preview <source_file> --schema`. For JSON, GeoJSON, or a remote dataset, run a bounded scratch query such as `SELECT * FROM datasets."<dataset name>" LIMIT 20`, then inspect its Parquet result with `dekart preview <result_file> --schema`. Resolve a named area from a boundary dataset in the report or an explicit bbox supplied by the user; if neither is available, ask for one instead of inventing it. Apply bbox overlap pruning only when the source provides bbox fields, and apply an exact spatial predicate whenever boundary geometry is available.

## Sources

- Give every source dataset a unique name with `update_dataset_name`; DuckDB resolves sources by dataset name within the report.
- For an uploaded source, create and name its dataset, call `create_file`, then upload CSV, Parquet, JSON, or GeoJSON with `dekart upload-file`.
- For a connector source, prepare and run its connection-backed query in the same report. Apply that connector's cost and validation rules before running it.

## Prepare Queries

Create separate scratch and final-output datasets. Create both queries with the DuckDB engine and no `connection_id`:

```bash
dekart call --name create_query --args '{"dataset_id":"<dataset_id>","execution_engine":"QUERY_EXECUTION_ENGINE_DUCKDB"}' --json
```

Reference sources as `datasets."<dataset name>"`:

```sql
SELECT id, ST_Point(longitude, latitude) AS geometry
FROM datasets."Source dataset"
ORDER BY id
```

Alias map geometry exactly as lowercase `geometry`. Do not add `INSTALL`, `LOAD`, source readers, or internal schema setup; Dekart prepares those statements for the CLI and browser. Save SQL with `update_query` and require `dry_run.valid` before execution.

For a Kepler H3 layer, return a string cell ID named exactly `h3`. Pass
latitude before longitude and aggregate before computing boundary geometry:

```sql
SELECT
  h3_latlng_to_cell_string(latitude, longitude, 8) AS h3,
  count(*) AS point_count
FROM datasets."Source dataset"
WHERE latitude BETWEEN <south> AND <north>
  AND longitude BETWEEN <west> AND <east>
GROUP BY h3;
```

Kepler renders H3 cells directly, so omit boundary geometry unless the
analysis needs it. For JSON attributes or tooltips, use
`json_extract_string` (or `->>` on a `JSON` value) to return unquoted scalar
text. DuckDB JSON arrays are zero-indexed.

## Execute And Inspect

Run scratch validation first, then run the final map query once:

```bash
dekart run-query --query-id <query_id> --out-dir <dir> --wait --json
dekart preview <result_file> --schema
dekart preview <result_file> --limit 20
```

The CLI waits for connector dependencies, downloads pinned inputs, and materializes the browser-equivalent Parquet result locally. Do not reproduce that logic in shell commands. Use `--params-json` when the report query uses parameters.

After the final query runs, perform later counts, measurements, and previews through the scratch query so the final map layer is not overwritten. In `map_config`, bind layers only to the derived output dataset; omit source dataset IDs unless the user asks to display the raw sources too.
