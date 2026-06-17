# Wherobots / Sedona Reference

## Step 1: Discover Schema

Wherobots is dekart-only here (no local CLI fallback). Discover catalogs/tables via dekart's connection, and confirm the geometry column and that it is in EPSG:4326 before drafting. Sedona uses `ST_*` functions similar to PostGIS.

Run Wherobots discovery SQL through Dekart query mode. Use `dekart call --name list_connections --args '{}' --json` first and select a `CONNECTION_TYPE_WHEROBOTS` connection id, then run SQL with `dekart query`.

Avoid `SHOW` / `DESCRIBE`. Prefer bounded row previews and metadata queries that return rows, for example:

```sql
-- List schemas as rows when information_schema is available
SELECT catalog_name, schema_name
FROM wherobots_open_data.information_schema.schemata
WHERE schema_name LIKE '%overture%'
ORDER BY schema_name
LIMIT 50;
```

```sql
-- List tables as rows when information_schema is available
SELECT table_schema, table_name
FROM wherobots_open_data.information_schema.tables
WHERE table_schema = 'overture_maps_foundation'
ORDER BY table_name
LIMIT 200;
```

```sql
-- List columns as rows when information_schema is available
SELECT table_schema, table_name, column_name, data_type
FROM wherobots_open_data.information_schema.columns
WHERE table_schema = 'overture_maps_foundation'
  AND table_name = '<target_table>'
ORDER BY ordinal_position;
```

If `information_schema` is unavailable for the connection, use this row-returning Overture seed list to choose the first preview tables instead of using `SHOW` / `DESCRIBE`:

```sql
SELECT *
FROM VALUES
  ('divisions_division_area', 'administrative boundaries and named areas'),
  ('transportation_segment', 'roads, rail, paths, and transport segments'),
  ('places_place', 'points of interest and places'),
  ('buildings_building', 'building footprints')
AS overture_tables(table_name, notes);
```

```sql
SELECT * FROM wherobots_open_data.overture_maps_foundation.divisions_division_area LIMIT 5;
```

Overture tables in Wherobots use `<theme>_<type>` names, for example `divisions_division_area`, `transportation_segment`, `places_place`, and `buildings_building`. For map output, select a geometry column aliased exactly as lowercase `geometry`.

## Step 2: Resolve The Target Area

Use Wherobots Overture `divisions_division_area` when it is available. Run this through Dekart query mode:

```sql
SELECT
  subtype,
  class,
  names.primary AS name_primary,
  bbox.xmin AS xmin,
  bbox.xmax AS xmax,
  bbox.ymin AS ymin,
  bbox.ymax AS ymax
FROM wherobots_open_data.overture_maps_foundation.divisions_division_area
WHERE country = '<ISO2>'
  AND LOWER(names.primary) LIKE '%<area_name>%'
LIMIT 20;
```

If no matching boundary exists in Wherobots Overture, use another boundary table visible through the same Wherobots connection, a user-supplied polygon, or an explicit lon/lat bbox supplied by the user. Do not switch to a direct Wherobots notebook or SDK path.

## Step 3: Draft The Query

Wherobots Overture examples must run through Dekart query mode. Sedona does not support the PostGIS `&&` operator, so use the explicit bbox overlap pattern plus `ST_Intersects`. Keep the geospatial output column aliased exactly as lowercase `geometry`.

```sql
WITH area AS (
  SELECT geometry
  FROM wherobots_open_data.overture_maps_foundation.divisions_division_area
  WHERE country = 'DE'
    AND region = 'DE-BE'
    AND subtype = 'region'
    AND class = 'land'
  LIMIT 1
)
SELECT
  s.id,
  s.subtype,
  s.geometry AS geometry
FROM wherobots_open_data.overture_maps_foundation.transportation_segment s
CROSS JOIN area a
WHERE s.subtype = 'rail'
  AND s.bbox.xmax >= 13.08834457397461
  AND s.bbox.xmin <= 13.761162757873535
  AND s.bbox.ymax >= 52.33823776245117
  AND s.bbox.ymin <= 52.67551040649414
  AND ST_Intersects(s.geometry, a.geometry)
LIMIT 1000;
```

## H3 Aggregation

Wherobots/Sedona H3:
- `ST_H3CellIDs(geometry, <resolution>, <fullCover>)` returns H3 cell ids for a geometry.
- `ST_H3ToGeom(<array_of_cells>)` converts H3 ids back to geometry for map output.
