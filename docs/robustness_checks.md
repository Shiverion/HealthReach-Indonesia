# Robustness Checks and Fixes

Issues raised across two rounds of review after the initial results were drafted, all substantive, not stylistic — this document records what was checked, what was found, and what changed. Consistent with this project's practice of keeping dead ends visible (see `docs/phase1_summary.md`, `docs/sentinel1_derived_results.md`) rather than quietly editing history, the original documents are left in place with a note pointing here; this document is the corrected account. **Section 7 is the most important one in this file** — a check that was run in good faith to strengthen a finding instead strongly contradicted it, and the finding was downgraded accordingly rather than rescued.

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

## 4. Matched penalty sweep: is the proxy-vs-observed comparison actually controlled?

**The concern:** the proxy-moderate scenario used a ×2.5 penalty, the Sentinel-1-moderate scenario used ×5. Individually defensible, but this project's central claim is that *changing flood representation* changes the accessibility conclusion — and with two different penalty multipliers, outcome = f(footprint, penalty) has two things varying at once. Any difference between proxy and observed could be footprint, or could be the multiplier, or both.

**The fix:** `src/13_penalty_sensitivity_sweep.py` runs both layers at the identical multiplier set (×2, ×2.5, ×5, ×10), isolating footprint as the only variable that differs between proxy and observed.

**Result — the finding is not only preserved but sharper than before:**

| Multiplier | Proxy gap-widening | Observed gap-widening | Proxy / Observed ratio |
|---|---|---|---|
| ×2 | +1.58pp | +0.62pp | 2.57× |
| ×2.5 | +2.37pp | +0.95pp | 2.49× |
| ×5 | +4.83pp | +2.37pp | 2.03× |
| ×10 | +8.26pp | +4.84pp | 1.71× |

At **every** matched multiplier, the hazard-zone proxy overstates how much flood disruption widens the underserved-vs-well-served accessibility gap, by a factor of roughly 1.7–2.6× relative to the real observed-extent data. The ratio isn't perfectly constant, but the direction is unanimous across all four multipliers tested — this is a controlled, quantitative version of "representation matters," not just a qualitative comparison at one arbitrarily-chosen setting each. Full table: `data/processed/penalty_sensitivity_sweep.csv`.

Separately, the gap-widening direction itself (flooding widens the chronic gap) held at every multiplier for both layers — 8/8 scenarios showed positive widening, none reversed.

## 5. Edge-overlap sensitivity: is the 94% severe-disconnection number an artifact of midpoint sampling?

**The concern:** flood status was sampled at a single point (each edge's midpoint). A long edge with a small flooded fraction could be flagged as entirely impassable, inflating the severe scenario's fragmentation.

**Context that lowers the prior risk:** graph edges are consecutive OSM node-pairs, not whole ways, so most are already short (median 22m; 90th percentile 78.5m; only 1.1% exceed 200m) — checked empirically before assuming the concern was as large as the illustrative "800m edge" scenario suggested.

**The check:** `src/14_edge_overlap_sensitivity.py` resamples each edge at 5 points along its length and reruns the severe scenario at overlap thresholds of >0%, >25%, >50%, >75%.

**Result:**

| Overlap threshold | Edges removed | Largest component |
|---|---|---|
| >0% (any point) | 81,578 | 9.0% |
| >25% | 66,863 | 9.2% |
| >50% | 53,562 | 9.3% |
| >75% | 42,674 | 10.4% |

The largest-component percentage is essentially flat across thresholds spanning a 2× range in edges removed (81,578 → 42,674). This is close to the best possible outcome for this check: the extreme fragmentation result is not an implementation artifact of the flood-overlap sampling rule. (A fifth threshold, ">100%", was included in the original run but is a degenerate case in the script's `frac > threshold` logic — never true when the maximum possible fraction is 1.0 — and is excluded from this table as a coding edge case, not a finding.)

## 6. Continuous capacity analysis, leave-one-out, and workforce denominator sensitivity

**The concern (n=13, median split):** binarizing a continuous variable (workforce density) into two classes at the median throws away information and risks being driven by whichever districts sit near the cutoff or by a single influential district (Kota Banjarmasin was already known to behave unusually).

**Continuous check:** Spearman correlation between clinical-staff density and 60-min accessibility change across all 13 districts: **ρ = 0.549, p = 0.052** (n=13). Treated as descriptive triangulation alongside the scatter plot (`data/processed/capacity_vs_access_change_scatter.png`), not as a significance claim to lean on — at n=13 a fitted model would mostly cosplay as statistical power, so none was fit.

**Leave-one-district-out check:** the underserved-vs-well-served gap-widening finding was recomputed 13 times, each time excluding one district. **The gap widened (direction preserved) in 13/13 runs**, with the widening estimate ranging from +1.10pp to +2.93pp (full sample: +2.37pp) — no single district, including Barito Kuala (the most extreme individual case) or Kota Banjarmasin, drives the result or reverses it. Full table: `data/processed/leave_one_out_inequality.csv`.

**Workforce denominator sensitivity:** the capacity index used WorldPop 2020 population as the denominator against 2022 workforce counts. The source document (Profil Kesehatan 2022) turned out to have its own per-kabupaten 2022 census population (Gambar 1.5, read visually after confirming it wasn't in an extractable table — same situation as Tabel 13). Recomputing capacity with the matched-year BPS 2022 population: **2 of 13 districts flip classification** (Tapin underserved→well-served, Hulu Sungai Utara well-served→underserved), a real but modest sensitivity (11/13 stable). Recomputing the aggregate inequality finding with the BPS-based classification: baseline gap 17.19→17.42pp, widening 2.37→2.30pp — **the finding is essentially unchanged** despite the reclassification. Barito Kuala, the sharpest single data point in the write-up, stays "underserved" under both population sources.

## 7. Null model: the "chokepoint mechanism" claim does not survive testing

**Background:** the observed Sentinel-1 flood (9.94% of edges) disconnects more of the network (94.0% of population, largest surviving component 9.06% of nodes) than the broader hazard-zone proxy (17.3% of edges, 74.0% disconnected). The manuscript's original Finding 3 explained this as evidence of a network-topology mechanism — that real floods preferentially concentrate on structurally important "chokepoint" edges (river crossings), so fewer affected edges can still cause more damage than a larger, more diffusely-distributed set. Sections 3 and 5 of this document had already audited part of that claim (bridge tags, edge-overlap sensitivity) and found it held up. This section reports a more direct test of the mechanism itself, and it does not hold up.

**Scope, stated precisely:** this is Null A only — edges chosen **uniformly at random** from the whole network, same count (55,983) as the real Sentinel-1 flood, largest connected component as the damage metric, 200 trials (`src/16_null_model_random_edges.py`). Null A tests **Sentinel-1 vs. uniform random**, not Sentinel-1 vs. the proxy's specific spatial pattern directly — so what follows establishes that Sentinel-flooded edges are not unusually fragmentation-prone relative to an arbitrary equal-sized edge set, which is enough to withdraw the general "floods hit chokepoints better than chance" claim, but does not by itself characterize the proxy's specific spatial structure. Road-class-matched (Null B) and spatially-constrained (Null C) nulls, which would test sharper versions of the mechanism, were explicitly scoped out rather than attempted — noted here as a limitation of this check, not implied to have been covered.

**Result:**

| | Largest component remaining |
|---|---|
| Observed Sentinel-1 flood (real edges) | **9.06%** |
| Random removal, same edge count (200 trials) | mean 3.18%, range 1.35%–4.47% |

**Not one of 200 random trials was as mild as the observed flood.** Two directional Monte Carlo tests, both using the correct estimator p = (b+1)/(B+1):
- *Is the observed flood more damaging than random?* b = 200 trials at least as damaging, p = 1.0000 — zero evidence for this direction. A p-value of 1.0 means the data give no support for the alternative, not "100% proof the hypothesis is false"; stated precisely, not overstated.
- *Is the observed flood less damaging than random?* b = 0 trials at least as mild, p = (0+1)/(200+1) ≈ **0.005** — this is the statistically correct way to state the actual finding, and it is a strong result under this null.

**What this means, stated at the precision the test actually supports:** the chokepoint mechanism was withdrawn because its strongest testable prediction failed under a uniform-random null, not because Null A mathematically proved every possible version of the chokepoint story false (see the scope note above — it didn't test Sentinel vs. the proxy's actual spatial pattern, only vs. random). One plausible explanation for the reversal is that random failures are scattered across the whole province (each independently able to sever an unrelated local branch) while a real flood's damage stays geographically concentrated in one region — but **this is an untested hypothesis, not a finding**; establishing it would require a spatially-constrained null (Null C), which was not run. Stating it as "almost certainly because X" here would repeat, one paragraph after correcting it, exactly the kind of unearned causal claim this section exists to catch.

**What is still true, and does not depend on this mechanism being correct:**
- The direct empirical comparison — Sentinel-1 (fewer edges) disconnects more of the *population from facilities* than the proxy (more edges) — is a fact independent of any explanation for it, and is unaffected by this null model.
- The proxy-vs-observed comparison as a whole (§4 above, the matched-penalty sweep) is a separate, still-robust finding: it concerns the *inequality* result (proxy overstates gap-widening), not the chokepoint mechanism, and does not rely on it.

**What is retracted:** the specific causal story that real floods are unusually effective at severing structurally important links, and the "which roads flood matters more than how much" framing built on it. The manuscript's Finding 3 has been rewritten (§4.4, v0.3) to report the empirical S1-vs-proxy gap honestly while stating plainly that no confirmed mechanism explains it — candidate explanations (the real flood may sever the *specific* corridor connecting the largest population center to facilities, rather than being structurally special in a generic graph-theoretic sense; road-class composition of the two edge sets differs and wasn't controlled for) are noted as open questions, not claims.

This is the outcome the review process was actually for. A check run to strengthen a finding instead disproved its explanation, and the honest move is to say so, not to quietly drop the null model or reframe around it after the fact.

## 7b. Null A2: does the metric matter — generic connectivity vs. healthcare-specific access?

**The concern:** Null A's damage metric (largest connected component size) is not the same thing as the phenomenon that motivated Finding 3 in the first place — population losing access to healthcare specifically. These can diverge: random failure could fragment the graph into many small pieces that mostly contain no population (rural cul-de-sacs — bad for generic connectivity, fine for healthcare access), while a geographically concentrated flood could isolate one large, densely-populated, facility-poor region (comparatively mild for generic connectivity, severe for healthcare access).

**The check:** `src/17_null_model_facility_access.py` reruns the same 200-trial randomization, same edge count (55,983), but with a different damage metric: population sitting in a post-removal connected component that contains **zero health facilities**, summed across all components (not just the largest one).

**A genuine measurement discrepancy surfaced while building this, reported rather than smoothed over:** using this component-complete method, the *real* Sentinel-1 flood disconnects 68.65% of population from all facilities — not the 94.0% reported as the headline "severe" scenario figure elsewhere in this project (`docs/sentinel1_derived_results.md`, `docs/manuscript.md` §4.2). Both numbers are computed correctly; they answer different questions. The headline pipeline (`src/06`, `src/11`) runs its multi-source Dijkstra restricted to the single **largest** post-disruption connected component only (a standard simplification to avoid separately pathing hundreds of tiny fragments) — so a population pocket stranded in a *smaller* fragment that happens to retain its own local puskesmas is counted as "no access" by the headline method, even though it has a real, working facility nearby. Null A2's component-complete method credits that local access. **This means the headline "94.0% disconnected" figure likely overstates true disconnection in heavily-fragmented disrupted scenarios** — a real limitation of the headline pipeline, surfaced by building a more careful null model, not by external review this time. Recomputing every headline scenario with per-component pathing is noted as follow-up work and was not done in this pass (see `docs/manuscript.md` §5.2); the 94.0%/74.0% comparisons between proxy and observed severe scenarios are still valid as an apples-to-apples comparison (both computed the same way), just not to be read as literal, complete population-disconnection figures in isolation.

**Result, using the internally-consistent A2 method throughout (observed vs. random, same metric for both):**

| | Population disconnected from all facilities |
|---|---|
| Observed Sentinel-1 flood (real edges) | **68.65%** |
| Random removal, same edge count (200 trials) | mean 89.49%, range 86.51%–91.54% |

Empirical randomization p ≈ 0.005 for the correctly-specified direction (observed less damaging than random) — same as Null A, and if anything a cleaner separation (the observed value sits below the *minimum* of all 200 random trials).

**This confirms Null A rather than complicating it.** The healthcare-specific metric and the generic-topology metric agree: the real flood is less disruptive by both measures than the same number of edges failing at random. This was not guaranteed — the metrics could have diverged (generic connectivity mildly damaged, healthcare access severely damaged, or vice versa) — and finding agreement instead is a stronger basis for the retraction than Null A alone, not a redundant check.

## What this means for the write-up

Three rounds of review, ten issues total, all addressed rather than merely acknowledged. The first round caught outright errors (facility undercount, a scenario-definition bug). The second round caught claims that were individually defensible but not yet earned at the confidence level they were stated with — most held up or got stronger (matched-penalty sweep, leave-one-out, edge-overlap, workforce denominator), one did not (the chokepoint mechanism, §7). The third round caught something harder to see: precision failures in how the *retraction itself* was worded (overstating a p-value's meaning, repeating an unearned causal claim one paragraph after correcting a different one, a stale claim about which disruption representation shows amplification), plus a genuine follow-up check (§7b) that confirmed the retraction using an independent damage metric — and, as a side effect of building that check carefully, surfaced a real measurement caveat in the headline pipeline that nobody had asked about yet. Reporting a limitation nobody raised, because building a robustness check happened to expose it, is the same standard applied throughout this file — just self-directed this time instead of prompted.
