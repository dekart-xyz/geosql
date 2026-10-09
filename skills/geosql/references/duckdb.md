# DuckDB Reference

Use DuckDB to transform or join uploaded files, connector-query results and HTTP sources (JSON, CSV, GeoJSON or parquet fetched by Dekart from an HTTPS URL of a saved HTTP source connection) already represented in one Dekart report. Keep every source, scratch, and output dataset in that report; reuse the source report instead of creating a separate output report.

## Prerequisites

1. Identify the Python interpreter that owns `command -v dekart`; do not assume `python` or `python3` is the same environment. Run `<dekart-python> -c 'import sys; from importlib.metadata import version; print(sys.version.split()[0], version("dekart"))'`. If Python is older than 3.9, stop and ask the user to install Dekart under Python 3.9 or newer. If the Dekart CLI is older than 0.16.0, stop and ask the user to run `<dekart-python> -m pip install --upgrade 'dekart>=0.16.0'`. Queries over HTTP sources need 0.22.0 or newer. If any `dekart` command answers `Update GeoSQL and the Dekart CLI: pip install --upgrade geosql dekart`, ask the user to run that command, then retry once; do not loop.
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
- For an HTTP source, no dataset is uploaded: `dekart call --name list_connections --json` lists HTTP sources with their base URL, docs URL and header names (never values). The DuckDB query reads the URL directly (see below). If no HTTP source covers the host, ask the user to create one in Dekart under Connections, naming the host; `create_connection` is not available through MCP.

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

Alias map geometry exactly as lowercase `geometry`. Do not add `INSTALL`, `LOAD`, file readers, or internal schema setup; Dekart prepares those statements for the CLI and browser. Save SQL with `update_query` and require `dry_run.valid` before execution.

The one reader you write yourself is an HTTP source: `read_json`, `read_json_auto`, `read_csv`, `read_csv_auto`, `read_parquet` or `ST_Read` (GeoJSON, `keep_wkb` is the only option) with one constant HTTPS URL under the base URL of a saved HTTP source:

```sql
SELECT * FROM read_json('https://api.example.com/v1/stations')
```

When the URL depends on values in a dataset of the report, pass a scalar subquery whose single column is `format('<constant URL template>', <expressions>)`; each `{}` stands for one complete query-parameter value, and the subquery must return exactly one row:

```sql
SELECT * FROM read_json((
  SELECT format('https://api.example.com/v1/isochrone?lat={}&lng={}', latitude, longitude)
  FROM datasets."Stations" WHERE station_id = '<id>'
))
```

A query may hold one computed URL and no constant reader beside it; constant readers alone may appear several times. Put each computed URL in its own query and join the results in a third. Globs, lists, concatenated URLs, `{{param}}` inside the URL, and hosts without an HTTP source fail `dry_run` with a one-line reason; fix the SQL or ask the user for the connection rather than retrying unchanged. Dekart fetches the URL with the connection's headers on every run, so results reflect the API at run time. A computed URL whose subquery returns zero or several rows fails with `HTTP source URL query returned <n> rows; exactly one non-empty URL is required.`

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

The CLI waits for connector dependencies, downloads pinned inputs and HTTP sources (computing dataset-derived URLs in the same order as the browser), and materializes the browser-equivalent Parquet result locally. Do not reproduce that logic in shell commands. Use `--params-json` when the report query uses parameters.

After the final query runs, perform later counts, measurements, and previews through the scratch query so the final map layer is not overwritten. In `map_config`, bind layers only to the derived output dataset; omit source dataset IDs unless the user asks to display the raw sources too.
