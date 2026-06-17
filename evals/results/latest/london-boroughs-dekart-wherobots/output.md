The map renders correctly — the classic Greater London silhouette with all 33 boroughs as a choropleth, Thames visible through the center.

## London Boroughs — done ✅

Built from **Overture Maps `divisions_division_area`** via the **Wherobots** connector in Dekart query mode.

**Map:** https://cloud.dekart.xyz/reports/b2671c9c-831f-4e39-9232-ccc6bc7e6d86

**What the map shows:** the inner boroughs are small and dark (City of London 2.5 km², Kensington & Chelsea, Islington), fanning out to the large yellow outer boroughs (Bromley 150 km², Hillingdon, Havering). The Sunset palette + dark basemap makes the radial size gradient and the Thames corridor immediately readable.

**How I got the boroughs cleanly:**
- There's no "Greater London" region in Overture (the only `region` polygon is *England*), and the `county` subtype mixes the 33 boroughs with neighboring counties (Essex, Kent, Surrey, Hertfordshire, Buckinghamshire, Slough, Thurrock).
- So I scanned the London bbox, listed the `county` names, and filtered to the 33 actual boroughs (32 + City of London) by name.

**Validation (in SQL):**
| metric | value | sanity |
|---|---|---|
| boroughs | 33 | ✓ 32 + City of London |
| total area | 1,583.3 km² | ✓ Greater London ≈ 1,572 km² |
| largest | 150.2 km² | ✓ Bromley |
| smallest | 2.51 km² | ✓ City of London |

**IDs:** report `b2671c9c-831f-4e39-9232-ccc6bc7e6d86` · dataset `f731a969-479d-49b2-b06f-295dffc1d092` · query `72626b80-6c6d-4ad6-accf-5848d295c9b9` · status `JOB_STATUS_DONE`.

Want me to switch the encoding to a 3D extrusion by area, or color by a different attribute?
