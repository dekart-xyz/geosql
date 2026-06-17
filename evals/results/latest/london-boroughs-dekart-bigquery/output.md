The map renders correctly — all 33 Greater London boroughs as a clean choropleth in the familiar London outline, with the Thames visible cutting through. Color encodes borough area: dark purple = small inner boroughs (City of London, Kensington & Chelsea, Islington), yellow = large outer boroughs (Bromley, Havering, Hillingdon).

## London Boroughs — done

**Map:** https://cloud.dekart.xyz/reports/27265ab6-88fe-495c-b01d-e49cf055d0a5

**Source:** `bigquery-public-data.overture_maps.division_area` (subtype `county`, country `GB`), constrained to the 33 Greater London boroughs.

**Approach**
- Discovered that London boroughs are stored as `subtype = 'county'` in Overture (not a "region"). The Greater London bbox also catches 7 neighbouring counties (Essex, Kent, Surrey, etc.), so I filtered to the exact 33-borough name list.
- Scan gate: hardcoded London bbox (`-0.51..0.33`, `51.28..51.69`) for partition pruning.

**Validation (all in SQL)**
- Count: **33 boroughs** (32 + City of London) ✓
- Total area: **1,577 km²** — matches Greater London's ~1,572 km² ✓
- Range: City of London smallest at **2.5 km²**, largest **149.7 km²** ✓
- Snapshot inspected: correct shape, Thames visible, hairline borders, sequential Sunset palette.

**Styling:** GeoJSON choropleth, color = `area_km2` (quantile, Sunset sequential), muted basemap, 0.5px white borders, view locked to city scale.

IDs: report `27265ab6-88fe-495c-b01d-e49cf055d0a5`, dataset `27b1ad51-005f-4b24-9d1e-b4828f600931`.

Want me to add population or population-density data for a more meaningful choropleth, or extrude boroughs in 3D by a second metric?
