> **Superseded.** This document used the original 90-facility dataset (later found to undercount facilities by ~4x, see `docs/robustness_checks.md`) and an inconsistently-defined "moderate" disruption scenario (fixed in the same doc). Kept in place for the audit trail. Current numbers: `docs/sentinel1_derived_results.md`.

# Phase 1 Results — Baseline & Flood-Disrupted Accessibility

**Status:** Complete except issue #5 (Sentinel-1 observed flood extent, blocked on manual NASA Earthdata auth).
**Region:** South Kalimantan (13 kabupaten/kota). **Population:** WorldPop Indonesia 2020, clipped (~4.50M — reasonably close to official ~4.1–4.3M census figures, WorldPop's usual modest overestimate).

## Method

1. Health facilities (90: 35 hospitals, 46 clinics, 9 doctors) and classified road network (62,674 segments → 592k-node routable graph) extracted from the Geofabrik Kalimantan OSM PBF via a streaming `pyosmium` pass — see §"Data pipeline notes" below for why this replaced the originally-planned live Overpass approach.
2. Facilities snapped to the road graph (median snap distance 30m — tight, i.e. facility locations agree well with the road network).
3. Baseline travel time computed via one multi-source Dijkstra run (all facility nodes as sources) — standard efficient approach for one-to-many accessibility, avoids per-population-point shortest-path queries.
4. Flood disruption applied via the BNPB InaRISK hazard-classification raster (georeferenced + color-classified from the rendered MapServer output — see PROTOCOL.md §6 caveat: this is a **general multi-year hazard zone**, not the observed Jan 2021 flood footprint). Two brackets:
   - **Severe:** all medium+high hazard edges removed (treated as impassable)
   - **Moderate:** only high-hazard edges removed; medium-hazard edges penalized 2.5× travel time rather than removed
5. Population raster aggregated to ~1km cells (sum-resampled, preserves total population), snapped to nearest graph node via KD-tree, travel time looked up per scenario.

## Results

| Scenario | Any road access | Within 30 min | Within 60 min | Within 120 min | Fully disconnected |
|---|---|---|---|---|---|
| **Baseline** | 83.6% | 64.8% | 78.4% | 83.0% | 16.4% |
| **Flood — moderate** | 44.2% | 31.0% | 39.5% | 43.6% | 55.8% |
| **Flood — severe** | 26.0% | 14.8% | 21.6% | 25.1% | 74.0% |

Baseline network-fragmentation check: even in undisrupted conditions, 16.4% of population has no road-network path to any facility at all in the graph as built (likely a mix of genuinely remote areas and OSM road-network gaps — see limitations).

## Reading these numbers honestly

The disrupted-scenario magnitudes are dramatic — including in the "moderate" bracket, which only removes 10% of edges (high-hazard only) yet disconnects 56% of population from any facility. Two things are going on, and they should not be conflated:

1. **A real, interesting finding:** road networks are disproportionately vulnerable to losing a small number of chokepoint/bridge segments — cutting 10% of edges can fragment a majority of the population if those edges happen to be critical connectors. This is a well-documented property of transport networks generally, and plausible here given South Kalimantan's population and road network are concentrated in the low-lying Barito river delta (the same reason the real Jan 2021 flood was so severe).
2. **A methodology artifact to fix before claiming anything about the actual 2021 event:** this is disruption against the *general multi-year hazard-risk zone*, not the *observed extent of the Jan 2021 flood*. BNPB reported the real event affected 633K of ~4.1M people (~15%) — nowhere near 56–74% disconnected. The hazard layer covers a much larger area than any single flood event actually inundates, and binary edge removal doesn't model partial/temporary disruption (informal detours, 4WD/boat access, receding water over the event's multi-week timeline).

**Bottom line: these are legitimate baseline and sensitivity-bound results, not yet a validated claim about the January 2021 flood specifically.** That claim requires substituting Sentinel-1 SAR observed extent for the actual event (issue #5) in place of the hazard-layer proxy used here.

## Data pipeline notes (for anyone rerunning this)

- Live Overpass queries for the full province `drive` network network OOM'd during graph post-processing (`largest_component`) even after fixing the earlier query-splitting issue — province-scale "every residential street" graphs are too large for this environment's available memory.
- GDAL's built-in OSM driver (`pyogrio`/`fiona` reading `.osm.pbf` directly) hit "Cannot read node" / mid-file parsing errors on the Kalimantan extract under both default and disk-based indexing — a known class of issue with GDAL's OSM driver on larger files.
- `pyosmium` (streaming, bounded memory) worked cleanly and is now the primary extraction path (`src/01c_extract_with_osmium.py`). `src/01_fetch_osm_data.py` (osmnx/Overpass) and `src/01b_extract_from_geofabrik.py` (GDAL OSM driver) are kept for reference/comparison but are not the path actually used.
- WorldPop's server doesn't support HTTP range requests — no partial/windowed remote read possible; the full ~1GB file must be downloaded before clipping.
- BNPB's `layer_bahaya_banjir_30` MapServer only exposes a *rendered* RGBA raster (no ImageServer/raw-value endpoint found), so hazard class was reverse-engineered from pixel color — a coarse 3-bin approximation, not authoritative classification values.

## Known limitations / next steps

- 90 facilities is likely an undercount — the extraction only captured point-mapped facilities; building-outline/multipolygon-relation-mapped campuses (common for larger hospitals) weren't resolved. An earlier live-Overpass count found 76 hospital + 275 clinic/health-centre *tagged features* province-wide (nodes+ways combined) vs. 90 total here — refining this is a reasonable follow-up, not a blocker for Phase 1's baseline conclusions.
- 16.4% baseline disconnection rate should be sanity-checked against whether it reflects genuinely remote populations or road-network gaps in OSM for rural Kalsel.
- Phase 2 (district-level capacity weighting) and the Sentinel-1 substitution (issue #5) are the two concrete next steps.
