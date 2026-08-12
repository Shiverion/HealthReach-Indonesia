# Beyond Proximity: Capacity-Stratified Healthcare Accessibility Under Flood Disruption in South Kalimantan, Indonesia

**Status: Draft v0.3.** Independent replication and extension. Repository: [HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia). Two rounds of review changed this draft substantively, not editorially — see `docs/robustness_checks.md`. The first round fixed outright errors (a 4x facility undercount, a disruption-scenario definition bug). The second round ran a set of sensitivity checks against claims that were individually defensible but not yet earned at the confidence level they were stated with; most held up or got stronger (§4.2, §4.3), but one — the "network-topology chokepoint" mechanism originally proposed in Finding 3 — was strongly contradicted by a randomization test and is reported here as a retraction, not rescued or reframed. v0.1/v0.2 numbers are superseded and kept in `docs/phase1_summary.md` / `docs/phase2_summary.md` for the audit trail.

## Abstract

Standard geographic healthcare accessibility models treat facilities as uniform points and disasters as static hazard layers, obscuring two things that determine real-world impact: whether a district is adequately staffed to treat patients, and where a flood actually happened rather than where it merely could. We replicate the geospatial network-accessibility methodology used by Macharia et al. (Kenya, 2025 preprint) for South Kalimantan, Indonesia, and extend it in two directions: (1) a district-level healthcare workforce capacity index used to stratify accessibility results by district, and (2) validation of flood disruption against Sentinel-1 SAR-observed flood extent for the actual January 2021 South Kalimantan flood, rather than a static multi-year hazard-risk classification. Two findings and one retraction, in order of how much confidence each supports: **chronic inequality** — baseline accessibility already varies by district workforce capacity (72.8% vs. 90.0% of population within 60 minutes of a facility, low- vs. high-capacity districts); **disaster amplification** — this gap widens under flood disruption regardless of which disruption layer is used (from 17.2pp to 19.6pp under observed data, a widening of +2.4pp computed from unrounded values), but a hazard-risk proxy systematically overstates that widening by 1.7–2.6× across every penalty setting tested — a controlled sensitivity sweep, not a single arbitrary comparison, so the contribution here is about magnitude and which districts appear most affected, not about direction; and a **retracted mechanism** — an initial finding that real flood damage concentrates on structurally important network "chokepoints" did not survive a randomization test (not one of 200 random-edge-removal trials was as mild as the real flood's actual pattern, the opposite of what the chokepoint hypothesis predicted, empirical p≈0.005 for the correctly-specified direction) and is reported here as withdrawn rather than salvaged.

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

### 4.3 Finding 2 — Disaster amplification, magnitude depends on disruption representation

| Scenario | Any access | Within 30min | Within 60min | Within 120min |
|---|---|---|---|---|
| Baseline | 83.6% | 75.3% | 81.0% | 83.4% |
| Sentinel-1 — moderate (primary estimate) | 83.6% | 71.0% | 79.4% | 82.8% |
| Sentinel-1 — severe (stress test) | 6.0% | 3.9% | 5.2% | 5.8% |

| Capacity class | Baseline within 60min | Observed-moderate within 60min | pp change |
|---|---|---|---|
| Underserved | 72.8% | 70.0% | **−2.8pp** |
| Well-served | 90.0% | 89.5% | −0.4pp |

The chronic 17.2pp gap widens to 19.6pp under real flood disruption — **a widening of +2.4pp** (computed from unrounded values; the rounded display figures above give +2.3pp). This is the more honest headline than a ratio of the two class-level drops (−2.8pp underserved vs. −0.4pp well-served): dividing those two produces a dramatic-sounding multiple mostly because the well-served denominator is small, exactly the kind of statistic that shouldn't be trusted at face value. The pp-gap framing survives that critique.

**This holds cleanly at the aggregate level with observed data, at the moderate (realistic) setting — and, per the matched-penalty sweep below, so does the proxy, at every multiplier tested. Both disruption layers show the gap widening; direction is not what distinguishes them.** What distinguishes them is magnitude, and one specific bracket: at the **severe** (binary-removal) setting only, the proxy's aggregate reverses outright — Kota Banjarmasin, highest workforce capacity in the province (56.1 staff/10k) but also the most flood-exposed district geographically, collapses entirely under the proxy's blanket hazard coverage and flips the population-weighted aggregate. With observed extent, Banjarmasin shows a **0.0pp change** even at the severe setting (its specific connecting roads were not, in fact, part of the actual flooded footprint). So: proxy vs. observed does not change *whether* the gap widens (both do, at realistic settings) — it changes *by how much* (1.7–2.6×, see below) and, at the unrealistic severe setting specifically, it can change which districts appear most affected entirely.

**Robustness, checked rather than assumed:** a matched-penalty sweep (proxy and observed disruption run at identical multipliers ×2/×2.5/×5/×10, not the mismatched ×2.5/×5 used above) confirms both layers widen the gap at every multiplier — 8/8 scenarios positive, none reversed — with the proxy overstating the widening by 1.7–2.6× at every setting (`docs/robustness_checks.md` §4). A leave-one-district-out check preserved the widening direction in 13/13 runs (range +1.10pp to +2.93pp), and a workforce-denominator sensitivity check (WorldPop 2020 vs. the source document's own matched-year 2022 population) left the aggregate finding essentially unchanged (+2.37pp → +2.30pp) despite 2 of 13 districts flipping capacity classification. Full detail: `docs/robustness_checks.md` §4, §6.

**Note on the severe bracket specifically:** at full edge removal, the aggregate reverses (well-served districts show a larger pp drop, 83.3 vs. 69.1) because several well-served districts collapse to near-zero access under that unrealistic setting. Read this as further reason the severe bracket is a stress test, not a headline number — the moderate bracket is where the inequality finding should be read.

**Sharpest single data point:** Barito Kuala, the lowest-capacity district in the province, shows the largest access drop of any district (−10.2pp, 88.7%→78.5%), followed by Banjar (−4.1pp) — both underserved, both adjacent to the low-lying delta.

### 4.4 Finding 3, revised — a robust empirical gap, a retracted mechanism

The observed-extent severe scenario disconnects more of the population (94.0%) than the proxy-based severe scenario (74.0%) despite affecting fewer roads (9.94% of edges vs. 17.3%). **This specific comparison is a fact and is unaffected by what follows.**

**The mechanism originally proposed to explain it does not survive testing, and is withdrawn rather than reframed.** The initial draft of this finding attributed the pattern to a network-topology "chokepoint" effect: real flood water concentrates on river corridors, and roads cross rivers at a comparatively small number of structurally critical links, so a smaller set of affected edges could still cause more damage than a larger, more diffuse one. Two checks were run against this claim. The first, a bridge-tagging audit (734 significant-road-class edges that are both flooded and graph-theoretic chokepoints, matched to 122 source OSM ways), found only 9.8% tagged as bridges — reassuring against a specific *SAR-artifact* explanation (a dry bridge deck misread as flooded), and that narrower conclusion still stands (`docs/robustness_checks.md` §3). The second check tested the chokepoint *mechanism*'s strongest testable prediction, directly: a uniform-random null model (`docs/robustness_checks.md` §7) removed the same number of edges (55,983) chosen uniformly at random from the network, 200 times, and compared the resulting connectivity loss to the real flood's actual pattern. **Scope, stated precisely:** this tests Sentinel-1 against a random baseline, not against the proxy's own specific spatial pattern directly — sufficient to withdraw the general chokepoint claim, not sufficient to characterize every possible variant of it.

**The result strongly contradicts the chokepoint hypothesis.** Not one of 200 random trials was as mild as the real flood's actual pattern (largest surviving component 1.35–4.47%, mean 3.18%, vs. the observed 9.06%). Reported at the precision the test supports: testing whether the observed flood is *more* damaging than random gives p = 1.0000 (zero support for that direction, not "100% disproven"); testing the direction the data actually show — the observed flood is *less* damaging than random — gives empirical randomization p = (0+1)/(200+1) ≈ **0.005**, a strong result under this null. One plausible explanation is that random failures are scattered across the whole province (each independently able to sever an unrelated local branch) while a real flood's damage stays geographically concentrated in one region — **but this is an untested hypothesis, not a finding**; confirming it would require a spatially-constrained null, which was not run. Asserting it as established fact here would repeat, one paragraph later, the exact kind of unearned causal claim this section exists to correct.

**A follow-up check (Null A2, `docs/robustness_checks.md` §7b) confirms this rather than complicating it.** Null A's damage metric (largest connected component) is not the same phenomenon that motivated this finding — population losing healthcare access specifically. Rerunning the identical 200-trial randomization with population-disconnected-from-any-facility as the metric instead could have diverged from Null A (generic connectivity and healthcare-specific access are not guaranteed to move together). It did not: random removal disconnects more population from facilities than the real flood by this metric too (mean 89.5% vs. observed 68.65%, empirical p≈0.005 for the correct direction, the observed value below the minimum of all 200 trials) — independent confirmation, not redundant repetition.

**Stated separately, what is retracted and what is not:**
- **Retracted:** the claim that real floods preferentially sever structurally important links better than chance would. The evidence points the opposite direction, and the "which roads flood matters more than how much" framing built on that claim is withdrawn.
- **Not retracted, and not dependent on the mechanism above:** the empirical fact that this specific flood disconnected more of the population from facilities than the proxy scenario despite fewer roads affected. No confirmed explanation is offered for this here. Plausible, unconfirmed candidates — the flood may have severed the *specific* corridor connecting the province's largest population center to its facilities (an origin-destination-specific effect, not a generic graph-theoretic one), or the two edge sets may differ in road-class composition in ways not controlled for — are noted as open questions for future work, not findings.

This is reported as a retraction because that is what the evidence supports, not reframed as a different discovery. A robustness check that disproves a claim is not a failed check.

## 5. Discussion

### 5.1 Robustness: what changed between proxy and observed data, and why it matters

Both disruption layers agree on direction but disagree on magnitude and, critically, on which specific districts appear most affected. The proxy's Banjarmasin confound (§4.3) demonstrates that a hazard-risk layer is not a safe substitute for observed extent even for *directional* inequality claims, not merely for precise magnitudes. This comparison — not the capacity stratification — is this project's most defensible methodological contribution; see §5.3.

### 5.2 Limitations

- **Facility completeness, partially addressed.** The original 90-facility extraction undercounted by roughly 4x (fixed, see §3.3), but the corrected 365 may still not be complete or fully deduplicated; no independent ground-truth facility census was used to validate the final count beyond cross-checking province-wide OSM tag totals.
- **District-, not facility-level, capacity.** Facility-level workforce data is not public in South Kalimantan; the capacity index is a district average and cannot distinguish a well-staffed hospital from an understaffed one within the same kabupaten. The methodology is capacity-*stratified*, not capacity-*integrated* — see §3.5.
- **Temporal mismatch across data layers.** Road/facility network reflects a current (2026) OSM snapshot applied to a January 2021 event; not addressed with a historical-snapshot sensitivity check in this pass (concrete remedy noted in §3.2).
- **SAR processing rigor.** Water classification uses per-image Otsu thresholding on raw (uncalibrated) VV backscatter intensity — adequate for isolating a bimodal low/high-backscatter split within one image, but does not include radiometric calibration to sigma0, speckle filtering, terrain correction, a permanent-water mask from an external product, connected-component filtering to remove speckle-scale false positives, VV+VH combination, or validation against an independent observed-flood product. Appropriate for exploratory event mapping; a remote-sensing reviewer would reasonably ask for these before treating the flood extent as publication-grade. Single before/after pair, not a dense time series — flood extent may have differed at other points in the multi-week event.
- **Binary/penalty disruption modeling.** Neither "removed" nor "penalized" fully captures real-world adaptive behavior (informal water transport, wading, temporary detours). The true population-affected figure likely sits closer to the moderate bracket than the severe one, but this is a qualitative judgment, not something the current model quantifies directly.
- **The mechanism behind Finding 3 is unresolved, not just unconfirmed.** §4.4 reports why the originally-proposed chokepoint mechanism was retracted (a randomization null model showed the opposite pattern, confirmed by a second, independent damage metric). The underlying empirical gap (observed extent disconnects more population than the proxy despite fewer roads affected) is real but currently has no confirmed explanation — treat this as an open question, not a finding awaiting only more evidence in the same direction.
- **The headline "any access" / disconnection percentages likely overstate disconnection in heavily-fragmented disrupted scenarios.** Discovered while building the Null A2 check (`docs/robustness_checks.md` §7b): the main pipeline (§3.4, §3.6) computes travel time via multi-source Dijkstra restricted to the single *largest* post-disruption connected component, so a population pocket stranded in a smaller fragment that retains its own local facility is counted as having no access. A component-complete recomputation gives materially different absolute figures for the same severe scenario (68.65% vs. the reported 94.0% disconnected) — the severe-vs-moderate and proxy-vs-observed *comparisons* remain valid (both sides of each comparison use the same method), but the absolute headline percentages should not be read as final, complete population-disconnection figures. Recomputing every scenario with per-component pathing is noted as follow-up work, not done in this pass.
- **Preprint status.** The primary reproduction target (Macharia et al.) was a preprint as of this analysis; peer-reviewed status should be re-checked before final citation.

### 5.3 Contribution

Relative to the reproduced methodology: (1) a district-level capacity-stratified view of accessibility, explicitly scoped as stratification rather than a claim of capacity-integrated modeling; (2) a matched-conditions comparison between hazard-proxy and observed-extent disruption modeling for the same event (same population, facilities, network, and penalty multipliers — only the flood representation differs), showing the proxy approach systematically overstates inequality-widening relative to observed data across every multiplier tested, which is this project's cleanest and most defensible result; (3) a documented instance of a proposed mechanism failing a direct test — the chokepoint hypothesis in the original Finding 3 was checked with a randomization null model designed to confirm it, and was strongly contradicted instead, reported here as a retraction rather than reframed around the surviving empirical comparison it was meant to explain. If this project has a secondary methodological contribution beyond (2), it is demonstrating that a plausible, superficially well-audited mechanistic story (which itself passed two prior checks — a bridge-tag audit and an edge-overlap sensitivity test) can still be wrong, and that the two prior checks were not sufficient to catch it because they tested for a measurement artifact, not for the mechanism itself.

## 6. Data and code availability

All data pipeline code, intermediate outputs, and this manuscript are at [github.com/Shiverion/HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia). Raw bulk downloads are not committed (see `.gitignore`) but reproducible from `src/`, which documents exact source URLs and access methods, including dead ends left in place as methodological notes: live Overpass API instability, GDAL OSM-driver parsing bugs, a corrupted PDF text layer, two rounds of mislocated Sentinel-1 scene selection, an under-scoped facility extraction, and an inconsistently-defined disruption scenario — see `docs/robustness_checks.md` for the last two.

## References

- Macharia, P.M. et al. *Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya.* Research Square preprint, 2025.
- Macharia, P.M. et al. *Geographic accessibility to public and private health facilities in Kenya in 2021: An updated geocoded inventory and spatial analysis.* PMC9670107, 2023.
- HeiGIT. *Flood Impact Assessment on Road Network and Healthcare Access at the example of Jakarta, Indonesia.* AGILE-GISS, 2021.
- BNPB (Badan Nasional Penanggulangan Bencana). Situation reports, January 2021 South Kalimantan floods.
- Dinas Kesehatan Provinsi Kalimantan Selatan. *Profil Kesehatan Provinsi Kalimantan Selatan Tahun 2022.*
- WHO. SDG Indicator 3.c.1: Health worker density and distribution.
