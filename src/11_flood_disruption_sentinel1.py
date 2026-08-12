"""Flood-disrupted travel-time scenarios using the REAL observed Sentinel-1 flood
extent for the Jan 2021 event (src/10_sentinel1_flood_extent.py), replacing the
interim BNPB hazard-zone proxy used in src/06_flood_disruption.py.

Same severe/moderate bracket structure as the proxy scenarios in
src/06_flood_disruption.py, and defined identically in *operation* (severe =
remove, moderate = penalize only, nothing removed) so the two are genuinely
comparable -- see docs/manuscript.md §5.1 for why that comparison is treated
as a primary result, not just a discarded first attempt at the proxy.
"""
import pickle
import statistics
import numpy as np
import rasterio
import geopandas as gpd
import networkx as nx
from pathlib import Path
from shapely.geometry import LineString

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

GRAPH = DATA_PROC / "kalsel_road_graph.pickle"
FLOOD_EXTENT = DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif"
FACILITIES = DATA_PROC / "kalsel_facilities_snapped.geojson"

MODERATE_PENALTY = 5.0


def sample_flood_at_midpoints(G, flood_path):
    with rasterio.open(flood_path) as src:
        band = src.read(1)
        transform = src.transform
        bounds = src.bounds
        edges = list(G.edges(data=True))
        mid_lons = np.array([(u[0] + v[0]) / 2 for u, v, _ in edges])
        mid_lats = np.array([(u[1] + v[1]) / 2 for u, v, _ in edges])
        in_bounds = (mid_lons >= bounds.left) & (mid_lons <= bounds.right) & \
                    (mid_lats >= bounds.bottom) & (mid_lats <= bounds.top)
        rows, cols = rasterio.transform.rowcol(transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        flooded = band[rows, cols] == 1
        flooded = flooded & in_bounds  # edges outside the S1 scene footprint -> not flagged
    return edges, flooded, in_bounds


def run_scenario(G, facilities, edges, flooded_mask, mode, out_time, out_edges=None):
    G_scenario = G.copy()
    affected_rows = []
    for (u, v, data), is_flooded in zip(edges, flooded_mask):
        if not is_flooded:
            continue
        affected_rows.append({"highway": data.get("highway"), "geometry": LineString([u, v])})
        if mode == "severe":
            G_scenario.remove_edge(u, v)
        elif mode == "moderate":
            G_scenario[u][v]["time_min"] *= MODERATE_PENALTY
        else:
            raise ValueError(mode)

    if out_edges is not None:
        gpd.GeoDataFrame(affected_rows, crs="EPSG:4326").to_file(out_edges, driver="GeoJSON")
        print(f"  [ok] flood-affected edges -> {out_edges}")

    components = sorted(nx.connected_components(G_scenario), key=len, reverse=True)
    G_main = G_scenario.subgraph(components[0]).copy()
    print(f"  [info] largest component: {len(components[0])} nodes "
          f"({100*len(components[0])/G.number_of_nodes():.1f}% of original graph)")

    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G_main}
    print(f"  [info] {len(sources)} facility source nodes reachable")

    travel_time = nx.multi_source_dijkstra_path_length(G_main, sources, weight="time_min")
    times = sorted(travel_time.values())
    print(f"  [info] travel time (min) — median={statistics.median(times):.1f}, "
          f"p90={times[int(0.9*len(times))]:.1f}, max={max(times):.1f}")
    print(f"  [info] nodes stranded from all facilities: {G.number_of_nodes() - len(travel_time)}")

    with open(out_time, "wb") as f:
        pickle.dump(travel_time, f)
    print(f"  [ok] travel time -> {out_time}")


def main():
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(FACILITIES)

    edges, flooded, in_bounds = sample_flood_at_midpoints(G, FLOOD_EXTENT)
    print(f"[info] {in_bounds.sum()}/{len(edges)} edges fall within the Sentinel-1 scene footprint")
    print(f"[info] {flooded.sum()}/{len(edges)} edges ({100*flooded.sum()/len(edges):.2f}% of all edges) "
          f"cross observed flood water\n")

    print("=== SEVERE (remove) ===")
    run_scenario(G, facilities, edges, flooded, "severe",
                 DATA_PROC / "flood_disrupted_sentinel1_travel_time.pickle",
                 DATA_PROC / "flood_affected_edges_sentinel1.geojson")

    print("\n=== MODERATE (penalize 5x, no removal) ===")
    run_scenario(G, facilities, edges, flooded, "moderate",
                 DATA_PROC / "flood_disrupted_sentinel1_moderate_travel_time.pickle")


if __name__ == "__main__":
    main()
