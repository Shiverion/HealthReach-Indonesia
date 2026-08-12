"""P0 robustness check: does the proxy-vs-observed conclusion survive matched
penalty multipliers?

The earlier moderate scenarios used different multipliers for the two layers
(proxy x2.5, Sentinel-1 x5) -- individually defensible but not a controlled
comparison, since outcome = f(footprint, penalty) and both were varying at
once. This sweeps both layers across the same multiplier set and reports,
per multiplier: population-weighted access, and the underserved-vs-well-served
60min accessibility gap before/after.

Actual result (see docs/robustness_checks.md §4): both layers show positive
gap-widening at every multiplier -- flood disruption amplifies the chronic
gap under both representations, not just the observed one. The finding is
that the PROXY systematically OVERSTATES this widening relative to observed
data, by 1.7-2.6x at every multiplier tested, not that only one
representation shows amplification at all.
"""
import pickle
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
import networkx as nx
from scipy.spatial import cKDTree
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
pop_mod = importlib.import_module("07_population_weighted_comparison")

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

MULTIPLIERS = [2, 2.5, 5, 10]


def get_flag_masks(G):
    edges = list(G.edges(data=True))
    mid_lons = np.array([(u[0] + v[0]) / 2 for u, v, _ in edges])
    mid_lats = np.array([(u[1] + v[1]) / 2 for u, v, _ in edges])

    with rasterio.open(DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard_class.tif") as src:
        band = src.read(1)
        rows, cols = rasterio.transform.rowcol(src.transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        proxy_flagged = np.isin(band[rows, cols], [2, 3])

    with rasterio.open(DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif") as src:
        band = src.read(1)
        bounds = src.bounds
        in_bounds = (mid_lons >= bounds.left) & (mid_lons <= bounds.right) & \
                    (mid_lats >= bounds.bottom) & (mid_lats <= bounds.top)
        rows, cols = rasterio.transform.rowcol(src.transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        s1_flagged = (band[rows, cols] == 1) & in_bounds

    return edges, proxy_flagged, s1_flagged


def run_penalty_scenario(G, facilities, edges, flagged_mask, multiplier):
    G_scenario = G.copy()
    for (u, v, data), is_flagged in zip(edges, flagged_mask):
        if is_flagged:
            G_scenario[u][v]["time_min"] *= multiplier
    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G_scenario}
    return nx.multi_source_dijkstra_path_length(G_scenario, sources, weight="time_min")


def pop_weighted_access(xs, ys, pops, tree, node_list, travel_time, max_snap=0.02):
    node_arr = np.array(node_list)
    dist, idx = tree.query(np.column_stack([xs, ys]), k=1)
    ok = dist <= max_snap
    nodes_hit = [tuple(node_arr[i]) for i in idx[ok]]
    times = np.full(len(xs), np.nan)
    times[ok] = [travel_time.get(n, np.nan) for n in nodes_hit]
    valid = ~np.isnan(times)
    total = pops.sum()
    within60 = pops[valid][times[valid] <= 60].sum()
    return 100 * within60 / total, times


def main():
    with open(DATA_PROC / "kalsel_road_graph.pickle", "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(DATA_PROC / "kalsel_facilities_snapped.geojson")
    node_list = list(G.nodes())
    tree = cKDTree(np.array(node_list))

    print("Loading population points and capacity classification...")
    xs, ys, pops = pop_mod.load_population_points()
    capacity = gpd.read_file(DATA_PROC / "kabupaten_capacity_index.geojson")[["kabupaten", "capacity_class", "geometry"]]
    from shapely.geometry import Point
    pts_geom = gpd.GeoDataFrame({"pop": pops}, geometry=[Point(x, y) for x, y in zip(xs, ys)], crs="EPSG:4326")
    pts_geom = gpd.sjoin(pts_geom, capacity, how="left", predicate="within")
    class_mask_under = (pts_geom["capacity_class"] == "underserved").to_numpy()
    class_mask_well = (pts_geom["capacity_class"] == "well-served").to_numpy()

    print("Sampling flood flags at edge midpoints...")
    edges, proxy_flagged, s1_flagged = get_flag_masks(G)
    print(f"  proxy: {proxy_flagged.sum()} edges flagged, S1: {s1_flagged.sum()} edges flagged\n")

    with open(DATA_PROC / "baseline_travel_time.pickle", "rb") as f:
        baseline_tt = pickle.load(f)
    baseline_access, baseline_times = pop_weighted_access(xs, ys, pops, tree, node_list, baseline_tt)

    def class_within60(times, mask):
        valid = ~np.isnan(times) & mask
        return 100 * pops[valid][times[valid] <= 60].sum() / pops[mask].sum()

    baseline_under = class_within60(baseline_times, class_mask_under)
    baseline_well = class_within60(baseline_times, class_mask_well)
    baseline_gap = baseline_well - baseline_under

    print(f"BASELINE: any-access-weighted 60min={baseline_access:.1f}%, "
          f"underserved={baseline_under:.1f}%, well-served={baseline_well:.1f}%, gap={baseline_gap:.2f}pp\n")

    rows = [{"layer": "baseline", "multiplier": None, "within60_pct": baseline_access,
             "underserved_within60": baseline_under, "well_served_within60": baseline_well,
             "gap_pp": baseline_gap}]

    for layer, flagged in [("proxy", proxy_flagged), ("sentinel1", s1_flagged)]:
        for mult in MULTIPLIERS:
            print(f"=== {layer} x{mult} ===")
            tt = run_penalty_scenario(G, facilities, edges, flagged, mult)
            access, times = pop_weighted_access(xs, ys, pops, tree, node_list, tt)
            under = class_within60(times, class_mask_under)
            well = class_within60(times, class_mask_well)
            gap = well - under
            print(f"  within60={access:.1f}%, underserved={under:.1f}%, well-served={well:.1f}%, "
                  f"gap={gap:.2f}pp (baseline gap was {baseline_gap:.2f}pp)")
            rows.append({"layer": layer, "multiplier": mult, "within60_pct": access,
                         "underserved_within60": under, "well_served_within60": well, "gap_pp": gap})

    df = pd.DataFrame(rows)
    df["gap_widening_pp"] = df["gap_pp"] - baseline_gap
    out = DATA_PROC / "penalty_sensitivity_sweep.csv"
    df.to_csv(out, index=False)
    print(f"\n[ok] sweep -> {out}")
    print("\n=== Summary table ===")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
