"""Flood-disrupted travel-time scenario using the REAL observed Sentinel-1 flood
extent for the Jan 2021 event (src/10_sentinel1_flood_extent.py), replacing the
interim BNPB hazard-zone proxy used in src/06_flood_disruption.py.

Unlike the hazard-zone proxy (a broad multi-year risk classification, which is why
that scenario needed severe/moderate brackets to avoid overclaiming), this is the
actual observed flood footprint for this specific event -- so a single binary
"road segment underwater = impassable" scenario is now a defensible primary result,
not just a sensitivity bound.
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
OUT_TIME = DATA_PROC / "flood_disrupted_sentinel1_travel_time.pickle"
OUT_EDGES = DATA_PROC / "flood_affected_edges_sentinel1.geojson"


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


def main():
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(FACILITIES)

    edges, flooded, in_bounds = sample_flood_at_midpoints(G, FLOOD_EXTENT)
    print(f"[info] {in_bounds.sum()}/{len(edges)} edges fall within the Sentinel-1 scene footprint")
    print(f"[info] {flooded.sum()}/{len(edges)} edges ({100*flooded.sum()/len(edges):.2f}% of all edges) "
          f"cross observed flood water")

    G_disrupted = G.copy()
    affected_rows = []
    for (u, v, data), is_flooded in zip(edges, flooded):
        if is_flooded:
            G_disrupted.remove_edge(u, v)
            affected_rows.append({"highway": data.get("highway"), "geometry": LineString([u, v])})

    affected_gdf = gpd.GeoDataFrame(affected_rows, crs="EPSG:4326")
    affected_gdf.to_file(OUT_EDGES, driver="GeoJSON")
    print(f"[ok] flood-affected edges -> {OUT_EDGES}")

    components = sorted(nx.connected_components(G_disrupted), key=len, reverse=True)
    G_main = G_disrupted.subgraph(components[0]).copy()
    print(f"[info] post-disruption largest component: {len(components[0])} nodes "
          f"({100*len(components[0])/G.number_of_nodes():.1f}% of original graph)")

    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G_main}
    print(f"[info] {len(sources)} facility source nodes reachable post-disruption")

    travel_time = nx.multi_source_dijkstra_path_length(G_main, sources, weight="time_min")
    times = sorted(travel_time.values())
    print(f"[info] disrupted travel time (min) — median={statistics.median(times):.1f}, "
          f"p90={times[int(0.9*len(times))]:.1f}, max={max(times):.1f}")
    print(f"[info] nodes stranded from all facilities: {G.number_of_nodes() - len(travel_time)}")

    with open(OUT_TIME, "wb") as f:
        pickle.dump(travel_time, f)
    print(f"[ok] Sentinel-1-based flood-disrupted travel time -> {OUT_TIME}")


if __name__ == "__main__":
    main()
