"""Flood-disrupted travel-time scenario: remove/degrade road segments that fall
inside a BNPB InaRISK medium/high flood-hazard zone, then recompute the
multi-source Dijkstra and compare against the baseline.

Interim methodology note (see PROTOCOL.md issue #5): this uses the BNPB *hazard*
layer as a coarse proxy for disruption, not Sentinel-1 *observed* flood extent for
the actual Jan 2021 event — that still needs the user's NASA Earthdata step. This
scenario answers "if roads in flood-hazard zones become impassable, what happens to
accessibility", which is a defensible baseline scenario on its own, but should be
re-run against observed Jan 2021 SAR extent once available for the real event claim.
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
HAZARD_CLASS = DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard_class.tif"
FACILITIES = DATA_PROC / "kalsel_facilities_snapped.geojson"
OUT_TIME = DATA_PROC / "flood_disrupted_travel_time.pickle"
OUT_EDGES = DATA_PROC / "flood_affected_edges.geojson"

DISRUPT_CLASSES = {2, 3}  # medium + high hazard -> treated as impassable


def sample_hazard_at_midpoints(G, hazard_path):
    with rasterio.open(hazard_path) as src:
        band = src.read(1)
        transform = src.transform
        edges = list(G.edges(data=True))
        mid_lons = np.array([(u[0] + v[0]) / 2 for u, v, _ in edges])
        mid_lats = np.array([(u[1] + v[1]) / 2 for u, v, _ in edges])
        rows, cols = rasterio.transform.rowcol(transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        classes = band[rows, cols]
    return edges, classes


def main():
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(FACILITIES)

    edges, classes = sample_hazard_at_midpoints(G, HAZARD_CLASS)
    disrupted_mask = np.isin(classes, list(DISRUPT_CLASSES))
    print(f"[info] {disrupted_mask.sum()}/{len(edges)} edges ({100*disrupted_mask.sum()/len(edges):.1f}%) "
          f"fall in medium/high BNPB flood-hazard zones")

    G_disrupted = G.copy()
    affected_rows = []
    for (u, v, data), is_disrupted in zip(edges, disrupted_mask):
        if is_disrupted:
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
    print(f"[info] nodes stranded from all facilities (disconnected): "
          f"{G.number_of_nodes() - len(travel_time)}")

    with open(OUT_TIME, "wb") as f:
        pickle.dump(travel_time, f)
    print(f"[ok] flood-disrupted travel time -> {OUT_TIME}")


if __name__ == "__main__":
    main()
