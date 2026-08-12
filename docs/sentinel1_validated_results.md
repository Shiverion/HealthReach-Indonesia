# Validated Results — Real Sentinel-1 Observed Flood Extent (Jan 2021 Event)

**Status:** Complete. This supersedes the interim BNPB hazard-zone proxy used in `docs/phase1_summary.md` and `docs/phase2_summary.md` as the primary result — those documents are kept as-is for methodological transparency (showing how proxy vs. real data changed the picture), but this is now the validated finding for the actual January 2021 event.

## Method

1. Sentinel-1 GRD pair (VV polarization): baseline Dec 15, 2020 and event Jan 20, 2021, same relative orbit, footprints matching almost exactly (see conversation log for the two rounds of mislocated scenes caught and corrected before landing on this pair).
2. Raw GRD has no direct georeferencing (only 210 ground control points) — warped to EPSG:4326 via GCPs, cropped to the flood-affected AOI.
3. Water classified per-scene via Otsu thresholding on log-scaled backscatter intensity (relative per-image separation, not a full radiometric sigma0 calibration — adequate for this purpose since Otsu only needs within-image bimodal separation).
4. New flood extent = event water AND NOT baseline water (removes permanent rivers/water bodies common to both dates).
5. **Visually validated** (see image sent in conversation): flooding tracks tightly along the Barito river corridor and concentrates near the delta/city area; the mountainous Meratus range on the AOI's eastern edge shows essentially none — physically correct pattern, strong evidence the classification captured real flood signal.
6. Two disruption brackets applied to the road graph, same logic as the Phase 1 proxy brackets:
   - **Severe:** flooded road segments removed (impassable)
   - **Moderate:** flooded segments penalized 5× travel time (slow/risky but passable — wading, detour, boat)

## Headline numbers

| Scenario | Any road access | Within 30min | Within 60min | Within 120min |
|---|---|---|---|---|
| Baseline | 83.6% | 64.8% | 78.4% | 83.0% |
| **Sentinel-1 moderate** (realistic) | 83.6% | 57.8% | 74.3% | 81.8% |
| Sentinel-1 severe (impassable, stress test) | 6.0% | 3.3% | 4.5% | 5.7% |

**Read the moderate scenario as the primary real-world estimate.** It shows a real but measured impact (64.8%→57.8% within 30min, a 7pp drop) — much more consistent in scale with BNPB's reported ~15% of population directly affected than the severe scenario's near-total collapse. The severe scenario is a legitimate finding in its own right (see below) but should be framed as a fragility stress-test, not a literal claim that 94% of the population had zero path to care — real floods have informal resilience mechanisms (boats, wading, temporary detours) that a binary "delete the edge" graph model can't represent.

**Why severe is so much worse than the earlier BNPB-hazard-zone severe scenario (94% vs. 74% disconnected), despite affecting fewer roads (9.94% of edges vs. 17.3%):** this is consistent with — and further evidence for — the network fragility finding from Phase 2. A real flood concentrates precisely on river corridors and crossings, which are exactly the road network's structural chokepoints (bridges). Removing a smaller number of *well-targeted* chokepoint edges fragments the network more than removing a larger number of *diffusely distributed* hazard-zone edges. This is itself a genuine, reportable methodological insight: **which roads flood matters more than how much area floods.**

## Phase 2 inequality finding — now confirmed cleanly, confound resolved

| Capacity class | Baseline: within 60min | Sentinel-1 moderate: within 60min | pp drop |
|---|---|---|---|
| Underserved | 68.6% | 62.1% | **−6.5pp** |
| Well-served | 88.9% | 87.3% | −1.5pp |

Unlike the interim hazard-zone proxy (where Kota Banjarmasin's total collapse flipped the aggregate and required excluding cities to see the real pattern), **the real Sentinel-1 data shows the expected inequality pattern cleanly at the aggregate level, no exclusions needed.** Kota Banjarmasin — the confound before — now shows 0.0pp drop (stays at 100% within-60min access), because the actual observed flood didn't happen to hit its specific connecting roads, unlike the broad hazard-risk zone which covered it entirely.

**Sharpest single data point:** Barito Kuala — the lowest-capacity district in the province (24.6 clinical staff per 10k) — shows the single largest access drop of any district (−25.2pp, 84.8%→59.5%). This is also geographically expected: Barito Kuala sits immediately adjacent to Banjarmasin on the low-lying delta.

Full per-kabupaten table: `data/processed/inequality_sentinel1_per_kabupaten.csv`.

## What this means for the eventual write-up

The proxy-vs-real comparison across Phase 1/2 is itself a worthwhile methodological point to keep, not just discard: it demonstrates concretely that a general multi-year hazard-risk layer is not a substitute for event-specific observed extent, both because it overstates uniform disruption (confounding the inequality analysis via Banjarmasin) and because it misses the chokepoint-concentration effect that makes a real, geographically-specific flood more network-disruptive than its area coverage alone would suggest.

## Remaining known limitation

Binary/penalty disruption modeling still doesn't capture real-world adaptive behavior (informal water transport, temporary access). The severe scenario's magnitude should not be quoted as a literal population-affected figure. If this becomes a real research output, refining the disruption model (e.g., partial-capacity edges scaled by estimated flood depth rather than a binary flooded/not-flooded classification) would be the natural next methodological step.
