"""Phase 2: district-level healthcare workforce capacity index.

Uses the WHO SDG 3.c.1-style indicator (physicians + nurses/midwives per 10,000
population) computed from the verified Tabel 13/14 workforce data (transcribed from
page images after the PDF's text layer proved corrupted for that table -- see
docs/phase1_summary.md pipeline notes for the equivalent OSM story). Population
denominators come from the same WorldPop raster used in Phase 1, zonal-summed per
kabupaten boundary (fetched via Nominatim, one geocoding mismatch caught and fixed:
"Banjar" initially resolved to Banjarmasin city, not Kabupaten Banjar).
"""
import geopandas as gpd
import pandas as pd
import rasterio
import rasterio.mask
import numpy as np
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

KABUPATEN = DATA_RAW / "kalsel_kabupaten_boundaries.geojson"
WORKFORCE = DATA_RAW / "kalsel_health_profile" / "workforce_by_kabupaten.csv"
POP_RASTER = DATA_RAW / "population_roads" / "kalsel_population_2020.tif"
OUT = DATA_PROC / "kabupaten_capacity_index.geojson"


def population_per_kabupaten(kab: gpd.GeoDataFrame) -> pd.Series:
    pops = []
    with rasterio.open(POP_RASTER) as src:
        for geom in kab.geometry:
            try:
                out_image, _ = rasterio.mask.mask(src, [geom.__geo_interface__], crop=True, filled=True, nodata=0)
                pops.append(float(np.nansum(np.where(out_image[0] < 0, 0, out_image[0]))))
            except ValueError:
                pops.append(0.0)  # geometry doesn't overlap raster
    return pd.Series(pops, index=kab.index)


def main():
    kab = gpd.read_file(KABUPATEN)
    wf = pd.read_csv(WORKFORCE)

    kab = kab.merge(wf, on="kabupaten", how="left")
    kab["population_2020"] = population_per_kabupaten(kab)

    kab["clinical_staff"] = kab["dokter_spesialis"] + kab["dokter_umum"] + kab["perawat"] + kab["bidan"]
    kab["clinical_staff_per_10k"] = kab["clinical_staff"] / kab["population_2020"] * 10_000

    median_capacity = kab["clinical_staff_per_10k"].median()
    kab["capacity_class"] = np.where(kab["clinical_staff_per_10k"] >= median_capacity, "well-served", "underserved")

    print(kab[["kabupaten", "population_2020", "clinical_staff", "clinical_staff_per_10k", "capacity_class"]]
          .sort_values("clinical_staff_per_10k").to_string(index=False))
    print(f"\n[info] province median: {median_capacity:.1f} clinical staff per 10k population")

    kab.to_file(OUT, driver="GeoJSON")
    print(f"[ok] capacity index -> {OUT}")


if __name__ == "__main__":
    main()
