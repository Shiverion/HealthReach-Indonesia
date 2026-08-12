# Beyond Proximity: Capacity-Stratified Healthcare Accessibility Under Flood Disruption in South Kalimantan, Indonesia

**Status: Draft v0.2.** Independent replication and extension. Repository: [HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia). Changes from v0.1 are substantive, not editorial — see `docs/robustness_checks.md` for the three issues a review pass caught and how each was resolved (facility-extraction undercount, a disruption-scenario definition bug, and a chokepoint-finding artifact audit). This version's numbers are corrected; v0.1's are not, and are kept in `docs/phase1_summary.md` / `docs/phase2_summary.md` for the audit trail rather than quietly edited away.

## Abstract

Standard geographic healthcare accessibility models treat facilities as uniform points and disasters as static hazard layers, obscuring two things that determine real-world impact: whether a district is adequately staffed to treat patients, and where a flood actually happened rather than where it merely could. We replicate the geospatial network-accessibility methodology used by Macharia et al. (Kenya, 2025 preprint) for South Kalimantan, Indonesia, and extend it in two directions: (1) a district-level healthcare workforce capacity index used to stratify accessibility results by district, and (2) validation of flood disruption against Sentinel-1 SAR-observed flood extent for the actual January 2021 South Kalimantan flood, rather than a static multi-year hazard-risk classification. Three findings, in order of how much confidence each supports: **chronic inequality** — baseline accessibility already varies by district workforce capacity (72.8% vs. 90.0% of population within 60 minutes of a facility, low- vs. high-capacity districts); **disaster amplification** — this gap widens under real flood disruption (a −2.8pp vs. −0.4pp change), visible only with observed disruption data, not a hazard-risk proxy; and, with appropriately limited confidence given a single event, **evidence consistent with** a network-topology mechanism in which which specific roads flood matters more to accessibility than how much area floods.

## 1. Introduction

Geographic accessibility to healthcare is typically modeled as a function of population, road networks, and facility locations, producing a travel-time surface used to identify underserved populations. Two simplifications are near-universal in this literature and both matter for disaster response: facilities are treated as equivalent regardless of whether they are adequately staffed, and disaster disruption is modeled using hazard-risk classifications (multi-year probabilistic risk zones) rather than the actual extent of a specific event, because observed-extent data is harder to obtain and process.

This study asks: for a specific flood event in a specific place, how much does each simplification matter, and does correcting for them change which populations are identified as most affected?

South Kalimantan, Indonesia is a strong setting for this question. It experienced a well-documented, severe flood in January 2021 (BNPB: 10 of 13 kabupaten/kota affected, 46 deaths, 633,273 people affected) with real ground-truth impact data to validate against, sits on a river delta where population and infrastructure concentrate on flood-prone lowlands, and has open data across the layers this analysis needs.

## 2. Related work and positioning

**Primary reproduction target:** Macharia et al., *"Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya"* (Research Square preprint, 2025) — establishes the baseline-vs-disrupted geographic accessibility methodology this study reproduces.

**Prior art in Indonesia, explicitly acknowledged:** HeiGIT's *Flood Impact Assessment on Road Network and Healthcare Access... Jakarta, Indonesia* (AGILE-GISS, 2021) applies the same genre of analysis to the 2013 Jakarta flood. This study's contribution is not "the first accessibility study in Indonesia" but the combination of a new region and event, capacity stratification, and event-specific Sentinel-1-derived disruption modeling, compared directly against the more commonly-used hazard-proxy approach under matched conditions (§3.6, §5.1).

## 3. Data and methods

### 3.1 Study area and event

South Kalimantan province, 13 kabupaten/kota. Disruption event: the January 2021 flood, BNPB-documented across 10 of the 13 districts.

### 3.2 Data sources and their temporal alignment

| Layer | Source | Reference date |
|---|---|---|
| Health facilities | OpenStreetMap (Geofabrik Kalimantan extract) | current snapshot (2026) |
| Road network | Same OSM extract | current snapshot (2026) |
| Population | WorldPop Indonesia | 2020 |
| Flood event | Sentinel-1 SAR, BNPB reports | January 2021 |
| District workforce | Dinkes Kalsel *Profil Kesehatan* | 2022 |

**This table makes a real limitation visible rather than hiding it: the road/facility network is a current (2026) OSM snapshot, not a January-2021 snapshot.** WorldPop 2020 against a January 2021 flood is a reasonable one-year gap. Workforce data from 2022 against a 2021 event is a defensible one-year gap given no earlier published alternative exists. The road/facility gap is larger and unaddressed here — see §5.2. The concrete remedy, not implemented in this pass, is an Overpass historical query pinned to `[date:"2021-01-20T00:00:00Z"]` in place of the current-snapshot extract, ideally as a sensitivity check against the current results rather than a full replacement.

### 3.3 Health facility extraction

365 facilities (75 hospitals, 263 clinics, 21 doctors, 3 dentists, 3 unnamed) via `osmium`'s two-pass multipolygon/relation area assembly (`src/12_extract_facilities_complete.py`), filtered to care-providing categories matching the official Kemenkes/BNPB scope (excludes standalone pharmacies), deduplicated by proximity + name matching. This corrects an earlier extraction (90 facilities) that only captured point-mapped OSM features and silently missed building/relation-mapped hospital campuses — see `docs/robustness_checks.md` §1 for the diagnosis and fix, and note the baseline median travel time changed from 13.7 to 6.8 minutes as a result. Every number in this manuscript uses the corrected 365-facility dataset.

### 3.4 Baseline accessibility model

Standard population → road network → facility travel-time model. Roads assigned free-flow speeds by class (20–80 km/h). Travel time from every road-network node to the nearest facility computed via a single multi-source Dijkstra run (all facility-matched graph nodes as simultaneous sources). Population aggregated to ~1km cells (sum-resampled) and snapped to the nearest graph node via KD-tree for the population-weighted summary.

### 3.5 District capacity index

Following the WHO SDG 3.c.1 convention (physicians + nursing/midwifery personnel per 10,000 population), a clinical-staff density index was computed per kabupaten from doctors, nurses, and midwives (Tabel 13–14 of the Profil Kesehatan document), divided by WorldPop population zonal-summed to kabupaten boundaries. Districts were split at the province median into "underserved" and "well-served" classes.

**A framing clarification, stated explicitly rather than left implicit:** this index is used to *stratify* the accessibility results — computing them separately for low- and high-capacity districts and comparing — not to *integrate* capacity into the accessibility function itself. A 500-staff hospital and a 3-staff clinic are still treated identically as "the nearest facility" in the travel-time model; capacity does not change which facility is selected as nearest or how far away it counts as accessible. This is a capacity-*stratified* accessibility analysis, not a capacity-*weighted* one in the sense of a joint model like 2SFCA or a gravity-based supply-demand formulation, which would require facility-level (not district-level) workforce data this project does not have. We did not fabricate a facility-level proxy to make the model appear more sophisticated than the data supports; the title and framing throughout reflect stratification, and a genuine capacity-integrated model (e.g., Enhanced 2SFCA) is noted as future work in §5.2, contingent on facility-level data becoming available.

### 3.6 Flood disruption modeling: proxy vs. observed

Two disruption layers were used deliberately, so the comparison itself is part of the result.

**Proxy (BNPB InaRISK hazard classification).** BNPB's flood-hazard MapServer exposes only a rendered RGBA raster, reverse-engineered via color-threshold classification into three bins (low/medium/high). Represents flood-*prone* area accumulated over many years, not any single event's footprint.

**Observed (Sentinel-1 SAR).** A Sentinel-1 GRD pair (baseline Dec 15, 2020; event Jan 20, 2021; matched relative orbit) was warped to EPSG:4326 via embedded GCPs, cropped to the AOI, and water classified per-scene via Otsu thresholding on log-scaled VV backscatter. New flood extent = event water minus baseline water. Visually sanity-checked against known geography (river-corridor concentration, negligible flooding on the mountainous AOI edge) — this is a qualitative check, not validation against an independent flood product, which has not been performed (§5.2).

**Disruption brackets, defined identically in operation for both layers** (a fix from an earlier draft where the proxy-moderate scenario mixed edge removal and penalty inconsistently — see `docs/robustness_checks.md` §2):
- **Severe:** flagged road segments removed (impassable) — a network-fragility stress test
- **Moderate:** flagged segments penalized (×2.5 proxy / ×5 observed), nothing removed — the more realistic estimate, verified to leave graph connectivity unchanged from baseline as required by construction

## 4. Results

### 4.1 Baseline accessibility

83.6% of South Kalimantan's population has road-network access to a health facility of any kind; 75.3% within 30 minutes, 81.0% within 60 minutes, 83.4% within 120 minutes.

### 4.2 Finding 1 — Chronic inequality (pre-disaster)

| Capacity class | Baseline: within 60min |
|---|---|
| Underserved | 72.8% |
| Well-served | 90.0% |

Districts with below-median clinical-workforce density already show substantially worse baseline accessibility, independent of any flooding. This is the least surprising of the three findings and the one supported with the most confidence — it does not depend on any disruption-modeling choice.

### 4.3 Finding 2 — Disaster amplification, visible only with observed data

| Scenario | Any access | Within 30min | Within 60min | Within 120min |
|---|---|---|---|---|
| Baseline | 83.6% | 75.3% | 81.0% | 83.4% |
| Sentinel-1 — moderate (primary estimate) | 83.6% | 71.0% | 79.4% | 82.8% |
| Sentinel-1 — severe (stress test) | 6.0% | 3.9% | 5.2% | 5.8% |

| Capacity class | Baseline within 60min | Observed-moderate within 60min | pp change |
|---|---|---|---|
| Underserved | 72.8% | 70.0% | **−2.8pp** |
| Well-served | 90.0% | 89.5% | −0.4pp |

Underserved districts lose roughly 6.5× the proportional access that well-served districts do under the real flood. This holds cleanly at the aggregate level with observed data. It did **not** hold cleanly with the hazard-zone proxy: there, Kota Banjarmasin — highest workforce capacity in the province (56.1 staff/10k) but also the most flood-exposed district geographically (the low-lying delta capital) — collapsed entirely under the proxy's blanket hazard coverage and flipped the population-weighted aggregate. With observed extent, Banjarmasin shows a **0.0pp change** (its specific connecting roads were not, in fact, part of the actual flooded footprint), and the inequality result holds without excluding anything. This is itself evidence that observed-extent validation matters for whether an inequality claim survives scrutiny, not only for precision.

**Note on the severe bracket specifically:** at full edge removal, the aggregate reverses (well-served districts show a larger pp drop, 83.3 vs. 69.1) because several well-served districts collapse to near-zero access under that unrealistic setting. Read this as further reason the severe bracket is a stress test, not a headline number — the moderate bracket is where the inequality finding should be read.

**Sharpest single data point:** Barito Kuala, the lowest-capacity district in the province, shows the largest access drop of any district (−10.2pp, 88.7%→78.5%), followed by Banjar (−4.1pp) — both underserved, both adjacent to the low-lying delta.

### 4.4 Finding 3 — Evidence consistent with a network-topology mechanism (n=1, stated at appropriate confidence)

The observed-extent severe scenario disconnects more of the population (94.0%) than the proxy-based severe scenario (74.0%) despite affecting fewer roads (9.94% of edges vs. 17.3%). Real flood water concentrates on river corridors; roads cross rivers at a comparatively small number of structural chokepoints. A hazard-risk proxy, more diffusely distributed, removes more edges overall but hits fewer *critical* ones.

**Audited against an alternative explanation:** this pattern could in principle be a SAR/vector-overlay artifact — a bridge deck detected as "flooded" because SAR sees water underneath it while the deck itself stays dry and passable. Of the 734 significant-road-class edges that are both flooded and graph-theoretic chokepoints (edges whose removal alone disconnects part of the network), only 9.8% (12 of 122 matched source ways) are OSM-tagged as bridges — reassuring against the artifact explanation, though incomplete OSM bridge-tagging in this region means under-tagged real bridges cannot be fully ruled out without imagery-based verification, which was not performed. Full audit: `docs/robustness_checks.md` §3.

**Confidence level, stated explicitly:** this is one flood event in one province. The result is evidence consistent with a general network-topology mechanism — that accessibility disruption is determined more by the structural importance of affected links than by the total number or area of affected roads — not a demonstrated general empirical finding. Establishing generality would require replication across additional flood events and network topologies, which this study does not attempt.

## 5. Discussion

### 5.1 Robustness: what changed between proxy and observed data, and why it matters

Both disruption layers agree on direction but disagree on magnitude and, critically, on which specific districts appear most affected. The proxy's Banjarmasin confound (§4.3) demonstrates that a hazard-risk layer is not a safe substitute for observed extent even for *directional* inequality claims, not merely for precise magnitudes. This comparison — not the capacity stratification — is this project's most defensible methodological contribution; see §5.3.

### 5.2 Limitations

- **Facility completeness, partially addressed.** The original 90-facility extraction undercounted by roughly 4x (fixed, see §3.3), but the corrected 365 may still not be complete or fully deduplicated; no independent ground-truth facility census was used to validate the final count beyond cross-checking province-wide OSM tag totals.
- **District-, not facility-level, capacity.** Facility-level workforce data is not public in South Kalimantan; the capacity index is a district average and cannot distinguish a well-staffed hospital from an understaffed one within the same kabupaten. The methodology is capacity-*stratified*, not capacity-*integrated* — see §3.5.
- **Temporal mismatch across data layers.** Road/facility network reflects a current (2026) OSM snapshot applied to a January 2021 event; not addressed with a historical-snapshot sensitivity check in this pass (concrete remedy noted in §3.2).
- **SAR processing rigor.** Water classification uses per-image Otsu thresholding on raw (uncalibrated) VV backscatter intensity — adequate for isolating a bimodal low/high-backscatter split within one image, but does not include radiometric calibration to sigma0, speckle filtering, terrain correction, a permanent-water mask from an external product, connected-component filtering to remove speckle-scale false positives, VV+VH combination, or validation against an independent observed-flood product. Appropriate for exploratory event mapping; a remote-sensing reviewer would reasonably ask for these before treating the flood extent as publication-grade. Single before/after pair, not a dense time series — flood extent may have differed at other points in the multi-week event.
- **Binary/penalty disruption modeling.** Neither "removed" nor "penalized" fully captures real-world adaptive behavior (informal water transport, wading, temporary detours). The true population-affected figure likely sits closer to the moderate bracket than the severe one, but this is a qualitative judgment, not something the current model quantifies directly.
- **Bridge-artifact audit is reassuring, not conclusive.** See §4.4 — OSM bridge-tagging completeness in this region is an open uncertainty.
- **Preprint status.** The primary reproduction target (Macharia et al.) was a preprint as of this analysis; peer-reviewed status should be re-checked before final citation.

### 5.3 Contribution

Relative to the reproduced methodology: (1) a district-level capacity-stratified view of accessibility, explicitly scoped as stratification rather than a claim of capacity-integrated modeling; (2) a matched-conditions comparison between hazard-proxy and observed-extent disruption modeling for the same event (same population, facilities, network, and penalty multipliers — only the flood representation differs), showing the proxy approach systematically overstates inequality-widening relative to observed data across every multiplier tested, which is this project's cleanest and most defensible result; (3) evidence, appropriately hedged for a single case, consistent with a network-topology mechanism where chokepoint concentration matters more than areal extent, audited against a specific plausible artifact explanation and an edge-overlap-rule sensitivity check, both of which it survives.

## 6. Data and code availability

All data pipeline code, intermediate outputs, and this manuscript are at [github.com/Shiverion/HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia). Raw bulk downloads are not committed (see `.gitignore`) but reproducible from `src/`, which documents exact source URLs and access methods, including dead ends left in place as methodological notes: live Overpass API instability, GDAL OSM-driver parsing bugs, a corrupted PDF text layer, two rounds of mislocated Sentinel-1 scene selection, an under-scoped facility extraction, and an inconsistently-defined disruption scenario — see `docs/robustness_checks.md` for the last two.

## References

- Macharia, P.M. et al. *Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya.* Research Square preprint, 2025.
- Macharia, P.M. et al. *Geographic accessibility to public and private health facilities in Kenya in 2021: An updated geocoded inventory and spatial analysis.* PMC9670107, 2023.
- HeiGIT. *Flood Impact Assessment on Road Network and Healthcare Access at the example of Jakarta, Indonesia.* AGILE-GISS, 2021.
- BNPB (Badan Nasional Penanggulangan Bencana). Situation reports, January 2021 South Kalimantan floods.
- Dinas Kesehatan Provinsi Kalimantan Selatan. *Profil Kesehatan Provinsi Kalimantan Selatan Tahun 2022.*
- WHO. SDG Indicator 3.c.1: Health worker density and distribution.
