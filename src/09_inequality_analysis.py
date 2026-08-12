"""Phase 2 core question: did flood disruption hit already-underserved districts
(low clinical-workforce-per-capita) harder than well-served ones? Cross-tabulates
the Phase 1 baseline/disrupted travel-time results against the Phase 2 capacity
classification.
"""
import pickle
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.spatial import cKDTree
from pathlib import Path
from shapely.geometry import Point

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

POP_RASTER = DATA_RAW / "population_roads" / "kalsel_population_2020.tif"
GRAPH = DATA_PROC / "kalsel_road_graph.pickle"
CAPACITY = DATA_PROC / "kabupaten_capacity_index.geojson"

AGGREGATION_FACTOR = 10
MAX_SNAP_DIST_DEG = 0.02
THRESHOLDS_MIN = [30, 60, 120]


def load_population_points():
    with rasterio.open(POP_RASTER) as src:
        src_data = src.read(1)
        src_data = np.where(src_data < 0, 0, src_data)
        out_height = max(1, src.height // AGGREGATION_FACTOR)
        out_width = max(1, src.width // AGGREGATION_FACTOR)
        dst_transform = src.transform * src.transform.scale(src.width / out_width, src.height / out_height)
        data = np.zeros((out_height, out_width), dtype="float64")
        reproject(source=src_data, destination=data, src_transform=src.transform, src_crs=src.crs,
                   dst_transform=dst_transform, dst_crs=src.crs, resampling=Resampling.sum)
        rows, cols = np.where(data > 0.5)
        pops = data[rows, cols]
        xs, ys = rasterio.transform.xy(dst_transform, rows, cols)
        return np.array(xs), np.array(ys), pops


def main():
    print("Rebuilding population points...")
    xs, ys, pops = load_population_points()
    pts = gpd.GeoDataFrame({"pop": pops}, geometry=[Point(x, y) for x, y in zip(xs, ys)], crs="EPSG:4326")

    capacity = gpd.read_file(CAPACITY)[["kabupaten", "clinical_staff_per_10k", "capacity_class", "geometry"]]
    pts = gpd.sjoin(pts, capacity, how="left", predicate="within")
    unmatched = pts["kabupaten"].isna().sum()
    print(f"[info] {unmatched}/{len(pts)} population points fell outside any kabupaten polygon (coastal/boundary slivers)")
    pts = pts.dropna(subset=["kabupaten"])

    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    node_list = list(G.nodes())
    tree = cKDTree(np.array(node_list))
    dist, idx = tree.query(np.column_stack([pts.geometry.x, pts.geometry.y]), k=1)
    pts["snap_node_idx"] = idx
    pts["snap_ok"] = dist <= MAX_SNAP_DIST_DEG

    # S1 (Sentinel-1 observed extent) is the primary, event-specific comparison -- see
    # docs/sentinel1_derived_results.md. Proxy scenarios kept alongside for the
    # proxy-vs-observed methodological comparison (docs/manuscript.md §5.1).
    scenarios = {
        "baseline": DATA_PROC / "baseline_travel_time.pickle",
        "s1_moderate": DATA_PROC / "flood_disrupted_sentinel1_moderate_travel_time.pickle",
        "s1_severe": DATA_PROC / "flood_disrupted_sentinel1_travel_time.pickle",
        "proxy_moderate": DATA_PROC / "flood_disrupted_moderate_travel_time.pickle",
        "proxy_severe": DATA_PROC / "flood_disrupted_travel_time.pickle",
    }
    for key, path in scenarios.items():
        with open(path, "rb") as f:
            tt = pickle.load(f)
        node_arr = np.array(node_list)
        times = np.full(len(pts), np.nan)
        ok_mask = pts["snap_ok"].values
        nodes_hit = [tuple(node_arr[i]) for i in pts.loc[ok_mask, "snap_node_idx"]]
        times[ok_mask] = [tt.get(n, np.nan) for n in nodes_hit]
        pts[f"time_{key}"] = times

    print("\n=== Baseline vs flood disruption, by district capacity class ===\n")
    rows = []
    for cls, grp in pts.groupby("capacity_class"):
        total_pop = grp["pop"].sum()
        row = {"capacity_class": cls, "total_pop": total_pop}
        for key in scenarios:
            col = f"time_{key}"
            valid = grp[col].notna()
            reachable_pop = grp.loc[valid, "pop"].sum()
            within60 = grp.loc[valid & (grp[col] <= 60), "pop"].sum()
            row[f"{key}_pct_reachable"] = 100 * reachable_pop / total_pop
            row[f"{key}_pct_within60"] = 100 * within60 / total_pop
        rows.append(row)
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))

    print("\n=== Percentage-point drop in 'within 60 min' access, baseline -> flood ===\n")
    for scen in ["s1_moderate", "s1_severe", "proxy_moderate", "proxy_severe"]:
        summary[f"pp_drop_{scen}"] = summary["baseline_pct_within60"] - summary[f"{scen}_pct_within60"]
    print(summary[["capacity_class"] + [f"pp_drop_{s}" for s in ["s1_moderate", "s1_severe", "proxy_moderate", "proxy_severe"]]]
          .to_string(index=False))

    out = DATA_PROC / "inequality_summary.csv"
    summary.to_csv(out, index=False)
    print(f"\n[ok] summary -> {out}")

    per_kab_rows = []
    for kab, grp in pts.groupby("kabupaten"):
        total_pop = grp["pop"].sum()
        row = {"kabupaten": kab, "capacity_class": grp["capacity_class"].iloc[0],
               "clinical_staff_per_10k": grp["clinical_staff_per_10k"].iloc[0], "total_pop": total_pop}
        for key in scenarios:
            col = f"time_{key}"
            valid = grp[col].notna()
            within60 = grp.loc[valid & (grp[col] <= 60), "pop"].sum()
            row[f"{key}_pct_within60"] = 100 * within60 / total_pop
        per_kab_rows.append(row)
    per_kab = pd.DataFrame(per_kab_rows).sort_values("clinical_staff_per_10k")
    per_kab["pp_drop_s1_moderate"] = per_kab["baseline_pct_within60"] - per_kab["s1_moderate_pct_within60"]
    per_kab["pp_drop_proxy_moderate"] = per_kab["baseline_pct_within60"] - per_kab["proxy_moderate_pct_within60"]
    print("\n=== Per-kabupaten detail ===\n")
    print(per_kab.to_string(index=False))
    per_kab.to_csv(DATA_PROC / "inequality_per_kabupaten.csv", index=False)


if __name__ == "__main__":
    main()
