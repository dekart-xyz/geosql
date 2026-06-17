# Snowflake Reference

## Step 1: Discover Schema

```sql
SHOW DATABASES LIKE 'OVERTURE_MAPS__%';
```

If this returns no rows, stop and ask the user to install Overture Maps shares from Snowflake Marketplace before continuing.

```sql
SELECT table_catalog, table_schema, table_name
FROM OVERTURE_MAPS__TRANSPORTATION.INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'CARTO'
ORDER BY table_name;
```

```sql
SELECT column_name, data_type
FROM OVERTURE_MAPS__TRANSPORTATION.INFORMATION_SCHEMA.COLUMNS
WHERE table_schema = 'CARTO'
  AND table_name = '<TARGET_TABLE>'
ORDER BY ordinal_position;
```

## Step 2: Resolve The Target Area

```sql
SELECT subtype,
       class,
       names:primary::string AS name_primary,
       bbox:xmin::float AS xmin,
       bbox:xmax::float AS xmax,
       bbox:ymin::float AS ymin,
       bbox:ymax::float AS ymax
FROM OVERTURE_MAPS__DIVISIONS.CARTO.DIVISION_AREA
WHERE country = '<ISO2>'
  AND LOWER(names:primary::string) LIKE '%<area_name>%'
LIMIT 20;
```

## Step 3: Draft The Query

```sql
WITH area AS (
  SELECT geometry
  FROM OVERTURE_MAPS__DIVISIONS.CARTO.DIVISION_AREA
  WHERE country = 'DE'
    AND region = 'DE-BE'
    AND subtype = 'region'
    AND class = 'land'
  LIMIT 1
)
SELECT s.id, s.geometry
FROM OVERTURE_MAPS__TRANSPORTATION.CARTO.SEGMENT s
CROSS JOIN area a
WHERE s.subtype = 'rail'
  AND s.bbox:xmax::float >= 13.08834457397461
  AND s.bbox:xmin::float <= 13.761162757873535
  AND s.bbox:ymax::float >= 52.33823776245117
  AND s.bbox:ymin::float <= 52.67551040649414
  AND ST_INTERSECTS(s.geometry, a.geometry)
LIMIT 1000;
```

## Running Queries With `snow` CLI

Use `snow sql` directly for Snowflake data and keep queries bounded.

```bash
# First verify Overture shares are installed
snow sql --query "SHOW DATABASES LIKE 'OVERTURE_MAPS__%';"

# Validate quickly with row count first
snow sql --query "WITH area AS (...) SELECT COUNT(*) FROM ...;"

# Execute preview rows (table output)
snow sql --query "WITH area AS (...) SELECT ... LIMIT 50;"

# CSV output for piping (clean stdout)
snow sql --format CSV --silent --query "WITH area AS (...) SELECT ... LIMIT 50000;"
```

Guardrails:
1. Always validate with tight filters and `COUNT(*)` first.
2. Always keep extraction bounded (`bbox` + `ST_INTERSECTS` + `LIMIT`) unless the user explicitly asks for full export.
3. For map export, use CSV mode with `--format CSV --silent`.
4. Ensure a default Snow CLI connection is configured before running commands.
5. If `SHOW DATABASES LIKE 'OVERTURE_MAPS__%'` returns no rows, ask the user to install Overture Maps from Snowflake Marketplace, then retry.

## H3 Aggregation

For Snowflake use native `H3_*` functions. Confirm the function exists before using it.
