"""Clip WorldPop Indonesia population raster to the South Kalimantan boundary.

Note: WorldPop's server doesn't support HTTP range requests (confirmed: vsicurl
windowed read fails with "Range downloading not supported"), so this operates on
the fully-downloaded local file rather than a remote partial read.
"""
import geopandas as gpd
import rasterio
import rasterio.mask
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SRC_LOCAL = DATA_RAW / "population_roads" / "idn_ppp_2020_full.tif"
OUT = DATA_RAW / "population_roads" / "kalsel_population_2020.tif"


def main():
    if OUT.exists():
        print(f"[skip] {OUT} already exists")
        return

    boundary = gpd.read_file(DATA_RAW / "kalsel_boundary.geojson")
    geom = [boundary.union_all().__geo_interface__]

    print(f"Opening local file {SRC_LOCAL} ...")
    with rasterio.open(SRC_LOCAL) as src:
        print(f"[info] source CRS={src.crs}, size={src.width}x{src.height}")
        out_image, out_transform = rasterio.mask.mask(src, geom, crop=True)
        out_meta = src.meta.copy()

    out_meta.update(
        {
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        }
    )

    with rasterio.open(OUT, "w", **out_meta) as dest:
        dest.write(out_image)

    print(f"[ok] population raster -> {OUT} ({out_image.shape[2]}x{out_image.shape[1]} px)")


if __name__ == "__main__":
    main()
