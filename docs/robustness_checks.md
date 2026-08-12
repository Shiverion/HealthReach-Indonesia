# Robustness Checks and Fixes

Three issues were raised in review after the initial results were drafted. All three were substantive, not stylistic — this document records what was checked, what was found, and what changed. Consistent with this project's practice of keeping dead ends visible (see `docs/phase1_summary.md`, `docs/sentinel1_validated_results.md`) rather than quietly editing history, the original documents are left in place with a note pointing here; this document is the corrected account.

## 1. Facility completeness: 90 → 365

**The concern:** the original facility extraction (`src/01c_extract_with_osmium.py`) only captured point-mapped OSM facilities. An independent live-Overpass count had found 76 hospital-tagged and 275 clinic/health-centre-tagged features province-wide (nodes+ways combined) versus 90 in the dataset actually used — meaning building-outline and multipolygon-relation-mapped hospital campuses were being silently dropped. If the missing facilities were concentrated in specific areas (rural districts, say), every accessibility number in this project would be biased.

**The fix:** `src/12_extract_facilities_complete.py` properly assembles OSM multipolygon relations via `osmium.area.AreaManager`'s two-pass handler (the original extraction's `way()` callback only handled simple closed ways, which is why it silently returned zero results for relation-based facilities — most real hospital campuses are mapped as relations, not simple ways). Filtered to the same care-providing categories used throughout this project (hospital, clinic, doctors, dentist — matching the Kemenkes/BNPB scope, which explicitly excludes standalone pharmacies from its own facility counts), then deduplicated by proximity (150m) + name matching, since a single real-world facility is often represented in OSM as a point marker *and* a building outline *and* sometimes a campus relation simultaneously.

**Result: 365 facilities** (75 hospitals, 263 clinics, 21 doctors, 3 dentists, 3 unnamed), close to the ~250–350 range estimated from the independent Overpass count. Old file kept as `data/raw/facilities/kalsel_facilities_nodes_only.geojson` for the audit trail.

**Impact on results:** substantial, as expected. Baseline median travel time to the nearest facility dropped from 13.7 to 6.8 minutes. **All downstream numbers in this project (baseline, both disruption layers, inequality analysis) have been recomputed with the corrected facility set** — see `docs/sentinel1_validated_results.md` for the updated figures. The direction of every qualitative finding (chronic inequality, disaster amplification, Barito Kuala as the sharpest case, the proxy-vs-observed Banjarmasin confound) survived the correction; the magnitudes changed and are now more defensible.

## 2. Proxy-moderate scenario: definition/reporting inconsistency

**The concern:** the proxy "moderate" scenario was described in early drafts as penalizing flooded roads (slower, not impassable), yet its reported numbers showed a large "any access" drop (83.6%→44.2%) — which is only possible if edges were actually being *removed*, not merely slowed. That's a real inconsistency: a pure-penalty scenario cannot change graph connectivity, full stop.

**Root cause:** the original ad-hoc "moderate" computation removed high-hazard edges outright *and* penalized medium-hazard edges — a mixed operation — but was described in prose as if it were penalty-only. The math wasn't wrong; the description was.

**The fix:** `src/06_flood_disruption.py` and `src/11_flood_disruption_sentinel1.py` now define moderate identically in *operation* for both the proxy and Sentinel-1 layers: penalize all flagged edges (2.5× for proxy, 5× for observed), remove nothing. Verified directly: post-fix, the moderate scenario's largest connected component is 100.0% of the original graph with zero stranded nodes, exactly as graph theory requires. Severe (full removal) is unchanged and is the correct scenario for the earlier "any access" collapse.

This also makes the proxy-vs-observed comparison (the project's cleanest contribution — see `docs/manuscript.md` §5.1) genuinely apples-to-apples, which it was not before.

## 3. Chokepoint finding: bridge-artifact audit

**The concern:** SAR can detect water underneath a bridge deck while the deck itself remains dry and passable; if OSM's road vector for that bridge crosses the same pixel, a naive raster-vector overlay would falsely flag a passable bridge as flooded. If this happened at scale, it would mean the "real floods hit network chokepoints harder than their area coverage suggests" finding was partly a GIS artifact rather than a real effect.

**The audit:** graph-theoretic bridge edges (`networkx.bridges()` — edges whose removal alone disconnects part of the network; 157,073 of 562,990 total edges, 27.9%) were intersected with the Sentinel-1 flooded-edge set, restricted to significant road classes (trunk/primary/secondary/tertiary, excluding residential cul-de-sacs which dominate the raw chokepoint count but are mostly minor dead-ends). This gave 734 significant flooded chokepoint edges, matched back to 122 unique source OSM ways, whose `bridge` tag was then checked directly against the OSM data.

**Result: only 12/122 (9.8%) are OSM-tagged `bridge=yes`.** This is reassuring for the finding — the physical-bridge-artifact scenario is not the dominant explanation, since the large majority of flagged chokepoints aren't tagged as bridges at all. Several of the non-bridge flagged roads are literally named after the rivers they run alongside (e.g. `Jalan Sungai Kusan` — "Kusan River Road"), consistent with genuine riverside road inundation rather than overlay error.

**Honest residual caveat:** OSM bridge-tagging completeness in rural Indonesia is inconsistent (a known general data-quality pattern, not specific to this check), so under-tagged real bridges among the 90.2% non-bridge-tagged set cannot be fully ruled out without imagery-based manual verification, which was not performed exhaustively here. This is flagged as follow-up work, not resolved.

## What this means for the write-up

All three issues are addressed, not merely acknowledged: facilities were re-extracted and every downstream number recomputed; the proxy-moderate scenario was fixed and re-verified against graph theory directly; the chokepoint finding was audited against an alternative artifact explanation and found to survive it, with the residual uncertainty stated plainly rather than glossed over.
