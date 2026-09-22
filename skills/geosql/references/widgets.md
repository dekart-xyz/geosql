# Widgets Reference (Charts pane)

Load when the widget tool is available. Charts render in a pane next to the map and filter it: clicking a count-plot bar filters the map layers on the same dataset. The `dataId` rule is canonical in SKILL.md (Important IDs).

## Detection

Both must hold:

```bash
dekart tools --names | grep -qx update_report_widgets_config && echo widgets=ok
dekart snapshot --help | grep -q -- --include-widgets && echo snapshot=ok
```

- Tool missing: the server has no charts. Skip charts silently.
- Tool present, `--include-widgets` missing: the CLI is older than 0.21.0 and cannot verify charts. Ask the user to run `pip install -U dekart`, wait for confirmation, then continue. Never write charts you cannot verify.

## Document

```json
{"version": 1, "widgets": [{"id": "geosql-total", "dataId": "<dataset_id>", "type": "number", "title": "Crimes", "settings": {"operation": "count"}}]}
```

- Every widget needs `id`, `dataId`, `type`, `title`, `settings`. Unknown keys are rejected.
- Max 100 widgets. `id` matches `^[A-Za-z0-9_-]{1,128}$` and is unique in the report.
- `widgets_config` is a JSON **string** inside the args, built with `json.dumps`. Sending an object fails with `proto: ... invalid value for string field widgetsConfig`.
- Bind every chart to the final map-layer dataset (the one the primary map layer uses). Never bind to the scratch dataset (validation queries overwrite it) or to DuckDB source datasets, unless the user asks.

## Types and field compatibility

Column types come from the dataset file as DuckDB reads it, not from your SQL. Check them with `dekart preview <result_file> --schema`.

| Type | Settings | Field must be |
|---|---|---|
| `number` | `operation`: `count`, `distinct`, `sum`, `avg`, `min`, `max`, `median`; `field` (required unless `count`); `format`: `auto`, `number`, `compact`, `percent`; `decimals` 0-6; `prefix`, `suffix`, `subtitle` | `count`: no field. `distinct`: any. Others: numeric (not boolean) |
| `count-plot` | `field`, `sort`: `value-desc`, `value-asc`, `label-asc`, `label-desc`; `maxBars` 1-100 | text (`VARCHAR`). Not boolean, not integer |
| `histogram` | `field`, `maxBins` 1-1000, `color` | numeric. Not text timestamps |

A count-plot always counts rows. On an aggregate dataset (one row per district or cell) a count-plot of the id column shows 1 per bar; use a histogram of the metric instead, or a count-plot of a category per row (for example the top type per cell).

An incompatible widget can break other charts on the same dataset: one `avg` over a boolean made every `number` chart on that dataset fail. Treat any error card as blocking.

## SQL shaping (Step 3)

Shape the map-layer query so chart columns exist with the right types:

- Category from an integer: prefix it. BigQuery `CONCAT('D', CAST(district AS STRING)) AS district_label`, DuckDB `'D' || CAST(district AS VARCHAR)`. A plain cast to string is not enough: digit-only strings in a CSV result load back as `BIGINT`.
- Time for a count-plot: `FORMAT_TIMESTAMP('%Y-%m', date) AS month` (BigQuery) or `strftime(date, '%Y-%m')` (DuckDB), sorted with `label-asc`. A bare year string loads as a number; use a histogram on a numeric year instead.
- Time for a histogram: extract a number (`EXTRACT(HOUR FROM date) AS hour`, `maxBins` 24). BigQuery timestamps export as text (`2024-06-17 09:59:00 +0000 UTC`) and cannot feed a histogram.
- Rate from a boolean: `CAST(arrest AS INT64) AS arrest_int` (DuckDB `CAST(arrest AS INTEGER)`), then `number` with `operation: avg`, `format: percent`.
- Top category per aggregate row (for an H3 or district count-plot): DuckDB `mode(primary_type) AS top_type`, BigQuery `APPROX_TOP_COUNT(primary_type, 1)[OFFSET(0)].value AS top_type`.
- Top 7 plus `OTHER`, when the map color field has more than 8 categories, so the map palette and the count-plot share the same groups:

  ```sql
  WITH top_types AS (
    SELECT primary_type FROM <source> GROUP BY primary_type ORDER BY count(*) DESC LIMIT 7
  )
  SELECT
    primary_type,  -- keep the raw column for the distinct chart
    CASE WHEN primary_type IN (SELECT primary_type FROM top_types) THEN primary_type ELSE 'OTHER' END AS type_group,
    ...
  ```

## Read, append, write

`update_report_widgets_config` replaces the whole document. Read immediately before every write; never write from a copy read earlier in the session.

- Current widgets: `result.report.widgets_config` from `get_report_properties`, a JSON string. The key is omitted when the report has no charts; start from `{"version":1,"widgets":[]}`.
- Dataset ids: `result.datasets[].id` (names at `result.datasets[].name` when set).

```bash
dekart call --name get_report_properties --args '{"report_id":"<report_id>"}' --json --out /tmp/report-props.json \
  && python3 - <<'EOF' && dekart call --name update_report_widgets_config --args-file /tmp/widgets-args.json --json
import json
props = json.load(open("/tmp/report-props.json"))
doc = json.loads(props["result"]["report"].get("widgets_config") or '{"version":1,"widgets":[]}')
new = [
    {"id": "geosql-total", "dataId": "<map_layer_dataset_id>", "type": "number", "title": "Crimes", "settings": {"operation": "count", "format": "compact"}},
]
taken = {w["id"] for w in doc["widgets"]} & {w["id"] for w in new}
assert not taken, f"ids already in the report: {taken}"
doc["widgets"] += new
json.dump({"report_id": "<report_id>", "widgets_config": json.dumps(doc)}, open("/tmp/widgets-args.json", "w"))
EOF
```

The write runs only if the fresh read and the merge succeed. If the assert fires, pick a new id (for example `geosql-top-type-2`); never overwrite an existing chart by reusing its id.

## Ownership

- Id convention: `geosql-<purpose>` (`geosql-total`, `geosql-top-type`, `geosql-hour`) marks charts this skill created.
- Default is append-only. Change or remove an existing chart, `geosql-` or not, only when the current request is about that chart.
- The map-layer query is write-once (SKILL.md). If the user explicitly asks to change it, first list the fields every chart on it uses (any owner) and keep those columns with the same types. Add columns; never rename or retype them. If a user chart still breaks, report it; do not delete it.

## Verify

```bash
dekart snapshot --report-id <report_id> --include-widgets --out /tmp/<report_id>-charts.png
```

Without `--include-widgets` the snapshot shows the map only. A failed chart shows "This chart couldn't load." Fix the `geosql-` chart (field type, SQL shaping) and re-snapshot before reporting done. A failing user chart is reported, not edited. Add `--height 1400` when charts are cut off (local rendering only).

## Errors

Re-run a failed call with `--debug` to see the response body.

| Error | Fix |
|---|---|
| `invalid value for string field widgetsConfig` | `json.dumps` the document |
| `widgets_config_validation_failed`, `unknown_dataset_id` | use an id from `result.datasets[].id` |
| `invalid widget configuration: ... missing properties: 'field'` | `field` is required for every `number` operation except `count` |
| `widget id "<id>" must be unique within the report` | pick a new `geosql-` id |

## Worked examples

All three rendered without error cards on the Chicago crime report. For aggregates, the metric histogram fills Step 6 item 3, so item 4 becomes another `number` card when no second field is worth charting.

### Points (one row per crime, map colored by `type_group`, top 7 plus `OTHER`)

```json
[
  {"id": "geosql-total", "dataId": "<dataset_id>", "type": "number", "title": "Crimes", "settings": {"operation": "count", "format": "compact"}},
  {"id": "geosql-types", "dataId": "<dataset_id>", "type": "number", "title": "Crime types", "settings": {"operation": "distinct", "field": "primary_type"}},
  {"id": "geosql-top-type", "dataId": "<dataset_id>", "type": "count-plot", "title": "Crimes by type", "settings": {"field": "type_group", "sort": "value-desc", "maxBars": 10}},
  {"id": "geosql-hour", "dataId": "<dataset_id>", "type": "histogram", "title": "Crimes by hour", "settings": {"field": "hour", "maxBins": 24}}
]
```

### Polygon aggregate (one row per district, map colored by `crime_count`)

```json
[
  {"id": "geosql-total", "dataId": "<dataset_id>", "type": "number", "title": "Crimes (all districts)", "settings": {"operation": "sum", "field": "crime_count", "format": "compact"}},
  {"id": "geosql-arrest-rate", "dataId": "<dataset_id>", "type": "number", "title": "Avg district arrest rate", "settings": {"operation": "avg", "field": "arrest_rate", "format": "percent", "decimals": 1}},
  {"id": "geosql-districts", "dataId": "<dataset_id>", "type": "number", "title": "Districts", "settings": {"operation": "count"}},
  {"id": "geosql-count-dist", "dataId": "<dataset_id>", "type": "histogram", "title": "Crimes per district", "settings": {"field": "crime_count", "maxBins": 10}}
]
```

### H3 aggregate (one row per cell, map colored by `crime_count`)

```json
[
  {"id": "geosql-cells", "dataId": "<dataset_id>", "type": "number", "title": "H3 cells", "settings": {"operation": "count"}},
  {"id": "geosql-total", "dataId": "<dataset_id>", "type": "number", "title": "Crimes", "settings": {"operation": "sum", "field": "crime_count", "format": "compact"}},
  {"id": "geosql-top-type", "dataId": "<dataset_id>", "type": "count-plot", "title": "Cells by top crime type", "settings": {"field": "top_type", "sort": "value-desc", "maxBars": 10}},
  {"id": "geosql-count-dist", "dataId": "<dataset_id>", "type": "histogram", "title": "Crimes per cell", "settings": {"field": "crime_count", "maxBins": 20}}
]
```
