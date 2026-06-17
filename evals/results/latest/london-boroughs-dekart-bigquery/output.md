The map renders cleanly. Done.

## London Boroughs — BigQuery + Dekart

**Map:** https://cloud.dekart.xyz/reports/d0b9952b-2f9f-4f34-aa28-879fadf148c0

The snapshot shows the recognizable Greater London outline assembled from all **33 boroughs**, the Thames gap visible through the center, and a clean sequential color ramp (dark = small, yellow = large) by borough area.

### How it was built
- **Source:** `bigquery-public-data.overture_maps.division_area`
- **Boroughs are stored as** `subtype='county'`, `class='land'`, `admin_level=2` with official names (Westminster, Kensington and Chelsea, etc.). The `macrohood`/`neighborhood` "London Borough of…" entries are informal duplicates — ignored.
- **Filter:** bbox scan gate over Greater London + an explicit list of the 33 borough names (the bbox alone also catches Surrey, Kent, Essex, Herts, Bucks, Slough, Thurrock — excluded by name). No `ST_INTERSECTS` clipping needed since the boroughs *are* the selected areas.

### Validation
| Check | Result |
|---|---|
| Borough count | 33 (32 + City of London) ✓ |
| Total area | 1,577 km² (Greater London ≈ 1,572 km²) ✓ |
| Smallest | City of London, 2.5 km² ✓ |
| Largest | Bromley, 149.7 km² ✓ |
| Query cost | ~21 KB scanned |

### Styling
GeoJSON choropleth, color by `area_km2` (quantize, Sunset palette), 0.5px white hairline borders, light basemap, view locked to zoom 9.4 on central London. Tooltips show borough name + area.

**IDs:** report `d0b9952b-2f9f-4f34-aa28-879fadf148c0` · dataset `5dc829e6-88b7-4bd8-bb01-c5b4c9c10363` · query `26460e3a-931a-47d7-96ed-328cd43e5d33`

Want me to add per-borough population or feature counts (e.g. POIs, buildings) for a more analytical encoding?
