Done. Map of the **33 London boroughs** built from BigQuery Overture data and rendered as a choropleth in Dekart.

**Map:** https://cloud.dekart.xyz/reports/4306de5d-652b-4af5-b41f-3b59b4512d8d

### What it shows
A choropleth of all 33 London boroughs (32 boroughs + the City of London), shaded by land area (Sunset sequential palette, quantile scale). The snapshot confirms full Greater London coverage with the Thames threading through — small light-colored central boroughs (City of London, Islington, Kensington) and large dark outer boroughs (Bromley, Havering, Hillingdon).

### How it was built
- **Source:** `bigquery-public-data.overture_maps.division_area`
- **Discovery:** Boroughs are stored as `subtype='county', class='land'`, `region='GB-ENG'` with clean names (e.g. *Camden*, *Westminster*). No "Greater London" parent area exists, so I enumerated the canonical 33 borough names, gated by the Greater London bbox (overlap pattern) for cheap scan pruning.
- **Geometry note:** `geometry` is `GEOGRAPHY` (EPSG:4326), so `ST_AREA` returns m² → converted to km² (cast to `FLOAT64` for the color channel).

### Validation
| Check | Result |
|---|---|
| Borough count | **33** ✓ (32 + City of London) |
| Total area | **1,577.4 km²** ✓ (Greater London ≈ 1,572 km²) |
| Largest | Bromley, 149.7 km² ✓ |
| Smallest | City of London, 2.5 km² ✓ |
| Dry-run cost | 677 MB (under 10 GiB budget) |

### IDs
- report_id: `4306de5d-652b-4af5-b41f-3b59b4512d8d`
- map dataset_id: `8a9d19cd-07f8-4b87-9559-519902267487`
- query_id: `e63f2563-4061-4150-96fe-3ab8c0d4d530`
- job_id: `da475a17-adc3-4d0a-9b47-aa71dc178656` (JOB_STATUS_DONE)

Want me to add a 3D extrusion by area, switch the color to a metric like population/density, or add borough name labels directly on the map?
