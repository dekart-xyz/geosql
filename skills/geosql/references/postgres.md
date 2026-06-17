# Postgres / PostGIS Reference

## Step 1: Discover Schema

Postgres has no Overture public dataset. Discover the user's own spatial tables; do not assume table or column names.

```sql
-- List tables that have a geometry/geography column
SELECT f_table_schema, f_table_name, f_geometry_column, type, srid
FROM geometry_columns
ORDER BY f_table_schema, f_table_name;
```

```sql
-- Columns and types for a target table
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = '<schema>'
  AND table_name = '<target_table>'
ORDER BY ordinal_position;
```

Confirm the geometry column's SRID (expect `4326` for lon/lat). If SRID differs, plan to `ST_Transform(geom, 4326)` for map output. PostGIS must be enabled (`CREATE EXTENSION postgis;`); if `geometry_columns` errors, stop and ask the user to enable PostGIS.

## Step 2: Resolve The Target Area

There is no Overture `division_area` to resolve against. Use whatever boundary source exists in the user's data (an admin-boundary table, a user-supplied polygon, or an explicit bbox the user provides). If no boundary geometry exists, fall back to an explicit lon/lat bbox supplied by the user. Compute the bbox of a chosen boundary row with:

```sql
SELECT ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom)
FROM <boundary_table>
WHERE <name_column> ILIKE '%<area_name>%';
```

Extract the exact bbox constants from the result. Use the full precision values returned by the query, do not round or truncate them.

## Step 3: Draft The Query

PostGIS has no `bbox` struct column; use the `&&` bounding-box operator (index-accelerated) as the scan gate, then `ST_Intersects` for correctness. Build the area envelope from a boundary row or an explicit bbox.

```sql
WITH area AS (
  SELECT geom
  FROM admin_boundaries
  WHERE name ILIKE '%Berlin%'
  LIMIT 1
)
SELECT s.id, s.geom
FROM segments s
CROSS JOIN area a
WHERE s.subtype = 'rail'
  -- index-accelerated bbox overlap gate
  AND s.geom && a.geom
  -- exact geometry test
  AND ST_Intersects(s.geom, a.geom)
LIMIT 1000;
```

If you only have an explicit bbox (no boundary geometry), gate with `ST_MakeEnvelope`:

```sql
AND s.geom && ST_MakeEnvelope(13.0883, 52.3382, 13.7612, 52.6755, 4326)
```

Ensure both geometries share SRID 4326; wrap with `ST_Transform(..., 4326)` if not.

## H3 Aggregation

For Postgres use the `h3`/`h3-pg` extension (`h3_lat_lng_to_cell`, `h3_cell_to_boundary`). Confirm the function exists before using it.
