# Map Config Reference (`update_report_map_config`)

Load when writing or editing a report `map_config`. Styling choices (palette, radius, basemap) are in `references/map-styling.md`. The `dataId` rule is canonical in SKILL.md (Important IDs); every example below follows it.

## Write command

`map_config` is a JSON **string** inside the args object, not a nested object. Sending an object fails with `proto: ... invalid value for string field mapConfig`. Build the args file with `json.dumps` in a heredoc, never by hand:

```bash
python3 - <<'EOF'
import json
report_id = "<report_id>"
ds = "<map_layer_dataset_id>"
config = {
    "version": "v1",
    "config": {
        "visState": {
            "layers": [],             # layer objects from the examples below
            "interactionConfig": {"tooltip": {"enabled": True, "fieldsToShow": {ds: [{"name": "<column>"}]}}},
        },
        "mapState": {"latitude": 41.8781, "longitude": -87.6298, "zoom": 11},
        "mapStyle": {"styleType": "dark"},
    },
}
json.dump({"report_id": report_id, "map_config": json.dumps(config)}, open("/tmp/map-config-args.json", "w"))
EOF
dekart call --name update_report_map_config --args-file /tmp/map-config-args.json --json
```

`visState.layers` order is render order: first layer is drawn on top.

## Editing an existing report

Read before you write. `get_report_properties` returns the saved config at `result.report.map_config` as a JSON string; `json.loads` it, change only what the request needs, and write the whole document back. The key is omitted when the report has no saved config yet.

```bash
dekart call --name get_report_properties --args '{"report_id":"<report_id>"}' --json
```

## Layer shape

Channel bindings live in `layer.visualChannels`, a sibling of `layer.config`, never inside `config`. A field reference is `{"name": "<column>", "type": "<kepler type>"}` with type `string`, `integer`, `real`, `boolean`, or `timestamp`. Palettes go in `config.visConfig.colorRange.colors`; a custom list of hex colors is applied as given.

Scales: `ordinal` for text categories, `quantile` for skewed counts (most aggregates), `quantize` only for evenly spread values.

## Worked examples

Each layer below passed `update_report_map_config` and rendered in a snapshot against real Chicago crime and Overture data.

### 1. Points colored by category

Source rows have a WKT point column `geometry` (BigQuery CSV export) and a text column `type_group` (top 7 crime types plus `OTHER`, recipe in `references/widgets.md`). Use a `geojson` layer; `radius` sets point size.

```json
{
  "id": "crimes",
  "type": "geojson",
  "config": {
    "dataId": "<dataset_id>",
    "label": "Crimes by type",
    "columns": {"geojson": "geometry"},
    "isVisible": true,
    "visConfig": {
      "opacity": 0.8, "radius": 2, "filled": true, "stroked": false,
      "colorRange": {
        "name": "Top types", "type": "qualitative", "category": "Custom",
        "colors": ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#f781bf", "#999999"]
      }
    }
  },
  "visualChannels": {
    "colorField": {"name": "type_group", "type": "string"},
    "colorScale": "ordinal"
  }
}
```

Colors are assigned to categories in order. Keep the color field to 8 categories or fewer (top 7 plus `OTHER`) so every category gets its own color.

### 2. Polygon choropleth on a numeric field

```json
{
  "id": "districts",
  "type": "geojson",
  "config": {
    "dataId": "<dataset_id>",
    "label": "Crimes per district",
    "columns": {"geojson": "geometry"},
    "isVisible": true,
    "visConfig": {
      "opacity": 0.7, "filled": true, "stroked": true, "thickness": 0.5, "strokeColor": [255, 255, 255],
      "colorRange": {"name": "YlOrRd", "type": "sequential", "category": "ColorBrewer",
                     "colors": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]}
    }
  },
  "visualChannels": {
    "colorField": {"name": "crime_count", "type": "integer"},
    "colorScale": "quantile"
  }
}
```

### 3. H3 cells

Layer type is `hexagonId`; the column key is `hex_id`, bound to the string cell id column (`h3`).

```json
{
  "id": "h3",
  "type": "hexagonId",
  "config": {
    "dataId": "<dataset_id>",
    "label": "Crimes per H3 cell",
    "columns": {"hex_id": "h3"},
    "isVisible": true,
    "visConfig": {
      "opacity": 0.8, "coverage": 1, "enable3d": false,
      "colorRange": {"name": "Viridis", "type": "sequential", "category": "Uber",
                     "colors": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]}
    }
  },
  "visualChannels": {
    "colorField": {"name": "crime_count", "type": "integer"},
    "colorScale": "quantile"
  }
}
```

### 4. Lines with width by field

Roads as WKT `LINESTRING` in `geometry`, with a numeric `width` column computed in SQL (for example `CASE class WHEN 'motorway' THEN 3.0 WHEN 'primary' THEN 2.0 ELSE 0.5 END`). Stroke width is the `size` channel; `sizeRange` sets the pixel range.

```json
{
  "id": "roads",
  "type": "geojson",
  "config": {
    "dataId": "<dataset_id>",
    "label": "Major roads",
    "columns": {"geojson": "geometry"},
    "isVisible": true,
    "color": [60, 60, 60],
    "visConfig": {"opacity": 0.9, "stroked": true, "filled": false, "thickness": 1,
                  "strokeColor": [60, 60, 60], "sizeRange": [0.5, 4]}
  },
  "visualChannels": {
    "sizeField": {"name": "width", "type": "real"},
    "sizeScale": "linear"
  }
}
```

## Initial view

Save the insight view in `mapState` (`latitude`, `longitude`, `zoom`). `dekart snapshot --lat/--lon/--zoom` only overrides the view for that render; it does not change the saved map.

## Errors

The CLI prints only the error code. Re-run the same call with `--debug` to see `response_body.issues[]`; each issue has `path` and `actual`. A single mistake can produce many issues, one per layer type the validator tried; look for the one that names your key.

| Error | Cause | Fix |
|---|---|---|
| `proto: ... invalid value for string field mapConfig` | `map_config` sent as an object | `json.dumps` the config into a string |
| `map_config_validation_failed`, `additionalProperties 'colorField' not allowed` | channel field inside `config` | move `colorField`/`colorScale` (and `sizeField`, etc.) to `layer.visualChannels` |
| `map_config_validation_failed`, `unknown_dataset_id` | `dataId` or tooltip key is not a report dataset id | use `result.datasets[].id` from `get_report_properties` |
| `map_config_validation_failed`, `missing properties: 'hex_id'` or `'lat', 'lng'` | wrong `columns` keys for the layer type | use the keys from the examples above |

Column names are not validated. A config that binds a missing or misspelled column is accepted and renders a blank or uncolored layer. Check column names against `dekart preview <result_file> --schema` before writing (Snowflake exports are uppercase).
