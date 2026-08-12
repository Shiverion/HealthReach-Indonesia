# Beyond Proximity: Capacity-Aware Healthcare Accessibility Under Flood Disruption in South Kalimantan, Indonesia

**Status: Draft v0.1.** Independent replication and extension. Repository: [HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia).

## Abstract

Standard geographic healthcare accessibility models treat facilities as uniform points and disasters as static hazard layers, obscuring two things that determine real-world impact: whether a facility is actually staffed to treat patients, and where a flood actually happened rather than where it merely could. We replicate the geospatial network-accessibility methodology used by Macharia et al. (Kenya, 2025 preprint) for South Kalimantan, Indonesia, and extend it in two directions: (1) district-level healthcare workforce capacity weighting, using a WHO SDG 3.c.1-style clinical staff density indicator, and (2) validation of flood disruption against Sentinel-1 SAR-observed flood extent for the actual January 2021 South Kalimantan flood, rather than a static multi-year hazard-risk classification. We find that baseline accessibility already varies substantially by district workforce capacity (68.6% vs. 88.9% of population within 60 minutes of a facility, low- vs. high-capacity districts), that this gap widens under flood disruption in a way only visible with the *real* disruption footprint (a −6.5pp vs. −1.5pp access change), and — as a general methodological finding independent of this specific case — that a flood's *road-network topology* (which specific crossings it inundates) determines its accessibility impact more than its raw areal extent, because real floods concentrate on structural network chokepoints in a way that diffuse hazard-risk layers do not.

## 1. Introduction

Geographic accessibility to healthcare is typically modeled as a function of population, road networks, and facility locations, producing a travel-time surface used to identify underserved populations. Two simplifications are near-universal in this literature and both matter for disaster response: facilities are treated as equivalent regardless of whether they are adequately staffed, and disaster disruption is modeled using hazard-risk classifications (multi-year probabilistic risk zones) rather than the actual extent of a specific event, because observed-extent data is harder to obtain and process.

This study asks: for a specific flood event in a specific place, how much does each simplification matter, and does correcting for them change which populations are identified as most affected?

South Kalimantan, Indonesia is a strong setting for this question. It experienced a well-documented, severe flood in January 2021 (BNPB: 10 of 13 kabupaten/kota affected, 46 deaths, 633,273 people affected) with real ground-truth impact data to validate against, sits on a river delta where population and infrastructure concentrate on flood-prone lowlands, and has open data across the layers this analysis needs (OpenStreetMap facilities and roads, WorldPop population, government workforce statistics, and free Sentinel-1 SAR archives).

## 2. Related work and positioning

**Primary reproduction target:** Macharia et al., *"Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya"* (Research Square preprint, 2025) — establishes the baseline-vs-disrupted geographic accessibility methodology this study reproduces, itself building on Macharia et al.'s earlier Kenya facility-accessibility work (Macharia et al. 2023, *Geographic accessibility to public and private health facilities in Kenya in 2021*).

**Prior art in Indonesia, explicitly acknowledged rather than presented as absent:** HeiGIT's *Flood Impact Assessment on Road Network and Healthcare Access... Jakarta, Indonesia* (AGILE-GISS, 2021) applies the same genre of flood-accessibility analysis to the 2013 Jakarta flood. Several static (non-flood) Indonesian accessibility studies exist for other regions (Maluku, Muna Barat, Gunungkidul). This study's contribution is not "the first accessibility study in Indonesia" but the combination of (a) a new region and event, (b) workforce capacity weighting, and (c) validated observed-extent disruption modeling with an explicit comparison against the more commonly-used hazard-proxy approach.

## 3. Data and methods

### 3.1 Study area and event

South Kalimantan province, 13 kabupaten/kota. Disruption event: the January 2021 flood, BNPB-documented across 10 of the 13 districts.

### 3.2 Data sources

| Layer | Source | Notes |
|---|---|---|
| Health facilities | OpenStreetMap (Geofabrik Kalimantan extract, streamed via `pyosmium`) | 90 facilities (35 hospitals, 46 clinics, 9 doctors) |
| Road network | Same OSM extract, classified roads (motorway–residential) | 62,674 segments, 592k-node graph |
| Population | WorldPop Indonesia 2020, 100m | ~4.50M in the clipped province area |
| Baseline flood hazard (proxy) | BNPB InaRISK, rendered raster reclassified into 3 risk bins | Multi-year hazard-risk zone, not event-specific |
| Observed flood extent (primary) | Sentinel-1 GRD, before/after pair (Dec 15 2020 / Jan 20 2021) | See §3.5 |
| District workforce | Dinkes Kalsel *Profil Kesehatan 2022*, Tabel 13–14 | Doctors, nurses, midwives by kabupaten |

### 3.3 Baseline accessibility model

Standard population → road network → facility travel-time model. Roads assigned free-flow speeds by class (20–80 km/h). Travel time from every road-network node to the nearest facility computed via a single multi-source Dijkstra run (all 89 graph-matched facility nodes as simultaneous sources) rather than one shortest-path query per population point — the same result, computed once instead of tens of thousands of times. Population aggregated to ~1km cells (sum-resampled, preserving total counts) and snapped to the nearest graph node via a KD-tree for the population-weighted summary.

### 3.4 District capacity index

Following the WHO SDG 3.c.1 convention (physicians + nursing/midwifery personnel per 10,000 population), a clinical-staff density index was computed per kabupaten from doctors (general + specialist), nurses, and midwives, divided by WorldPop population zonal-summed to the same kabupaten boundaries. Districts were split at the province median into "underserved" and "well-served" classes.

### 3.5 Flood disruption modeling: proxy vs. observed

Two disruption layers were used, deliberately, to make the comparison itself part of the result rather than to discard one in favor of the other.

**Proxy (BNPB InaRISK hazard classification).** BNPB's flood-hazard MapServer exposes only a rendered RGBA raster (no raw classification value endpoint was found), so hazard class was reverse-engineered via color-threshold classification into three bins (low/medium/high). This represents flood-*prone* area accumulated over many years, not any single event's footprint.

**Observed (Sentinel-1 SAR).** A Sentinel-1 GRD pair was obtained: baseline Dec 15, 2020 and event Jan 20, 2021, matched to the same relative orbit for consistent viewing geometry. Raw GRD products carry only ground-control-point geolocation (no direct affine transform), so each scene was warped to EPSG:4326 via its embedded GCPs and cropped to the flood-affected AOI. Water was classified independently per scene via Otsu thresholding on log-scaled VV backscatter intensity (a per-image relative separation — adequate for isolating a scene's low-backscatter mode without requiring full radiometric sigma0 calibration). New flood extent was defined as event-classified water not present in the baseline classification, removing permanent rivers and water bodies common to both dates. The result was visually validated against known geography: flooding concentrates tightly along the Barito river corridor and the low-lying delta near the provincial capital, while the mountainous Meratus range at the AOI's eastern edge shows negligible flooded area — the expected physical pattern.

For both disruption layers, two brackets were computed against the road graph: **severe** (affected road segments removed as impassable) and **moderate** (affected segments penalized, travel time × 2.5 for the proxy / × 5 for the observed extent, representing passable-but-slow-or-risky conditions rather than complete impassability). The severe bracket is a network-fragility stress test; the moderate bracket is the more realistic estimate of actual conditions, since flooded roads are rarely completely and uniformly impassable to all traffic (informal detours, 4WD, boat) — a binary graph-edge deletion cannot represent that resilience mechanism.

## 4. Results

### 4.1 Baseline accessibility

83.6% of South Kalimantan's population has road-network access to a health facility of any kind; 64.8% within 30 minutes, 78.4% within 60 minutes, 83.0% within 120 minutes.

### 4.2 Flood disruption: proxy vs. observed

| Scenario | Any access | Within 30min | Within 60min | Within 120min |
|---|---|---|---|---|
| Baseline | 83.6% | 64.8% | 78.4% | 83.0% |
| Proxy — moderate | 44.2%¹ | 31.0% | 39.5% | 43.6% |
| Proxy — severe | 26.0% | 14.8% | 21.6% | 25.1% |
| Observed (Sentinel-1) — moderate | 83.6% | 57.8% | 74.3% | 81.8% |
| Observed (Sentinel-1) — severe | 6.0% | 3.3% | 4.5% | 5.7% |

¹ "Any access" for the proxy scenarios reflects total network fragmentation from removing all medium+high hazard-zone edges province-wide; see §5.1 for why this differs so sharply from the observed-extent severe scenario despite affecting a larger share of edges.

**The observed-extent moderate scenario is the primary real-world estimate**, and its magnitude (a 7pp drop in 30-minute access) is far more consistent with BNPB's reported ~15% of population directly affected than either severe scenario or the proxy-based moderate scenario. The proxy systematically overstates disruption because it applies a general multi-year hazard classification uniformly, rather than the geographically specific footprint of one event.

### 4.3 A network-topology finding, not specific to this case

The observed-extent severe scenario disconnects *more* of the population (94%) than the proxy severe scenario (74%) despite affecting *fewer* road segments (9.94% of edges vs. 17.3%). This is not noise: real flood water concentrates on river corridors, and roads cross rivers at a comparatively small number of bridges — exactly the network's structural chokepoints. A hazard-risk proxy, being more diffusely distributed across a broader area, removes more edges overall but hits fewer *critical* ones. The general form of this finding — that which specific links are disrupted matters more to network connectivity than how many or how much area is affected — is a transportation-network-science result independent of this specific flood, and is directly actionable: it argues for prioritizing bridge/chokepoint resilience investment over broad area-based hazard mitigation when the goal is preserving healthcare access specifically.

### 4.4 Inequality by district capacity

| Capacity class | Baseline within 60min | Observed (moderate) within 60min | pp change |
|---|---|---|---|
| Underserved | 68.6% | 62.1% | **−6.5pp** |
| Well-served | 88.9% | 87.3% | −1.5pp |

Underserved districts start from a substantially worse baseline (a standalone chronic-inequality finding, independent of flooding) and lose disproportionately more access under real flood disruption. This pattern is clean at the aggregate level using observed-extent data. It was *not* clean using the hazard-zone proxy — there, Kota Banjarmasin (highest capacity, 56.1 staff/10k, but also the most flood-exposed district geographically, being the low-lying delta capital) collapsed entirely under the proxy's blanket hazard coverage and flipped the population-weighted aggregate, requiring the two cities to be excluded before the expected pattern was visible among the 11 rural kabupaten. With observed extent, Banjarmasin shows a 0.0pp change (its specific road connections were not, in fact, part of the actual flooded footprint), and the aggregate inequality result holds without needing to exclude anything. **This is itself evidence for why observed-extent validation matters methodologically, not only for accuracy but for whether an inequality claim survives scrutiny at all.**

The single sharpest data point: Barito Kuala, the lowest-capacity district in the province (24.6 clinical staff per 10k population), shows the largest access drop of any district (−25.2pp), and sits immediately adjacent to Banjarmasin on the same low-lying delta.

## 5. Discussion

### 5.1 Robustness: what changed between proxy and observed data, and why it matters

Both disruption layers agree on direction (flooding reduces access, more so for underserved districts) but disagree substantially on magnitude and, critically, on which specific districts appear most affected. The proxy's Banjarmasin confound (§4.4) demonstrates that a hazard-risk layer is not a safe substitute for observed extent even for *directional* claims about inequality, not merely for precise magnitudes. Any accessibility study using only a hazard-risk proxy (a common practice, since observed-extent processing is more difficult) should treat district-level disparities identified that way as provisional rather than confirmed.

### 5.2 Limitations

- **Facility completeness.** 90 facilities is likely an undercount: the extraction reliably captured point-mapped OSM facilities but not building-outline/multipolygon-relation-mapped hospital campuses. An independent Overpass count found 76 hospital-tagged and 275 clinic/health-centre-tagged features province-wide (nodes+ways combined) versus 90 in the final dataset.
- **District-, not facility-level, capacity.** Facility-level workforce data is not public in South Kalimantan; the capacity index is necessarily a district average, which cannot distinguish a well-staffed hospital from an understaffed one within the same kabupaten.
- **Binary/penalty disruption modeling.** Neither the "removed" nor "penalized ×5" treatment of flooded road segments captures real-world adaptive behavior — informal water transport, wading, temporary detours — that likely means the true population-affected figure sits between the moderate and severe brackets, closer to moderate. The severe bracket should be read as a network-fragility stress test, not a literal claim.
- **Single before/after SAR pair.** One baseline and one event scene, not a dense time series; flood extent may have been larger or smaller at other points in the multi-week event.
- **Preprint status.** The primary reproduction target (Macharia et al.) was a preprint as of this analysis; its peer-reviewed status should be re-checked before final citation.

### 5.3 Contribution

Relative to the reproduced methodology: (1) district-level capacity weighting using a standard, comparable WHO indicator rather than proximity alone; (2) a validated comparison between hazard-proxy and observed-extent disruption modeling for the same event, showing the proxy approach is not just less precise but can produce a materially different (and in this case confounded) inequality finding; (3) a network-topology finding — chokepoint concentration mattering more than areal extent — that is transportable to other flood-accessibility contexts beyond this specific case.

## 6. Data and code availability

All data pipeline code, intermediate outputs, and this manuscript are at [github.com/Shiverion/HealthReach-Indonesia](https://github.com/Shiverion/HealthReach-Indonesia). Raw bulk downloads (population raster, road/facility PBF extracts, Sentinel-1 scenes) are not committed to the repository (see `.gitignore`) but are reproducible from the scripts in `src/`, which document the exact source URLs and access methods used, including several dead ends (live Overpass API instability, GDAL OSM-driver parsing bugs, a corrupted PDF text layer, two rounds of mislocated Sentinel-1 scene selection) left in place as methodological notes rather than cleaned away.

## References

- Macharia, P.M. et al. *Impact analysis of flood-induced changes in geographical accessibility and coverage to healthcare in both public and private sector, Kenya.* Research Square preprint, 2025.
- Macharia, P.M. et al. *Geographic accessibility to public and private health facilities in Kenya in 2021: An updated geocoded inventory and spatial analysis.* PMC9670107, 2023.
- HeiGIT. *Flood Impact Assessment on Road Network and Healthcare Access at the example of Jakarta, Indonesia.* AGILE-GISS, 2021.
- BNPB (Badan Nasional Penanggulangan Bencana). Situation reports, January 2021 South Kalimantan floods.
- Dinas Kesehatan Provinsi Kalimantan Selatan. *Profil Kesehatan Provinsi Kalimantan Selatan Tahun 2022.*
- WHO. SDG Indicator 3.c.1: Health worker density and distribution.
