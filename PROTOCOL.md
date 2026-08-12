# Research Protocol — HealthReach Indonesia

**Working title:** *Beyond Proximity: Capacity-Stratified Healthcare Accessibility Under Flood Disruption in South Kalimantan*
**Repository / portfolio name:** HealthReach Indonesia
**Status:** Analysis complete, including two rounds of review that caught and fixed several substantive issues — a facility undercount, a disruption-scenario bug, and (most consequentially) a randomization null model that strongly contradicted an early "chokepoint mechanism" claim, reported as a retraction rather than reframed. See `docs/robustness_checks.md`. Primary write-up: `docs/manuscript.md`. Current numbers: `docs/sentinel1_derived_results.md`. `docs/phase1_summary.md` and `docs/phase2_summary.md` are kept for methodological transparency (earlier interim results, both from the BNPB hazard-zone proxy and pre-review-fix).

---

## 1. Framing

This is an **independent replication and extension**, not a novel-from-scratch model. The claim to make in any write-up or application material:

> Independent replication of disaster-aware geographic healthcare accessibility methodology (Macharia et al., KEMRI-Wellcome/Oxford), extended to Indonesia with district-level healthcare workforce capacity stratification, applied to a real documented flood event via Sentinel-1-derived disruption modeling.

Do **not** claim "improved research from Oxford" or "first GIS healthcare study in Indonesia" — both are false claims that a knowledgeable reviewer will catch (see §4, prior art).

## 2. Reference / target literature

- **Primary reproduction target:** *"Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya"* — preprint, [Research Square](https://www.researchsquare.com/article/rs-7724672/v1). Not yet peer-reviewed as of this writing — verify publication status before citing as "published."
- **Methodology precedent:** Macharia et al., [*"Geographic accessibility to public and private health facilities in Kenya in 2021"*](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9670107/) (PMC9670107) — establishes the AccessMod-based travel-time methodology this project reproduces.
- **Tooling precedent:** [AccessMod](https://www.who.int/tools/accessmod) (WHO, free/open, QGIS-based least-cost-path travel time) is the standard tool this literature uses — use it directly rather than building travel-time modeling from scratch.

## 3. Case study region and event

**Region:** South Kalimantan (Kalimantan Selatan), 13 kabupaten/kota.

**Why this region (not East Kalimantan, not Jakarta):**
1. Real, severe, well-documented flood event — Jan 2021, called "the worst flood to affect the region in the last ten years" ([Wikipedia: 2021 South Kalimantan floods](https://en.wikipedia.org/wiki/2021_South_Kalimantan_floods)). BNPB situation reports name 10 of the 13 affected kabupaten/kota, with casualty and displacement figures — a real before/after event, not a hypothetical hazard scenario.
2. Flood-affected districts and the available workforce data are on the **same administrative grain** (kabupaten/kota) — no extra spatial harmonization needed.
3. Avoids direct overlap with prior art (§4).

**Flood event reference:** January 2021, South Kalimantan. BNPB: 10 kabupaten/kota affected, 46 deaths, 633,273 people affected, 123,410 houses inundated. Source: [BNPB situation report](https://bnpb.go.id/berita/-update-10-kabupaten-kota-terdampak-banjir-di-kalimantan-selatan).

## 4. Prior art — read and cite, do not ignore

- [HeiGIT, *"Flood Impact Assessment on Road Network and Healthcare Access... Jakarta, Indonesia"*](https://agile-giss.copernicus.org/articles/2/4/2021/) (AGILE-GISS 2021) — same genre of study, different city/event (2013 Jakarta flood). Differentiate explicitly: national-Indonesia methodology precedent exists, but not for South Kalimantan, and not with capacity weighting.
- Static (non-flood) Indonesian accessibility studies exist for Maluku, Muna Barat, Gunungkidul — cite as evidence the baseline methodology is well-trodden in-country; the novelty here is flood disruption + capacity weighting + a real 2021 event, not "first GIS accessibility study in Indonesia."

## 5. Scope — MVP first, extensions are stretch goals

### Phase 1 (core): Baseline vs. flood-disrupted accessibility
- Compute travel time to nearest health facility under normal conditions (population → road network → facilities).
- Recompute under flood disruption using **observed** flood extent for the Jan 2021 event (§6) — not just a static hazard-risk layer.
- Output: population within 30/60/120 min of a facility, normal vs. flood-disrupted.

### Phase 2 (core differentiator): District-level capacity weighting
- Weight accessibility by district-level healthcare workforce adequacy (ratio vs. RPTK target) — see §6 for confirmed data structure.
- Produces "effective accessibility," not just proximity.
- **Title reflects this exactly:** "district-capacity-adjusted," not "facility-capacity-adjusted" — facility-level workforce data was checked and does not exist in public form (§7).

### Explicitly deferred (do not start until Phase 1+2 are done and written up)
- National-scale analysis
- Uncertainty / bootstrapped scenario analysis
- Facility-location optimization (MCLP via `spopt`) — tooling identified and ready when/if this becomes Phase 3
- Forward-looking flood *prediction* via NASA GFMS/IMERG (§6) — cite as a validation reference point at most, don't build a forecaster
- Interactive dashboard — v2, after the research write-up

## 6. Data sources — confirmed and verified this session

| Layer | Source | Access | Status |
|---|---|---|---|
| Geocoded health facilities | [HDX Indonesia Healthsites](https://data.humdata.org/dataset/indonesia-healthsites) (healthsites.io / OSM) | Free download | Confirmed exists; **coverage completeness in Kalsel specifically not yet spot-checked** |
| Road network | [Geofabrik OSM Indonesia](https://download.geofabrik.de/asia/indonesia.html) | Free download, actively maintained | Confirmed; rural completeness not yet spot-checked |
| Population | [WorldPop Indonesia 100m grid](https://hub.worldpop.org/geodata/summary?id=44750) | Free download | Confirmed |
| Flood hazard (baseline risk) | BNPB [InaRISK GIS server](https://gis.bnpb.go.id/) (`layer_bahaya_banjir`), ArcGIS REST, JSON/GeoJSON | Free, programmatic | Confirmed |
| ~~Flood extent via MODIS/VIIRS~~ | ~~NASA MCDWD, LAADS DAAC~~ | Free, Earthdata login | **Ruled out for this event.** Pulled actual MODIS true-color imagery for Kalsel on Jan 12/15/18/20 2021 — nearly fully cloud-obscured on every date (Jan 15: no land visible at all). Monsoon season, which is why it flooded, is exactly when optical imagery can't see through cloud. Keep as a citation of the general methodology, not as an actual data layer. |
| **Flood extent (observed, Jan 2021 ground truth) — primary source** | Sentinel-1 SAR via NASA [ASF DAAC](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/sentinel-1) (Vertex) | Free, Earthdata login | Cloud-penetrating radar, operational since 2014, global coverage — standard approach in the Indonesian flood-mapping literature specifically because of this cloud problem. Not yet pulled an actual scene (needs authenticated ASF Vertex search); high confidence a usable pass exists in-window, confirm before building the pipeline. |
| Terrain / DEM | NASA SRTM (via Earthdata) | Free | Standard input for AccessMod |
| **District-level workforce capacity** | Kalsel *Profil Kesehatan 2022*, Tabel 15–17 (`data/raw/kalsel_health_profile/`) + [BPS Kalsel](https://kalsel.bps.go.id/) cross-check | Already downloaded | **Confirmed: kabupaten/kota level only.** No facility-level data — verified by reading the actual tables; "UNIT KERJA" rows are the 13 districts, hospital rows are unfilled template placeholders. |
| Optional stretch: forecast validation | NASA [GFMS](http://flood.umd.edu/) (IMERG-driven hydrological model) | Free, web + some historical archives | Real-time/historical simulation output could serve as an independent validation point for the Jan 2021 event; not required for core scope |

## 7. Known risks — checked

1. **HDX/OSM facility completeness in South Kalimantan — passed.** Live Overpass query: 76 hospital-tagged features vs. 53 official (Dinkes Kalsel 2022); 275 clinic/health-centre features vs. 241 official puskesmas. Same order of magnitude, not a sparse-rural-gap problem. OSM road-network completeness not independently re-verified (Overpass queries for it timed out on public mirrors under load) — re-check once the pipeline is actually being built.
2. **MODIS cloud cover — failed, plan updated.** Actual imagery pulled for Jan 12/15/18/20 2021 over Kalsel: near-total cloud cover on every date. **Sentinel-1 SAR is now the primary (not backup) source for observed flood extent** — see §6.
3. **Preprint status — confirmed still unpublished.** The primary reference paper (§2) is still a Research Square preprint as of the most recent check, no journal publication found. Cite as "preprint (Research Square, 2025)"; re-check before the final write-up in case it publishes in the meantime.

## 8. Tooling

- **Travel-time / accessibility modeling:** AccessMod (WHO, QGIS-based) — matches the literature directly. Python alternatives (`pandana`, OSRM) are a fallback if AccessMod proves awkward to script/reproduce.
- **Spatial processing:** `geopandas`, `rasterio`, QGIS.
- **Optimization (Phase 3, stretch only):** [`spopt`](https://pysal.org/spopt/notebooks/mclp.html) (PySAL) — Maximal Covering Location Problem, already identified as the right tool if this phase is reached.

## 9. Deliverable order

1. This protocol (done).
2. Phase 1 pipeline + written baseline-vs-disrupted results.
3. Phase 2 capacity weighting + written "effective accessibility" results.
4. Methodology write-up (paper-style: reproduction → limitation → hypothesis → experiment → robustness → contribution).
5. Repository cleanup / README for portfolio presentation.
6. (v2, optional) interactive dashboard.
