"""Georeference the BNPB InaRISK flood hazard export and classify it into risk bins.

Caveat (see PROTOCOL.md): this MapServer serves a *rendered* raster (RGBA colors
per the hazard color ramp), not raw classification values — there is no ImageServer
endpoint exposing pixel-level hazard class. This script reverse-engineers a coarse
3-bin classification (low/medium/high) from pixel color as an interim baseline-hazard
backdrop. It is NOT the primary disruption signal for the Jan 2021 event — that's
Sentinel-1 SAR observed flood extent (see issue #5, pending Earthdata auth). This
layer is for the general hazard-proneness context only.
"""
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
from PIL import Image

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SRC_PNG = DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard.tif"  # actually PNG bytes, mislabeled by server
OUT_TIF = DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard_georef.tif"
OUT_CLASS = DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard_class.tif"

# actual extent returned by the export/{f=json} call for this request (bbox snapped
# to preserve square pixels at 2400x2400) — see PROTOCOL.md / fetch log
EXTENT = dict(xmin=113.76499999999996, ymin=-5.4199999999999999, xmax=117.87499999999996, ymax=-1.3100000000000007)


def classify_pixel_rgb(rgb):
    """Rough hazard color-ramp -> {0: none/nodata, 1: low, 2: medium, 3: high}."""
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    alpha = rgb[..., 3] if rgb.shape[-1] == 4 else np.full(r.shape, 255)

    out = np.zeros(r.shape, dtype=np.uint8)
    nodata = (alpha < 10) | ((r > 245) & (g > 245) & (b > 245))  # transparent or white bg

    # green-dominant -> low
    low = (g >= r) & (g > b + 20) & ~nodata
    # yellow: high R+G, low B
    medium = (r > 180) & (g > 150) & (b < 120) & (r <= g + 40) & ~low & ~nodata
    # orange/red: high R, mid-low G, low B
    high = (r > 180) & (b < 100) & (g <= 180) & ~low & ~medium & ~nodata

    out[low] = 1
    out[medium] = 2
    out[high] = 3
    return out


def main():
    if OUT_CLASS.exists():
        print(f"[skip] {OUT_CLASS} already exists")
        return

    img = np.array(Image.open(SRC_PNG).convert("RGBA"))
    print(f"[info] image shape: {img.shape}")

    height, width = img.shape[0], img.shape[1]
    transform = from_bounds(EXTENT["xmin"], EXTENT["ymin"], EXTENT["xmax"], EXTENT["ymax"], width, height)

    meta = dict(
        driver="GTiff",
        height=height,
        width=width,
        count=4,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    )
    with rasterio.open(OUT_TIF, "w", **meta) as dest:
        for i in range(4):
            dest.write(img[:, :, i], i + 1)
    print(f"[ok] georeferenced RGBA -> {OUT_TIF}")

    classified = classify_pixel_rgb(img)
    class_meta = dict(
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
        nodata=0,
    )
    with rasterio.open(OUT_CLASS, "w", **class_meta) as dest:
        dest.write(classified, 1)

    unique, counts = np.unique(classified, return_counts=True)
    print(f"[ok] classified hazard -> {OUT_CLASS}")
    print("[info] pixel counts by class (0=none/nodata,1=low,2=med,3=high):", dict(zip(unique.tolist(), counts.tolist())))


if __name__ == "__main__":
    main()
