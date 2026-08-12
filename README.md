# HealthReach Indonesia

Independent replication and extension of disaster-aware geographic healthcare accessibility methodology (Macharia et al., KEMRI-Wellcome/Oxford), applied to the January 2021 South Kalimantan floods, with district-level healthcare workforce capacity stratification and disruption modeled from real Sentinel-1 SAR-observed flood extent rather than a static hazard-risk proxy.

**Status: analysis complete.** Read the results in this order:

1. [`docs/manuscript.md`](docs/manuscript.md) — the write-up: methods, results, discussion, limitations. Start here.
2. [`docs/sentinel1_derived_results.md`](docs/sentinel1_derived_results.md) — current numbers in full detail.
3. [`docs/robustness_checks.md`](docs/robustness_checks.md) — three issues a review pass caught (a 4x facility undercount, a disruption-scenario definition bug, a chokepoint-finding artifact audit) and how each was resolved. Worth reading on its own if you care about how this project handles being wrong.
4. [`notebooks/`](notebooks) — the same analysis, interactively, with maps and charts.

## Three findings

1. **Chronic inequality.** Districts with below-median healthcare workforce density already have substantially worse baseline accessibility (72.8% vs. 90.0% of population within 60 minutes of a facility), independent of any flooding.
2. **Disaster amplification.** The real January 2021 flood widened that gap (underserved districts lost roughly 6.5× the proportional access that well-served districts did) — but this is only visible using the actual observed flood extent. A common hazard-risk proxy (BNPB InaRISK) produces a confounded, backwards-looking result for this specific comparison because it doesn't distinguish which of a province's flood-prone areas actually flooded in this event.
3. **Representation matters, with appropriate confidence.** The real flood disconnected more of the population than the broader hazard-zone proxy despite affecting fewer roads — evidence consistent with a network-topology mechanism (which specific roads fail matters more than how much area floods), audited against a plausible artifact explanation (SAR misreading a dry bridge deck as flooded) and found to survive it, but based on one event in one province, not asserted as a general law.

## Repository structure

```
PROTOCOL.md                    research protocol: scope, data sources, case-study justification
README.md                      this file

docs/
  manuscript.md                 the write-up — start here
  sentinel1_derived_results.md   current, correct numbers
  robustness_checks.md          three review findings and their fixes
  phase1_summary.md             superseded (kept for audit trail — see banner in the file)
  phase2_summary.md             superseded (kept for audit trail — see banner in the file)
  literature/                   (empty placeholder for reference papers)

notebooks/                      5 executed notebooks — data overview, baseline model,
                                 proxy-vs-observed disruption, capacity/inequality, SAR walkthrough

src/                            pipeline scripts, roughly in run order:
  01_fetch_osm_data.py            \_ early attempts (live Overpass) — kept for the
  01b_extract_from_geofabrik.py   /  methodological record, NOT the path actually used
  01c_extract_with_osmium.py     roads + point-only facilities (streaming PBF parse)
  02_fetch_population.py         WorldPop raster, clipped to province
  03_process_bnpb_hazard.py      BNPB hazard-zone proxy, georeferenced + classified
  04_build_network_graph.py      routable graph + facility snapping
  05_baseline_travel_time.py     multi-source Dijkstra, baseline scenario
  06_flood_disruption.py         proxy-based disruption (severe + moderate brackets)
  07_population_weighted_comparison.py   % population within 30/60/120 min, all scenarios
  08_capacity_index.py           district workforce-per-capita index
  09_inequality_analysis.py      accessibility by capacity class, all scenarios
  10_sentinel1_flood_extent.py   SAR GCP-warp + Otsu classification + before/after diff
  11_flood_disruption_sentinel1.py   observed-extent disruption (severe + moderate)
  12_extract_facilities_complete.py  the facility extraction that's actually used —
                                      supersedes 01c's facility output, see robustness_checks.md
  build_notebooks.py             generates + executes the notebooks/ files

data/
  raw/            source data close to as-downloaded (large bulk files gitignored;
                  small reference files — boundaries, the final facility set — kept)
  processed/      pipeline outputs (large intermediates gitignored; small citable
                  results — inequality tables, capacity index — kept)
```

**If you're trying to understand the pipeline, read scripts in the numbered order above — but note `01`/`01b` are dead ends kept for the record (see their docstrings), and `12` is what actually produced the facility dataset used everywhere downstream, not `01c`.**

## Reproducing the pipeline

Large raw downloads (population raster, road/facility OSM extracts, Sentinel-1 scenes) aren't committed — see `.gitignore`. Each `src/` script documents its exact source URL and access method in its docstring. Run in the numbered order above; `04` onward assumes `01c` + `12` (roads and the complete facility set) and `02`/`03` (population and hazard raster) have already produced their outputs in `data/raw/`.

Sentinel-1 scenes require a free NASA Earthdata account and manual download via [search.asf.alaska.edu](https://search.asf.alaska.edu/) — no API key automation is set up for this step; see the conversation history / `PROTOCOL.md` for the exact search parameters used (South Kalimantan AOI, Dec 15 2020 baseline + Jan 20 2021 event, matched relative orbit).

To rebuild the notebooks after any pipeline change: `python src/build_notebooks.py` then `python -m nbconvert --to notebook --execute --inplace notebooks/*.ipynb`.

## Known limitations

Full list in `docs/manuscript.md` §5.2. Headline items: facility-level (not just district-level) workforce data isn't public, so capacity *stratifies* results rather than being *integrated* into the accessibility function; the road/facility network is a current OSM snapshot applied to a 2021 event (temporal mismatch, not corrected with a historical extract); SAR water classification is exploratory-grade (no radiometric calibration, speckle filtering, or terrain correction) rather than publication-grade.
