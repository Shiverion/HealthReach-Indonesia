# Sentinel-1-Derived Results — Real Observed Flood Extent (Jan 2021 Event)

**Vocabulary note:** this document uses *derived* (computed from Sentinel-1 data) and *sanity-checked* (agrees qualitatively with known geography) deliberately, not *validated* (which would require comparison against an independent flood product — Copernicus EMS, UNOSAT, or similar — not yet done). See `docs/robustness_checks.md` for the full reasoning.

**Status:** Complete, and corrected after review — see `docs/robustness_checks.md` for the three fixes applied (facility completeness 90→365, proxy-moderate scenario definition, chokepoint bridge-artifact audit) and why they mattered. This document reflects the corrected numbers; it supersedes the first-draft figures that circulated briefly before review.

This supersedes the interim BNPB hazard-zone proxy as the primary finding for the actual January 2021 event; `docs/phase1_summary.md` and `docs/phase2_summary.md` are kept for methodological transparency (how the picture looked with the proxy, and why the proxy-vs-observed comparison is itself a result — see `docs/manuscript.md` §5.1).

## Method

1. Sentinel-1 GRD pair (VV polarization): baseline Dec 15, 2020 and event Jan 20, 2021, same relative orbit, footprints matching almost exactly.
2. Raw GRD georeferenced via embedded ground control points (no direct affine transform on raw GRD products), cropped to the flood-affected AOI.
3. Water classified per-scene via Otsu thresholding on log-scaled backscatter intensity.
4. New flood extent = event water AND NOT baseline water.
5. **Visually sanity-checked:** flooding tracks the Barito river corridor and concentrates near the delta/city area; the mountainous Meratus range shows negligible flooded area.
6. Two disruption brackets, defined identically in *operation* to the proxy brackets in `src/06_flood_disruption.py` (fixed per `docs/robustness_checks.md` §2):
   - **Severe:** flooded road segments removed (impassable)
   - **Moderate:** flooded segments penalized 5× travel time, nothing removed — connectivity unchanged from baseline by construction

## Headline numbers (corrected, 365-facility dataset)

| Scenario | Any road access | Within 30min | Within 60min | Within 120min |
|---|---|---|---|---|
| Baseline | 83.6% | 75.3% | 81.0% | 83.4% |
| **Sentinel-1 moderate** (realistic) | 83.6% | 71.0% | 79.4% | 82.8% |
| Sentinel-1 severe (impassable, stress test) | 6.0% | 3.9% | 5.2% | 5.8% |

**Read the moderate scenario as the primary real-world estimate.** A measured, modest impact (75.3%→71.0% within 30min, a 4.3pp drop) — plausible in scale for a serious but not catastrophic-for-everyone event, consistent with BNPB's reported ~15% of population directly affected. The severe scenario remains a legitimate network-fragility stress test (see below) but is not a literal population-affected claim — real floods have informal resilience mechanisms (boats, wading, temporary detours) a binary edge-deletion graph model cannot represent.

## Chokepoint finding — now audited, not just observed

The severe scenario disconnects more of the population (94.0%) than the equivalent proxy-based severe scenario (74.0%) despite affecting fewer roads (9.94% of edges vs. 17.3%). This pattern is unchanged by the facility-completeness fix, since it depends only on road-network topology, not on facility count.

**Audited against the specific artifact risk that this could be a SAR/bridge overlay error** (water detected under a bridge deck that remains physically dry and passable): of the 734 significant-road-class (trunk/primary/secondary/tertiary) edges that are both flooded and graph-theoretic chokepoints, only 9.8% (12/122 matched source ways) are OSM-tagged as bridges. Full audit in `docs/robustness_checks.md` §3. This is reassuring for the finding but doesn't fully rule out under-tagged bridges in this region's OSM data — stated as an open caveat, not resolved.

**Framed at the appropriate confidence level for n=1 event:** the observed pattern is consistent with a general network-topology mechanism (which specific links fail matters more to connectivity than how many or how much area is affected) but this is one flood in one province — evidence consistent with the mechanism, not a demonstrated general finding. Replication across additional flood events/regions would be needed to claim generality.

## Inequality by district capacity — confirmed, confound resolved

| Capacity class | Baseline within 60min | Observed (moderate) within 60min | pp change |
|---|---|---|---|
| Underserved | 72.8% | 70.0% | **−2.8pp** |
| Well-served | 90.0% | 89.5% | −0.4pp |

Underserved districts start from a substantially worse baseline (a standalone chronic-inequality finding) and lose disproportionately more access under real flood disruption — underserved districts lose roughly 6.5× the access, proportionally, that well-served districts do. This holds cleanly at the aggregate level using observed-extent data, without needing to exclude any district. Kota Banjarmasin (the confound with the hazard-zone proxy, where its total collapse flipped the aggregate) shows a **0.0pp change** with real data — the actual flood didn't hit its specific connecting roads the way the broad hazard-risk zone assumed it would.

**Note on the severe bracket specifically:** at the severe (binary-impassable) setting, the aggregate reverses (well-served districts show a larger pp drop, 83.3 vs. 69.1), because several well-served districts (Hulu Sungai Tengah, Kota Banjarbaru, Hulu Sungai Selatan, Balangan) happen to collapse to near-zero access under full edge removal. This reversal is specific to the unrealistic severe bracket; the moderate bracket (the primary real-world estimate) shows the expected pattern cleanly. Read this as a further reason to treat severe as a stress test, not a headline number.

**Sharpest single data point:** Barito Kuala — the lowest-capacity district in the province (24.6 clinical staff per 10k) — shows the single largest access drop of any district (−10.2pp, 88.7%→78.5%), followed by Banjar (−4.1pp). Both are underserved districts.

Full per-kabupaten table: `data/processed/inequality_per_kabupaten.csv`.

## What this means for the eventual write-up

The proxy-vs-real comparison across Phase 1/2 is a worthwhile methodological point independent of magnitude corrections: a general hazard-risk layer both overstates uniform disruption (confounding the inequality analysis via Banjarmasin) and misses the chokepoint-concentration effect that makes a real, geographically-specific flood more network-disruptive than its area coverage alone would suggest.

## Remaining known limitations

- Binary/penalty disruption modeling still doesn't capture real-world adaptive behavior. See `docs/robustness_checks.md` and `docs/manuscript.md` §5.2 for the fuller limitations list (SAR processing rigor, temporal mismatch across data sources, facility-vs-district capacity granularity).
- If this becomes a real research output, refining the disruption model (partial-capacity edges scaled by estimated flood depth, rather than binary flooded/not-flooded) is the natural next methodological step.
