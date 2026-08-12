"""P0 robustness check: is the extreme 94% severe-disconnection number an
artifact of sampling flood status at a single edge midpoint?

Most graph edges are short (median 22m, since edges are consecutive OSM
node-pairs not whole ways -- see docs/robustness_checks.md), so midpoint
sampling is a reasonable approximation for most of the network. But a small
tail of longer edges (1.1% > 200m) could have a flooded midpoint while much
of the edge is actually dry, or vice versa. This resamples each edge at 5
points along its length and tests the severe (removal) scenario at several
overlap thresholds instead of the single any-midpoint-flooded rule.
"""
import pickle
import numpy as np
import rasterio
import networkx as nx
import geopandas as gpd
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

N_SAMPLE_POINTS = 5
THRESHOLDS = [0.0, 0.25, 0.5, 0.75, 1.0]  # fraction of sample points flooded to count edge as flooded


def sample_overlap_fraction(G, flood_path, is_class_raster=False):
    with rasterio.open(flood_path) as src:
        band = src.read(1)
        transform = src.transform
        bounds = src.bounds
        edges = list(G.edges(data=True))

        fractions = np.zeros(len(edges))
        for i, (u, v, _) in enumerate(edges):
            lons = np.linspace(u[0], v[0], N_SAMPLE_POINTS)
            lats = np.linspace(u[1], v[1], N_SAMPLE_POINTS)
            in_bounds = (lons >= bounds.left) & (lons <= bounds.right) & \
                        (lats >= bounds.bottom) & (lats <= bounds.top)
            if not in_bounds.any():
                continue
            rows, cols = rasterio.transform.rowcol(transform, lons[in_bounds], lats[in_bounds])
            rows = np.clip(rows, 0, band.shape[0] - 1)
            cols = np.clip(cols, 0, band.shape[1] - 1)
            vals = band[rows, cols]
            flooded = np.isin(vals, [2, 3]) if is_class_raster else (vals == 1)
            fractions[i] = flooded.sum() / in_bounds.sum()
    return edges, fractions


def run_severe_at_threshold(G, facilities, edges, fractions, threshold):
    G_scenario = G.copy()
    n_removed = 0
    for (u, v, _), frac in zip(edges, fractions):
        if frac > threshold or (threshold == 0.0 and frac > 0):
            G_scenario.remove_edge(u, v)
            n_removed += 1

    components = sorted(nx.connected_components(G_scenario), key=len, reverse=True)
    largest_pct = 100 * len(components[0]) / G.number_of_nodes()

    G_main = G_scenario.subgraph(components[0]).copy()
    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G_main}
    reachable = nx.multi_source_dijkstra_path_length(G_main, sources, weight="time_min") if sources else {}

    return n_removed, largest_pct, len(sources), len(reachable)


def main():
    with open(DATA_PROC / "kalsel_road_graph.pickle", "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(DATA_PROC / "kalsel_facilities_snapped.geojson")

    print("Sampling Sentinel-1 flood fraction along each edge (5 points)...")
    edges, fractions = sample_overlap_fraction(G, DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif")
    print(f"[info] edges with any flooded sample point: {(fractions > 0).sum()}")
    print(f"[info] edges with ALL sample points flooded: {(fractions >= 1.0).sum()}\n")

    print("=== Sentinel-1 severe scenario at different overlap thresholds ===")
    print("(threshold=0.0 means 'any sample point flooded', matching the original midpoint-only rule closely)\n")
    results = []
    for thresh in THRESHOLDS:
        n_removed, largest_pct, n_sources, n_reachable = run_severe_at_threshold(G, facilities, edges, fractions, thresh)
        reachable_node_pct = 100 * n_reachable / G.number_of_nodes()
        print(f"threshold>{thresh:.2f}: {n_removed:,} edges removed, largest component={largest_pct:.1f}% of graph, "
              f"{n_sources} facility sources reachable, {reachable_node_pct:.1f}% of nodes have ANY facility access")
        results.append(dict(threshold=thresh, n_removed=n_removed, largest_component_pct=largest_pct,
                             facility_sources=n_sources, any_access_node_pct=reachable_node_pct))

    import pandas as pd
    pd.DataFrame(results).to_csv(DATA_PROC / "edge_overlap_sensitivity.csv", index=False)
    print(f"\n[ok] -> {DATA_PROC / 'edge_overlap_sensitivity.csv'}")


if __name__ == "__main__":
    main()
