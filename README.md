# HealthReach Indonesia

Independent replication and extension of disaster-aware geographic healthcare accessibility methodology (Macharia et al., KEMRI-Wellcome/Oxford), applied to the January 2021 South Kalimantan floods with district-level healthcare workforce capacity weighting.

See [`PROTOCOL.md`](PROTOCOL.md) for the full research protocol: reference literature, case study justification, data sources, scope, and known risks.

## Status

Scoping and data-feasibility verification complete. Implementation not yet started.

## Structure

```
data/
  raw/
    kalsel_health_profile/   # Dinkes Kalsel Profil Kesehatan 2022 (district-level workforce data)
    flood/                   # BNPB InaRISK + NASA MODIS/Sentinel-1 flood extent
    facilities/              # HDX/healthsites.io geocoded health facilities
    population_roads/        # WorldPop + OSM road network
  processed/
notebooks/
src/
docs/
  literature/                # reference papers
```
