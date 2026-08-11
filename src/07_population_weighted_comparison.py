"""Aggregate the clipped population raster to a coarser grid, snap each populated
cell to the road network (via KD-tree, not a per-point linear scan), and compute
population-weighted accessibility: % of population within 30/60/120 min of a
facility, under baseline vs. flood-disrupted (severe and moderate) conditions.
"""
import pickle
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.spatial import cKDTree
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

POP_RASTER = DATA_RAW / "population_roads" / "kalsel_population_2020.tif"
GRAPH = DATA_PROC / "kalsel_road_graph.pickle"

AGGREGATION_FACTOR = 10  # ~100m native -> ~1km cells, matching standard AccessMod-style output resolution
MAX_SNAP_DIST_DEG = 0.02  # ~2.2km at the equator; beyond this, treat as "no motorized road access"
THRESHOLDS_MIN = [30, 60, 120]


def load_population_points():
    with rasterio.open(POP_RASTER) as src:
        src_data = src.read(1)
        src_data = np.where(src_data < 0, 0, src_data)  # nodata sentinel -> 0

        out_height = max(1, src.height // AGGREGATION_FACTOR)
        out_width = max(1, src.width // AGGREGATION_FACTOR)
        dst_transform = src.transform * src.transform.scale(
            src.width / out_width, src.height / out_height
        )
        data = np.zeros((out_height, out_width), dtype="float64")
        reproject(
            source=src_data,
            destination=data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=src.crs,
            resampling=Resampling.sum,
        )

        rows, cols = np.where(data > 0.5)
        pops = data[rows, cols]
        xs, ys = rasterio.transform.xy(dst_transform, rows, cols)
        return np.array(xs), np.array(ys), pops


def snap_and_lookup(xs, ys, tree, node_list, travel_time):
    dist, idx = tree.query(np.column_stack([xs, ys]), k=1)
    times = np.full(len(xs), np.nan)
    reachable = dist <= MAX_SNAP_DIST_DEG
    nodes_hit = [node_list[i] for i in idx[reachable]]
    times[reachable] = [travel_time.get(n, np.nan) for n in nodes_hit]
    return times, reachable


def summarize(pops, times, label):
    valid = ~np.isnan(times)
    total_pop = pops.sum()
    reachable_pop = pops[valid].sum()
    print(f"\n=== {label} ===")
    print(f"total population (sum of raster): {total_pop:,.0f}")
    print(f"population with any road-network access: {reachable_pop:,.0f} ({100*reachable_pop/total_pop:.1f}%)")
    for t in THRESHOLDS_MIN:
        within = pops[valid][times[valid] <= t].sum()
        print(f"  within {t} min: {within:,.0f} ({100*within/total_pop:.1f}% of total pop, "
              f"{100*within/reachable_pop:.1f}% of road-connected pop)")
    unreachable_pop = total_pop - reachable_pop
    print(f"  no facility reachable at all (disconnected/no road access): {unreachable_pop:,.0f} "
          f"({100*unreachable_pop/total_pop:.1f}%)")


def main():
    print("Loading and aggregating population raster...")
    xs, ys, pops = load_population_points()
    print(f"[info] {len(xs)} populated cells (~{AGGREGATION_FACTOR*100}m grid), "
          f"total population {pops.sum():,.0f}")

    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    node_list = list(G.nodes())
    tree = cKDTree(np.array(node_list))

    scenarios = {
        "BASELINE (normal conditions)": DATA_PROC / "baseline_travel_time.pickle",
        "FLOOD-DISRUPTED — severe (all medium+high hazard edges removed)": DATA_PROC / "flood_disrupted_travel_time.pickle",
        "FLOOD-DISRUPTED — moderate (high removed, medium penalized 2.5x)": DATA_PROC / "flood_disrupted_moderate_travel_time.pickle",
    }

    results = {}
    for label, path in scenarios.items():
        with open(path, "rb") as f:
            travel_time = pickle.load(f)
        times, reachable = snap_and_lookup(xs, ys, tree, node_list, travel_time)
        summarize(pops, times, label)
        results[label] = (pops.copy(), times.copy())

    with open(DATA_PROC / "population_weighted_results.pickle", "wb") as f:
        pickle.dump(results, f)
    print(f"\n[ok] results -> {DATA_PROC / 'population_weighted_results.pickle'}")


if __name__ == "__main__":
    main()
