"""Process the Sentinel-1 baseline/event GRD pair into an observed flood-extent
layer for the Jan 2021 South Kalimantan flood, replacing the interim BNPB
hazard-zone proxy used in Phase 1/2.

Method: warp each raw GRD (only has GCPs, no direct transform) into EPSG:4326
using its embedded ground control points, crop to the flood-affected AOI, then
classify water per-scene via Otsu thresholding on backscatter intensity (not a
full radiometric sigma0 calibration -- per-image relative separation is
sufficient for Otsu, see docs/phase1_summary.md-style caveat in the summary
this script's caller writes). New flood extent = event water AND NOT baseline
water (removes permanent rivers/water bodies common to both dates).
"""
import numpy as np
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform
from rasterio.enums import Resampling
from skimage.filters import threshold_otsu
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
S1_DIR = DATA_RAW / "flood" / "sentinel1" / "extracted"

BASELINE_TIFF = S1_DIR / "S1A_IW_GRDH_1SDV_20201215T220001_20201215T220026_035702_042D74_6B40.SAFE" / "measurement" / "s1a-iw-grd-vv-20201215t220001-20201215t220026-035702-042d74-001.tiff"
EVENT_TIFF = S1_DIR / "S1A_IW_GRDH_1SDV_20210120T220000_20210120T220025_036227_043FC4_66B8.SAFE" / "measurement" / "s1a-iw-grd-vv-20210120t220000-20210120t220025-036227-043fc4-001.tiff"

# flood-affected AOI (10 BNPB kabupaten bbox, see PROTOCOL.md / conversation)
AOI_BOUNDS = (114.3, -4.2, 115.9, -1.3)  # minx, miny, maxx, maxy
TARGET_RES_DEG = 0.0003  # ~33m at the equator -- coarser than native 10m, keeps arrays manageable

OUT_BASELINE_WATER = DATA_PROC / "s1_baseline_water.tif"
OUT_EVENT_WATER = DATA_PROC / "s1_event_water.tif"
OUT_NEW_FLOOD = DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif"


def warp_and_crop(tiff_path):
    with rasterio.open(tiff_path) as src:
        dst_crs = "EPSG:4326"
        src_crs = src.gcps[1]  # GCPs' own CRS -- tells GDAL to warp using the embedded GCP grid
        print(f"  [info] source gcp count: {len(src.gcps[0])}, gcp crs: {src_crs}")
        # let GDAL compute the natural warped extent/resolution first (do not force a
        # custom output grid directly -- that produced an all-zero read, likely a
        # mismatch between the forced grid and the source's actual warped placement)
        with WarpedVRT(src, src_crs=src_crs, crs=dst_crs, resampling=Resampling.average) as vrt:
            print(f"  [info] auto-warped bounds: {vrt.bounds}, shape: {vrt.shape}, res: {vrt.res}")
            window = rasterio.windows.from_bounds(*AOI_BOUNDS, transform=vrt.transform)
            out_width = max(1, int((AOI_BOUNDS[2] - AOI_BOUNDS[0]) / TARGET_RES_DEG))
            out_height = max(1, int((AOI_BOUNDS[3] - AOI_BOUNDS[1]) / TARGET_RES_DEG))
            data = vrt.read(1, window=window, out_shape=(out_height, out_width), resampling=Resampling.average)
            transform = rasterio.transform.from_bounds(*AOI_BOUNDS, out_width, out_height)
            crs = vrt.crs
    return data, transform, crs


def classify_water(intensity, transform, crs, out_path):
    valid = intensity > 0
    vals = intensity[valid].astype("float64")
    # log-scale like a rough dB conversion -- helps Otsu separate the low-backscatter water mode
    log_vals = 10 * np.log10(vals + 1)
    thresh = threshold_otsu(log_vals)
    print(f"  [info] Otsu threshold (log scale): {thresh:.2f}, "
          f"valid pixels: {valid.sum():,}/{intensity.size:,}")

    water = np.zeros(intensity.shape, dtype="uint8")
    log_full = np.where(valid, 10 * np.log10(intensity.astype("float64") + 1), 999)
    water[valid] = (log_full[valid] < thresh).astype("uint8")

    pct_water = 100 * water[valid].sum() / valid.sum()
    print(f"  [info] classified water: {pct_water:.1f}% of valid area")

    meta = dict(driver="GTiff", height=water.shape[0], width=water.shape[1],
                count=1, dtype="uint8", crs=crs, transform=transform, nodata=255)
    with rasterio.open(out_path, "w", **meta) as dst:
        dst.write(water, 1)
    return water


def main():
    print("Warping + cropping baseline scene (Dec 15, 2020)...")
    base_intensity, transform, crs = warp_and_crop(BASELINE_TIFF)
    print("Warping + cropping event scene (Jan 20, 2021)...")
    event_intensity, _, _ = warp_and_crop(EVENT_TIFF)

    print("Classifying water, baseline...")
    baseline_water = classify_water(base_intensity, transform, crs, OUT_BASELINE_WATER)
    print("Classifying water, event...")
    event_water = classify_water(event_intensity, transform, crs, OUT_EVENT_WATER)

    new_flood = ((event_water == 1) & (baseline_water == 0)).astype("uint8")
    pct_new_flood = 100 * new_flood.sum() / new_flood.size
    print(f"\n[info] NEW flood extent (event water, not present at baseline): "
          f"{pct_new_flood:.2f}% of AOI area")

    meta = dict(driver="GTiff", height=new_flood.shape[0], width=new_flood.shape[1],
                count=1, dtype="uint8", crs=crs, transform=transform, nodata=255)
    with rasterio.open(OUT_NEW_FLOOD, "w", **meta) as dst:
        dst.write(new_flood, 1)
    print(f"[ok] observed flood extent -> {OUT_NEW_FLOOD}")


if __name__ == "__main__":
    main()
