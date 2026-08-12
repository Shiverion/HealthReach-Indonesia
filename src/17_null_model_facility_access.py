"""Null A2: does the uniform-random null tell the same story when the damage
metric is population disconnected from healthcare specifically, rather than
generic largest-connected-component size (Null A, src/16)?

These are not the same metric. Random failure could fragment the graph into
many small pieces that mostly contain no population (rural cul-de-sacs) --
severe by a graph-topology measure, mild by a healthcare-access measure. A
geographically concentrated real flood could do the reverse: isolate one
large, densely-populated, facility-poor region -- comparatively mild by a
graph-topology measure, severe by a healthcare-access measure. Null A alone
cannot distinguish these; this is why it was run as a follow-up rather than
treated as redundant with Null A.

Metric: for each trial (real flood, or one of 200 random equal-sized edge
removals), find which connected components contain zero health facilities,
then sum the population (already snapped to graph nodes in earlier steps)
sitting in those facility-less components.
"""
import pickle
import random
import time
import numpy as np
import networkx as nx
import geopandas as gpd
import pandas as pd
import rasterio
from scipy.spatial import cKDTree
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
pop_mod = importlib.import_module("07_population_weighted_comparison")

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
N_TRIALS = 200
SEED = 42
MAX_SNAP = 0.02


def get_observed_flooded_edges(G):
    with rasterio.open(DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif") as src:
        band = src.read(1)
        transform = src.transform
        bounds = src.bounds
        edges = list(G.edges())
        mid_lons = np.array([(u[0] + v[0]) / 2 for u, v in edges])
        mid_lats = np.array([(u[1] + v[1]) / 2 for u, v in edges])
        in_bounds = (mid_lons >= bounds.left) & (mid_lons <= bounds.right) & \
                    (mid_lats >= bounds.bottom) & (mid_lats <= bounds.top)
        rows, cols = rasterio.transform.rowcol(transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        flooded = (band[rows, cols] == 1) & in_bounds
    return [e for e, f in zip(edges, flooded) if f]


def population_disconnected_pct(G, removed_edges, facility_nodes, pop_node_idx, pops, total_pop):
    """pop_node_idx: for each population point, index into `nodes` array of its snapped graph node.
    Returns % of total population sitting in a connected component with zero facilities."""
    G2 = G.copy()
    G2.remove_edges_from(removed_edges)
    components = list(nx.connected_components(G2))

    # map node -> component id (only need it for nodes population/facilities actually snap to)
    node_to_comp = {}
    facility_comp_ids = set()
    for i, comp in enumerate(components):
        # only bother recording membership for facility nodes; for population nodes we do a
        # cheaper trick below (build a node->comp dict only once per trial, sized to |V|)
        pass

    # Build node->component id array-free via dict (still O(V) but only string/tuple hashing,
    # same order of cost as the connected_components call itself)
    comp_id_of = {}
    for i, comp in enumerate(components):
        for n in comp:
            comp_id_of[n] = i

    facility_comp_ids = {comp_id_of[n] for n in facility_nodes if n in comp_id_of}

    disconnected_mask = np.array([
        (comp_id_of.get(node) not in facility_comp_ids) if node is not None else True
        for node in pop_node_idx
    ])
    return 100 * pops[disconnected_mask].sum() / total_pop


def main():
    with open(DATA_PROC / "kalsel_road_graph.pickle", "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(DATA_PROC / "kalsel_facilities_snapped.geojson")
    facility_nodes = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    facility_nodes = {n for n in facility_nodes if n in G}

    print("Loading population points...")
    xs, ys, pops = pop_mod.load_population_points()
    total_pop = pops.sum()
    node_list = list(G.nodes())
    tree = cKDTree(np.array(node_list))
    dist, idx = tree.query(np.column_stack([xs, ys]), k=1)
    ok = dist <= MAX_SNAP
    node_arr = np.array(node_list)
    pop_node_idx = [tuple(node_arr[i]) if o else None for i, o in zip(idx, ok)]
    print(f"[info] {ok.sum()}/{len(xs)} population points snapped within {MAX_SNAP} deg")

    all_edges = list(G.edges())
    observed_flooded = get_observed_flooded_edges(G)
    n_flooded = len(observed_flooded)

    print(f"\n[info] computing observed (real Sentinel-1 flood) facility-disconnection...")
    observed_pct = population_disconnected_pct(G, observed_flooded, facility_nodes, pop_node_idx, pops, total_pop)
    print(f"[info] observed: {observed_pct:.2f}% of population disconnected from all facilities")

    print(f"\n[info] running {N_TRIALS} random-edge-removal trials (facility-access metric)...")
    random.seed(SEED)
    trial_results = []
    t0 = time.time()
    for i in range(N_TRIALS):
        sample = random.sample(all_edges, n_flooded)
        pct = population_disconnected_pct(G, sample, facility_nodes, pop_node_idx, pops, total_pop)
        trial_results.append(pct)
        if (i + 1) % 25 == 0:
            elapsed = time.time() - t0
            print(f"  trial {i+1}/{N_TRIALS} ({elapsed:.0f}s elapsed, ~{elapsed/(i+1)*N_TRIALS:.0f}s total est.)")

    trial_results = np.array(trial_results)
    b_forward = int((trial_results >= observed_pct).sum())  # random at least as damaging (more pop disconnected)
    b_reverse = int((trial_results <= observed_pct).sum())  # random at least as mild
    p_forward = (b_forward + 1) / (N_TRIALS + 1)
    p_reverse = (b_reverse + 1) / (N_TRIALS + 1)

    print(f"\n[info] random-trial pop-disconnected %: mean={trial_results.mean():.2f}, "
          f"median={np.median(trial_results):.2f}, min={trial_results.min():.2f}, max={trial_results.max():.2f}")
    print(f"[info] observed ({observed_pct:.2f}%) vs random null distribution:")
    print(f"       forward (observed disconnects MORE population than random): b={b_forward}, p={p_forward:.4f}")
    print(f"       reverse (observed disconnects LESS population than random): b={b_reverse}, p={p_reverse:.4f}")

    pd.DataFrame({"trial": range(N_TRIALS), "pop_disconnected_pct": trial_results}).to_csv(
        DATA_PROC / "null_model_a2_facility_access.csv", index=False)

    with open(DATA_PROC / "null_model_a2_summary.pickle", "wb") as f:
        pickle.dump(dict(n_flooded=n_flooded, observed_pct=observed_pct, n_trials=N_TRIALS,
                          b_forward=b_forward, p_forward=p_forward, b_reverse=b_reverse, p_reverse=p_reverse,
                          trial_mean=trial_results.mean(), trial_min=trial_results.min(),
                          trial_max=trial_results.max()), f)
    print(f"\n[ok] -> {DATA_PROC / 'null_model_a2_facility_access.csv'}")


if __name__ == "__main__":
    main()
