# Phase 2 Results — District Capacity Weighting & Inequality Analysis

**Status:** Complete. **Region:** South Kalimantan, 13 kabupaten/kota.

## Method

1. **Capacity index:** WHO SDG 3.c.1-style indicator — (dokter spesialis + dokter umum + perawat + bidan) per 10,000 population — computed per kabupaten from Tabel 13/14 of the Dinkes Kalsel Profil Kesehatan 2022. Districts split at the province median (39.6 per 10k) into `underserved` (6 districts) vs `well-served` (7 districts, including both cities).
2. **Data quality note:** Tabel 13 (doctors) had a corrupted text layer in the source PDF (broken character encoding specific to that page — visible as scrambled single-character tokens under both `pdftotext` and `pdfplumber` text extraction). Resolved by rendering the page as an image and transcribing visually; every transcribed total matches the province-wide totals exactly (761 specialists, 1,380 general doctors, 491 dentists, 9,382 nurses, 5,553 midwives) — see `data/raw/kalsel_health_profile/workforce_by_kabupaten.csv`.
3. **Population denominators:** WorldPop raster zonal-summed per kabupaten boundary (fetched via Nominatim — one geocoding error caught and fixed: a plain "Banjar" query resolved to Banjarmasin city rather than the much larger Kabupaten Banjar; verified by checking polygon area against known figures before proceeding).
4. Population points from Phase 1 spatially joined to kabupaten, then baseline/disrupted travel times cross-tabulated by capacity class.

## Results

### Aggregate, population-weighted, by capacity class

| Capacity class | Baseline: within 60min | Flood (moderate): within 60min | pp drop |
|---|---|---|---|
| Underserved | 68.6% | 36.3% | −32.3pp |
| Well-served | 88.9% | 43.0% | −45.9pp |

**Read at face value, this looks backwards** — well-served districts show a *larger* percentage-point drop. That's not a mistake; it's Kota Banjarmasin.

### Why the aggregate is misleading, and the honest finding underneath it

Kota Banjarmasin (the provincial capital) has both the highest workforce capacity (56.1 clinical staff per 10k, by far the highest in the province) *and* the most extreme flood exposure — it's built on the Barito river delta below sea level, and collapses from 100% to 0% access in both flood scenarios. Its population (683k, the largest single district) dominates the "well-served" aggregate and single-handedly flips the population-weighted comparison.

**Excluding the two cities (Banjarmasin, Banjarbaru — categorically different, small/dense, not comparable to the 11 rural kabupaten) and comparing the remaining districts:**

| Group (rural kabupaten only) | Avg. pp drop (baseline→moderate) |
|---|---|
| Underserved (6 kabupaten) | −30.3pp |
| Well-served (5 kabupaten) | −21.7pp |

Among comparable rural districts, the expected pattern holds: **underserved districts lost more access, proportionally, than well-served ones.** The full per-kabupaten breakdown is in `data/processed/inequality_per_kabupaten.csv`.

**The actual finding, stated precisely:**
1. **Chronic inequality (pre-flood):** underserved districts already have meaningfully worse baseline access (68.6% vs. 88.9% within 60min) — a real, standalone finding independent of flooding.
2. **Disruption inequality, among comparable geography:** among rural kabupaten, underserved districts lose more access than well-served ones when flooded (30.3pp vs. 21.7pp average drop).
3. **The confound that must be stated explicitly:** capacity and flood exposure are not independent in this province — the capital concentrates both healthcare workforce *and* flood risk, because both cluster on the low-lying, economically-central river delta. A single "underserved vs. well-served" binary, population-weighted across all 13 districts, obscures this rather than revealing it. Any write-up of this result needs to make the Banjarmasin case explicit, not average it away.

## Caveat carried over from Phase 1

All of the above is still against the **BNPB hazard-zone proxy**, not Sentinel-1 observed extent for the actual Jan 2021 event (issue #5, still open). The *direction* of the inequality finding (chronic gap real; disruption gap real among comparable districts; Banjarmasin as confound) is likely robust to that substitution, since it's driven by geography and workforce distribution, not the specific disruption method — but the magnitudes should be re-checked once real event data is in.
